"""Google Gemini adapter (Interactions API) for the optional AI assist layer.

Endpoint, header and parameter names were verified against the current official
Google documentation (see docs/ADR-002-AI-Assist-Layer.md for the citations):

* POST https://generativelanguage.googleapis.com/v1beta/interactions
* Auth: ``x-goog-api-key: <key>`` (no Authorization bearer header)
* Body: ``model``, ``input``, ``system_instruction``, ``response_format``
  (``{type: "text", mime_type: "application/json", schema: <JSON Schema>}``),
  ``generation_config.max_output_tokens``, and ``store: false`` so the provider
  does not retain the interaction.
* Response: an ``Interaction`` whose ``steps[].content[].text`` holds the JSON
  string (a top-level ``output_text`` is used when present).

The model name always comes from settings (``AI_MODEL``); nothing is hardcoded.
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

GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _is_incomplete(data: Mapping[str, Any]) -> bool:
    """True when the interaction stopped because the output budget ran out.

    Thinking tokens count against ``max_output_tokens`` in this API, so a cap
    that is too small for the model's reasoning is spent before any text is
    written and the envelope comes back ``incomplete`` with nothing in it. The
    provider HTTP status is still 200, which is why this has to be read from the
    body rather than from the status code.
    """
    return data.get("status") == "incomplete"


def _extract_text(data: Any) -> str:
    if not isinstance(data, Mapping):
        raise AIUnavailableError("invalid_output")

    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    chunks: list[str] = []
    steps = data.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, Mapping) or step.get("type") != "model_output":
                continue
            content = step.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    isinstance(block, Mapping)
                    and block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                ):
                    chunks.append(block["text"])

    if not chunks:
        raise AIUnavailableError("invalid_output")
    return "".join(chunks)


class GeminiLLMClient:
    """Schema-constrained JSON generation through the Gemini Interactions API."""

    provider = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float,
        thinking_level: str | None = None,
        url: str = GEMINI_INTERACTIONS_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._timeout = timeout_seconds
        # ``None`` leaves the model's own reasoning effort in place. Every
        # feature here asks the model to *write*, not to analyse, so a lower
        # level both costs less and leaves the output budget for the answer.
        self.thinking_level = thinking_level
        self._url = url
        self._transport = transport

    def _generation_config(self) -> dict[str, Any]:
        """The ``generation_config`` block, with the thinking level when set."""
        config: dict[str, Any] = {"max_output_tokens": self.max_output_tokens}
        if self.thinking_level:
            config["thinking_level"] = self.thinking_level
        return config

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, Any],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult:
        body: dict[str, Any] = {
            "model": self.model,
            "input": user,
            "system_instruction": system,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": dict(schema),
            },
            "generation_config": self._generation_config(),
            # Never let the provider retain the prompt or the response.
            "store": False,
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
                        "x-goog-api-key": self._api_key,
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
            # interaction is ``incomplete``, the output budget ran out mid-answer,
            # which is a spent budget rather than a malformed response.
            if exc.reason == "invalid_output" and _is_incomplete(payload):
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
