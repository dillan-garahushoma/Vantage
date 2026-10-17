"""Join-code vocabulary: the alphabet, the length and the normalisation rule.

A join code is a short secret an HOA admin reads out or pastes into a message, so
the alphabet deliberately omits the characters people confuse when a code is
transcribed by hand: ``I``, ``L``, ``O``, ``0`` and ``1``. Thirty-one symbols over
ten characters is about 49.5 bits of entropy (see ADR-007), which is far beyond
what a human could guess - and the five-attempts-per-fifteen-minutes limiter in
:mod:`app.identity.services.join_attempt_limiter` closes the online-guessing door
long before that.
"""
from __future__ import annotations

import secrets

# No I, L, O, 0 or 1.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10


def generate_join_code() -> str:
    """Draw one fresh code from the alphabet using a cryptographic source."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalise_join_code(raw: str | None) -> str:
    """Return the canonical form of a user-typed code.

    Trims, upper-cases and drops spaces and hyphens, so ``" abcd-efgh jk "`` and
    ``"ABCDEFGHJK"`` are the same code. Anything that normalises to the empty
    string can never match a stored code, because every generated code is
    ten characters long.
    """
    if not raw:
        return ""
    cleaned = "".join(
        char for char in raw if not char.isspace() and char not in "-_"
    )
    return cleaned.upper()
