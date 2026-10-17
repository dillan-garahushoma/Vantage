"""Adapter for any OpenAI-compatible chat completions endpoint.

Covers hosted gateways such as NVIDIA Build. Verified against the OpenAI Chat
Completions contract:

* POST ``<base_url>/v1/chat/completions`` (``/v1`` is not doubled if the base
  URL already ends with it).
* Auth: ``Authorization: Bearer <key>``.
* Body: ``model``, ``messages`` (system + user), ``response_format``
  ``{"type": "json_object"}``, ``max_tokens``.
* Response: ``choices[0].message.content`` holds the JSON string.

Provider quirk: OpenAI's JSON mode requires the word "json" to appear somewhere
in the messages. This adapter appends a minimal instruction when it is missing,
so a caller's prompt is never the reason a call fails.

Reason mapping: ``429`` is ``rate_limited`` (a spent quota, retry later) and
``finish_reason: length`` is ``truncated`` (the output budget ran out), so both
stay distinguishable from a generic provider failure. Reasoning models behind an
OpenAI-compatible gateway usually count their reasoning against ``max_tokens``
too, which is why the default cap is generous.

This API has no schema parameter, so ``schema`` is enforced locally after the
response returns: provider output is always treated as untrusted.
"""
from __future__ import annotations

import time
from typing import Any, Mapping

import httpx

from app.core.ai.client import (
    DataClass,
    Feature,
    LLMResult,
    http_error_reason,
    parse_json_output,
)
from app.core.ai.errors import AIUnavailableError

_JSON_HINT = "\nRespond with a single JSON object."


def _chat_completions_url(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return f"{trimmed}/v1/chat/completions"


class OpenAICompatLLMClient:
    """JSON-mode chat completions against any OpenAI-compatible provider."""

    provider = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._url = _chat_completions_url(base_url)
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._timeout = timeout_seconds
        self._transport = transport

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, Any],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult:
        system_text = system
        if "json" not in f"{system}\n{user}".lower():
            system_text += _JSON_HINT

        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_output_tokens,
        }

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    self._url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise AIUnavailableError(http_error_reason(exc)) from None

        if response.status_code == 429:
            raise AIUnavailableError("rate_limited")
        if response.status_code >= 400:
            raise AIUnavailableError("provider_error")

        try:
            payload = response.json()
        except ValueError:
            raise AIUnavailableError("invalid_output") from None

        try:
            parsed = parse_json_output(_extract_text(payload), schema)
        except AIUnavailableError as exc:
            # A usable answer always wins; but when there is not one and the
            # provider stopped at the token limit, say so instead of reporting a
            # malformed answer - a spent budget and a broken contract need
            # different fixes.
            if exc.reason == "invalid_output" and _stopped_at_the_token_limit(payload):
                raise AIUnavailableError("truncated") from None
            raise
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LLMResult(
            parsed=parsed,
            provider=self.provider,
            model=self.model,
            latency_ms=latency_ms,
            input_chars=len(system) + len(user),
        )


def _stopped_at_the_token_limit(data: Any) -> bool:
    """True when the first choice stopped because it ran out of output tokens."""
    if not isinstance(data, Mapping):
        return False
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    first = choices[0]
    return isinstance(first, Mapping) and first.get("finish_reason") == "length"


def _extract_text(data: Any) -> str:
    if not isinstance(data, Mapping):
        raise AIUnavailableError("invalid_output")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIUnavailableError("invalid_output")

    first = choices[0]
    if not isinstance(first, Mapping):
        raise AIUnavailableError("invalid_output")

    message = first.get("message")
    if not isinstance(message, Mapping):
        raise AIUnavailableError("invalid_output")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AIUnavailableError("invalid_output")
    return content
