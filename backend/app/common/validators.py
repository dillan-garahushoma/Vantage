import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_REGEX.match(value))


def normalise_email(value: str) -> str:
    return value.strip().lower()
