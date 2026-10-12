"""Failure type for the optional AI assist layer.

Any problem in the AI layer surfaces as ``AIUnavailableError`` so callers can
fall back to a non-AI path. The exception deliberately carries only a reason
code: never an API key, never prompt text, never a raw provider response.
"""
from __future__ import annotations

from typing import Final, Literal

AIUnavailableReason = Literal[
    "disabled",
    "policy",
    "budget",
    "timeout",
    "network",
    "provider_error",
    "invalid_output",
]

_REASONS: Final[frozenset[str]] = frozenset(
    {"disabled", "policy", "budget", "timeout", "network", "provider_error", "invalid_output"}
)


class AIUnavailableError(Exception):
    """The AI assist layer could not produce a validated result."""

    def __init__(self, reason: str) -> None:
        if reason not in _REASONS:
            raise ValueError(f"Unknown AI unavailability reason: {reason!r}")
        self.reason: str = reason
        super().__init__(f"AI assist unavailable ({reason}).")
