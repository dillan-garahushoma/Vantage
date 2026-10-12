"""Deterministic in-process AI client for tests and development.

The factory only selects this when ``AI_PROVIDER=fake``, and configuration
refuses that provider outside development and test. It never touches the network.
"""
from __future__ import annotations

import asyncio
from typing import Any, Mapping

from app.core.ai.client import DataClass, Feature, LLMResult


def _synthesize(schema: Mapping[str, Any]) -> Any:
    """Build a deterministic, schema-shaped value.

    Deterministic by construction: no randomness, no clock, no I/O.
    """
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]

    expected = schema.get("type")
    if isinstance(expected, list):
        expected = next((t for t in expected if t != "null"), "null")

    if expected == "object" or "properties" in schema:
        properties = schema.get("properties") or {}
        names = schema.get("required")
        if not isinstance(names, list) or not names:
            names = list(properties.keys()) if isinstance(properties, Mapping) else []
        result: dict[str, Any] = {}
        for name in names:
            child = properties.get(name) if isinstance(properties, Mapping) else None
            result[name] = _synthesize(child if isinstance(child, Mapping) else {})
        return result

    if expected == "array":
        items = schema.get("items")
        return [_synthesize(items if isinstance(items, Mapping) else {})]

    if expected == "integer":
        return 0
    if expected == "number":
        return 0.0
    if expected == "boolean":
        return True
    if expected == "null":
        return None
    return "fake"


class FakeLLMClient:
    """Deterministic stand-in provider."""

    provider = "fake"

    def __init__(
        self,
        *,
        response: Any = None,
        model: str = "fake-deterministic",
        delay_seconds: float = 0.0,
    ) -> None:
        self._response = response
        self.model = model
        self._delay_seconds = delay_seconds

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, Any],
        data_class: DataClass,
        feature: Feature,
    ) -> LLMResult:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)

        parsed = self._response if self._response is not None else _synthesize(schema)
        return LLMResult(
            parsed=parsed,
            provider=self.provider,
            model=self.model,
            latency_ms=0,
            input_chars=len(system) + len(user),
        )
