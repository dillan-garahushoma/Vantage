"""Best-effort redaction of personal data before a prompt reaches a provider.

This is a **mitigation, not a guarantee**. It replaces the patterns it can
recognise in free text: email addresses, South African phone numbers, 13-digit
South African ID numbers, caller-supplied names and caller-supplied unit
numbers.

It cannot catch what it was not told about. A name, nickname, address or vehicle
registration that the caller does not pass in ``known_names``/``unit_numbers``
survives untouched, and so does any personal data that does not match one of the
fixed patterns. Redaction therefore reduces exposure; it does not make a prompt
safe, and it is never a substitute for the ``data_class=personal`` gate or for
not sending personal data at all.

The replacements are fixed markers: ``[EMAIL]``, ``[PHONE]``, ``[ID]``,
``[NAME]``, ``[UNIT]``.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Final

EMAIL_REGEX: Final = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# 13 digits, not part of a longer number.
SA_ID_REGEX: Final = re.compile(r"(?<!\d)\d{13}(?!\d)")

# +27 XX XXX XXXX / 0XX XXX XXXX, with optional spaces, dots or hyphens.
SA_PHONE_REGEX: Final = re.compile(
    r"(?<!\d)(?:\+27[\s.\-]?|0)\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)"
)

MIN_NAME_PART_LENGTH: Final = 3

# Replaced in this order on purpose: a South African ID number starts with a
# birth date, so it can begin with a digit pattern the phone rule would happily
# eat half of, and a phone number can contain a digit run the ID rule would
# treat as a 13-digit id. Longest, most specific patterns go first.
_PLACEHOLDER_EMAIL: Final = "[EMAIL]"
_PLACEHOLDER_ID: Final = "[ID]"
_PLACEHOLDER_PHONE: Final = "[PHONE]"
_PLACEHOLDER_NAME: Final = "[NAME]"
_PLACEHOLDER_UNIT: Final = "[UNIT]"


def _name_tokens(known_names: Iterable[str]) -> list[str]:
    """Split known names into whole-word tokens of at least three characters."""
    tokens: set[str] = set()
    for name in known_names:
        for part in re.split(r"\s+", str(name).strip()):
            if len(part) >= MIN_NAME_PART_LENGTH:
                tokens.add(part)
    # Longest first so a compound token wins over its own prefix.
    return sorted(tokens, key=len, reverse=True)


def _compile_whole_word(pattern: str, *, flags: int = 0) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(pattern)}(?!\w)", flags)


def redact(
    text: str,
    *,
    known_names: Iterable[str] = (),
    unit_numbers: Iterable[str] = (),
) -> str:
    """Return ``text`` with recognised personal data replaced by fixed markers.

    ``known_names`` are matched case-insensitively, whole word, including
    individual name parts of three or more characters. ``unit_numbers`` are
    matched case-insensitively as standalone tokens.
    """
    if not text:
        return text

    redacted = EMAIL_REGEX.sub(_PLACEHOLDER_EMAIL, text)
    redacted = SA_ID_REGEX.sub(_PLACEHOLDER_ID, redacted)
    redacted = SA_PHONE_REGEX.sub(_PLACEHOLDER_PHONE, redacted)

    for token in _name_tokens(known_names):
        redacted = _compile_whole_word(token, flags=re.IGNORECASE).sub(
            _PLACEHOLDER_NAME, redacted
        )

    for unit in unit_numbers:
        unit_text = str(unit).strip()
        if unit_text:
            redacted = _compile_whole_word(unit_text, flags=re.IGNORECASE).sub(
                _PLACEHOLDER_UNIT, redacted
            )

    return redacted
