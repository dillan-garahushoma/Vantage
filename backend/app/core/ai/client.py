"""Provider-neutral contract for the optional AI assist layer, plus the single
guardrail wrapper that every provider call must pass through.

The wrapper is the only place the AI gates are implemented, so no adapter can
skip them: master switch, per-feature flag, personal-data opt-in, input size cap,
and a hard timeout with no retry.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol

import httpx

from app.core.ai.errors import AIUnavailableError
from app.core.config import Settings


class DataClass(str, Enum):
    """How sensitive the data sent to the provider is."""

    aggregate = "aggregate"
    personal = "personal"


Feature = str  # one of "insights" | "triage" (validated at runtime by the wrapper)


@dataclass(frozen=True)
class LLMResult:
    """A schema-validated provider result."""

    parsed: Any
    provider: str
    model: str
    latency_ms: int
    input_chars: int


class LLMClient(Protocol):
    """Every AI provider adapter implements exactly this."""

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, Any],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult: ...


# Feature name -> the settings flag that must be true for it to run.
_FEATURE_FLAGS: dict[str, str] = {
    "insights": "AI_INSIGHTS_ENABLED",
    "triage": "AI_TRIAGE_ENABLED",
}


class GatedLLMClient:
    """Enforces every AI guardrail before the provider is reached.

    ``inner`` is the provider adapter. It may be ``None`` when AI is disabled -
    in that case the master-switch gate raises before the adapter is touched.
    """

    def __init__(self, settings: Settings, inner: LLMClient | None) -> None:
        self._settings = settings
        self.inner = inner

    @property
    def provider(self) -> str:
        """The wrapped provider's name, or ``disabled`` when there is none."""
        if self.inner is None:
            return "disabled"
        return getattr(self.inner, "provider", "unknown")

    @property
    def model(self) -> str:
        """The wrapped provider's model, or an empty string when there is none."""
        if self.inner is None:
            return ""
        return getattr(self.inner, "model", "")

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, Any],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult:
        settings = self._settings

        # 1. Master kill switch. Everything is off unless it was turned on.
        if not settings.AI_ENABLED:
            raise AIUnavailableError("disabled")

        # 2. Per-feature flag. Unknown features never reach a provider.
        flag_name = _FEATURE_FLAGS.get(feature)
        if flag_name is None:
            raise AIUnavailableError("policy")
        if not getattr(settings, flag_name):
            raise AIUnavailableError("disabled")

        # 3. Personal data needs the explicit opt-in.
        if data_class == DataClass.personal and not settings.AI_PERSONAL_DATA_ALLOWED:
            raise AIUnavailableError("policy")

        # 4. Size cap, checked before any HTTP.
        if len(system) + len(user) > settings.AI_MAX_INPUT_CHARS:
            raise AIUnavailableError("policy")

        if self.inner is None:
            raise AIUnavailableError("disabled")

        # 5. Hard timeout, single attempt. The adapter makes exactly one request.
        try:
            return await asyncio.wait_for(
                self.inner.generate_json(
                    system=system,
                    user=user,
                    schema=schema,
                    data_class=data_class,
                    feature=feature,
                ),
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise AIUnavailableError("timeout") from None


def http_error_reason(exc: httpx.HTTPError) -> str:
    """Map a transport-level failure to an AIUnavailableError reason."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.TransportError):
        return "network"
    return "provider_error"


def parse_json_output(raw_text: str, schema: Mapping[str, Any]) -> Any:
    """Decode provider text and schema-validate it.

    Provider output is untrusted, so a JSON decode failure or a schema mismatch
    both become ``invalid_output``. Messages never echo the provider's payload.
    """
    import json

    try:
        payload = json.loads(raw_text)
    except (ValueError, TypeError):
        raise AIUnavailableError("invalid_output") from None

    validate_json_schema(payload, schema)
    return payload


# --------------------------------------------------------------------------- #
# Minimal JSON Schema subset validator.
#
# We deliberately avoid a new dependency (e.g. jsonschema). This supports the
# subset we ask providers for: type, properties, required, items, enum,
# maxItems/minItems and additionalProperties=false. It raises on the first
# violation and never quotes the offending value, because that value may be
# personal data.
# --------------------------------------------------------------------------- #

_TYPE_CHECKS: dict[str, Any] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def _type_ok(value: Any, expected: str) -> bool:
    check = _TYPE_CHECKS.get(expected)
    if check is None:
        return True
    return bool(check(value))


def validate_json_schema(
    payload: Any, schema: Mapping[str, Any], *, path: str = "$"
) -> None:
    """Validate ``payload`` against a JSON Schema subset.

    Raises ``AIUnavailableError('invalid_output')`` on the first violation.
    """
    if not isinstance(schema, Mapping):
        return

    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_type_ok(payload, t) for t in expected if isinstance(t, str)):
            raise AIUnavailableError("invalid_output")
        expected = None
    elif isinstance(expected, str) and not _type_ok(payload, expected):
        raise AIUnavailableError("invalid_output")

    enum = schema.get("enum")
    if isinstance(enum, list) and payload not in enum:
        raise AIUnavailableError("invalid_output")

    # Array bounds. The providers we ask for structured output support minItems
    # and maxItems, and the DTOs enforce the same limits afterwards, so checking
    # them here keeps the two validators from disagreeing about what is valid.
    if isinstance(payload, list):
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(payload) > max_items:
            raise AIUnavailableError("invalid_output")
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(payload) < min_items:
            raise AIUnavailableError("invalid_output")

    if isinstance(payload, dict) and (expected == "object" or "properties" in schema):
        properties = schema.get("properties") or {}
        for name in schema.get("required") or []:
            if name not in payload:
                raise AIUnavailableError("invalid_output")
        for name, value in payload.items():
            if name in properties:
                validate_json_schema(value, properties[name], path=f"{path}.{name}")
            elif schema.get("additionalProperties") is False:
                raise AIUnavailableError("invalid_output")

    if isinstance(payload, list) and expected == "array":
        items = schema.get("items")
        if isinstance(items, Mapping):
            for index, item in enumerate(payload):
                validate_json_schema(item, items, path=f"{path}[{index}]")
