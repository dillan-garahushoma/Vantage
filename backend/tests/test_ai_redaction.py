"""Tests for best-effort redaction of personal data before an AI call (BATCH AI-2).

Redaction is a reduction of risk, not a guarantee. These tests pin what it does
catch so the limits in the docstring stay honest.
"""

from __future__ import annotations

import pytest

from app.core.ai.redaction import redact


def test_emails_are_replaced() -> None:
    assert redact("Write to alice.smith+estate@example.co.za please.") == (
        "Write to [EMAIL] please."
    )


@pytest.mark.parametrize(
    "text",
    [
        "Call +27 82 123 4567 now",
        "Call +27821234567 now",
        "Call +27-82-123-4567 now",
        "Call 082 123 4567 now",
        "Call 082-123-4567 now",
        "Call 0821234567 now",
        "Call 021 555 0100 now",
    ],
)
def test_south_african_phone_formats_are_replaced(text: str) -> None:
    assert redact(text) == "Call [PHONE] now"


def test_thirteen_digit_sa_id_numbers_are_replaced() -> None:
    assert redact("ID 9202204720082 on file") == "ID [ID] on file"
    # A leading zero is a valid birth-year month/day start and must not be
    # half-eaten by the phone pattern.
    assert redact("ID 0508155678083 on file") == "ID [ID] on file"


def test_known_names_are_replaced_case_insensitively_and_whole_word() -> None:
    text = "Alice complained about alice's neighbour, per ALICE."
    assert redact(text, known_names=("Alice Smith",)) == (
        "[NAME] complained about [NAME]'s neighbour, per [NAME]."
    )


def test_name_parts_of_three_or_more_characters_are_replaced() -> None:
    text = "Jo van der Merwe logged it."
    assert redact(text, known_names=("Jo van der Merwe",)) == "Jo [NAME] [NAME] [NAME] logged it."


def test_short_name_parts_do_not_match_inside_longer_words() -> None:
    text = "The annexe is fine."
    assert redact(text, known_names=("Ann",)) == text


def test_unit_numbers_are_replaced() -> None:
    text = "Unit A-101 and unit A-1012 are affected; A-101 too."
    assert redact(text, unit_numbers=("A-101",)) == (
        "Unit [UNIT] and unit A-1012 are affected; [UNIT] too."
    )


def test_mixed_text_is_redacted_together() -> None:
    text = (
        "Resident Alice Smith (alice@example.com, +27 82 123 4567, ID 9202204720082) "
        "in unit A-101 reports a leak."
    )
    assert redact(text, known_names=("Alice Smith",), unit_numbers=("A-101",)) == (
        "Resident [NAME] [NAME] ([EMAIL], [PHONE], ID [ID]) in unit [UNIT] reports a leak."
    )


def test_text_without_personal_data_is_returned_unchanged() -> None:
    text = "The estate pool pump failed twice this week."
    assert redact(text) == text


def test_text_with_no_known_names_or_units_is_still_scrubbed() -> None:
    assert redact("Mail bob@example.com or ring 083 765 4321.") == (
        "Mail [EMAIL] or ring [PHONE]."
    )


def test_redaction_does_not_depend_on_iterable_order() -> None:
    text = "Alice Smith in A-101"
    a = redact(text, known_names=("Smith", "Alice Smith"), unit_numbers=("A-101",))
    b = redact(text, known_names=("Alice Smith", "Smith"), unit_numbers=("A-101",))
    assert a == b == "[NAME] [NAME] in [UNIT]"


def test_empty_and_none_like_inputs_are_safe() -> None:
    assert redact("") == ""


def test_regex_metacharacters_in_known_values_are_escaped() -> None:
    text = "Owner (Pty) Ltd filed it."
    assert redact(text, known_names=("(Pty) Ltd",)) == "Owner [NAME] [NAME] filed it."


def test_redact_does_not_touch_placeholder_looking_text_twice() -> None:
    text = "[EMAIL] and [PHONE]"
    assert redact(text) == text
