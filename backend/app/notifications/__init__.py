"""Outbound notifications (email today).

The package is intentionally tiny: a transport-agnostic sender
(:mod:`app.notifications.email`) and the messages built on top of it
(:mod:`app.notifications.residency_notifications`). Nothing here reads or logs a
secret value, and the default transport sends nothing.
"""
from app.notifications.email import (
    EmailMessage,
    EmailSender,
    NullEmailSender,
    SmtpEmailSender,
    build_email_sender,
)
from app.notifications.residency_notifications import ResidencyNotifier

__all__ = [
    "EmailMessage",
    "EmailSender",
    "NullEmailSender",
    "SmtpEmailSender",
    "build_email_sender",
    "ResidencyNotifier",
]
