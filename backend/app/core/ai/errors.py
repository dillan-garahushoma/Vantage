"""Failure type for the optional AI assist layer.

Any problem in the AI layer surfaces as ``AIUnavailableError`` so callers can
fall back to a non-AI path. The exception deliberately carries only a reason
code: never an API key, never prompt text, never a raw provider response.

``truncated`` is separate from ``invalid_output`` on purpose. A provider that
stops generating because it ran out of output tokens returns a well-formed
envelope with no answer in it, which is an operator problem - the cap is too
small - not a malformed answer. Reporting both as ``invalid_output`` is what
made a too-small output cap look like a rejected API key.

``rate_limited`` is separate from ``provider_error`` for the same reason: a spent
quota (HTTP 429) is a limit that resets or needs billing, not a broken key, a
bug or an outage, and the two want opposite responses from the operator.
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
    "rate_limited",
    "invalid_output",
    "truncated",
]

_REASONS: Final[frozenset[str]] = frozenset(
    {
        "disabled",
        "policy",
        "budget",
        "timeout",
        "network",
        "provider_error",
        "rate_limited",
        "invalid_output",
        "truncated",
    }
)


class AIUnavailableError(Exception):
    """The AI assist layer could not produce a validated result."""

    def __init__(self, reason: str) -> None:
        if reason not in _REASONS:
            raise ValueError(f"Unknown AI unavailability reason: {reason!r}")
        self.reason: str = reason
        super().__init__(f"AI assist unavailable ({reason}).")
