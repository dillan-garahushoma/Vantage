"""In-process sliding-window limiter for failed join-code attempts.

A join code is short enough to be shared in a message, so the only real defence
against someone guessing one - or brute-forcing five hundred of them - is to make
guessing cheap to detect. Five failed code attempts per user per fifteen minutes
turns a 49-bit secret into something no online attacker can reach while a resident
who mistyped their code three times is barely inconvenienced.

**Single process.** The counter lives in this process's memory, so two API workers
do not share it and a restart forgets every window. That is documented as an open
question in ADR-007: it is correct for one pilot estate behind one process, and it
would need a shared store the moment the API is scaled horizontally.
"""
from __future__ import annotations

import time
from collections import deque

from app.core.exceptions import RateLimitException

DEFAULT_MAX_FAILURES = 5
DEFAULT_WINDOW_SECONDS = 15 * 60

# The refusal a blocked caller sees. Callers that throttle something other than a
# join code (adding a provider by email, ONB master P1.1) pass their own wording.
DEFAULT_BLOCKED_MESSAGE = "Too many failed join attempts. Please try again later."


class JoinAttemptLimiter:
    """Counts failed join-code attempts per user in a sliding time window.

    The clock is injectable so the window can be tested without sleeping.
    """

    def __init__(
        self,
        *,
        max_failures: int = DEFAULT_MAX_FAILURES,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        clock=None,
    ) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._clock = clock if clock is not None else time.monotonic
        self._failures: dict[int, deque[float]] = {}

    def _recent(self, user_id: int) -> deque[float]:
        """Drop the attempts that have fallen out of the window."""
        queue = self._failures.get(user_id)
        if queue is None:
            return deque()
        cutoff = self._clock() - self._window_seconds
        while queue and queue[0] <= cutoff:
            queue.popleft()
        if not queue:
            self._failures.pop(user_id, None)
        return queue

    def failures_in_window(self, user_id: int) -> int:
        return len(self._recent(user_id))

    def is_blocked(self, user_id: int) -> bool:
        return self.failures_in_window(user_id) >= self._max_failures

    def ensure_allowed(self, user_id: int, *, message: str | None = None) -> None:
        """Raise a 429 when this user has exhausted their failed attempts."""
        if self.is_blocked(user_id):
            raise RateLimitException(message or DEFAULT_BLOCKED_MESSAGE)

    def record_failure(self, user_id: int) -> None:
        """Count one failed code attempt."""
        self._recent(user_id)
        self._failures.setdefault(user_id, deque()).append(self._clock())

    def reset(self, user_id: int) -> None:
        self._failures.pop(user_id, None)

    def reset_all(self) -> None:
        self._failures.clear()


# The application-wide limiter. Tests inject their own instance instead.
join_attempt_limiter = JoinAttemptLimiter()
