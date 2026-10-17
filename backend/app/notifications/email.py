"""Outbound email: one small interface, one SMTP implementation, one safe default.

There is deliberately **no** third-party email dependency. ``smtplib`` from the
standard library is enough for the volume a pilot estate produces, and it keeps the
product's existing rule that infrastructure is not added for its own sake.

The pieces:

* :class:`EmailMessage` - the only shape a caller can hand over. Recipients are a
  tuple, the subject is a single line, and the body is plain text: nothing here can
  set a header of its own, so a caller cannot smuggle one in through a field.
* :class:`EmailSender` - the protocol the rest of the app depends on, so a test can
  pass an in-memory double and no test ever opens a socket.
* :class:`SmtpEmailSender` - the real transport. Blocking ``smtplib`` calls run in
  a worker thread so an async request handler is never stalled by a slow relay.
* :class:`NullEmailSender` - the default when ``EMAIL_ENABLED`` is false. It logs
  that a message *would* have been sent and never touches the network, which is
  what makes the whole feature safe to ship switched off.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as _StdEmailMessage
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """One plain-text message. No caller-supplied headers, ever."""

    to: tuple[str, ...]
    subject: str
    body: str
    reply_to: str | None = None

    def __post_init__(self) -> None:
        if not self.to:
            raise ValueError("An email needs at least one recipient.")
        # A newline in a subject or address is a header-injection attempt, not a
        # subject; refuse it rather than let the transport decide.
        for value in (self.subject, *self.to, self.reply_to or ""):
            if "\n" in value or "\r" in value:
                raise ValueError("Email headers must not contain newlines.")


@runtime_checkable
class EmailSender(Protocol):
    """Anything that can deliver one :class:`EmailMessage`."""

    async def send(self, message: EmailMessage) -> None:  # pragma: no cover - protocol
        ...


class NullEmailSender:
    """The default sender: logs the intent, sends nothing, never fails.

    Chosen when ``EMAIL_ENABLED`` is false. It records the subject and the number
    of recipients (never the body, which can carry personal data) so an operator
    can see that the wiring is live while no message leaves the machine.
    """

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "email disabled (EMAIL_ENABLED=false); would send %r to %d recipient(s)",
            message.subject,
            len(message.to),
        )


class SmtpEmailSender:
    """A real SMTP transport, run off the event loop.

    ``smtplib`` is blocking, so each send happens in a worker thread. STARTTLS is
    used by default; credentials are only sent when both a username and a password
    were configured, so a local development relay without auth works unchanged.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_starttls: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_starttls = use_starttls
        self._timeout = timeout_seconds

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        raw = _StdEmailMessage()
        raw["From"] = self._sender
        raw["To"] = ", ".join(message.to)
        raw["Subject"] = message.subject
        if message.reply_to:
            raw["Reply-To"] = message.reply_to
        raw.set_content(message.body)

        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
            if self._use_starttls:
                client.starttls()
            if self._username and self._password:
                client.login(self._username, self._password)
            client.send_message(raw)


def build_email_sender(settings: object) -> EmailSender:
    """The sender the application should use, from configuration alone.

    Returns :class:`SmtpEmailSender` only when ``EMAIL_ENABLED`` is true *and* a
    host is configured; otherwise the silent :class:`NullEmailSender`. Nothing
    here reads a secret value - the SMTP password is unwrapped only to hand it to
    the transport.
    """
    enabled = bool(getattr(settings, "EMAIL_ENABLED", False))
    host = getattr(settings, "SMTP_HOST", None)
    if not enabled or not host:
        return NullEmailSender()

    password = getattr(settings, "SMTP_PASSWORD", None)
    return SmtpEmailSender(
        host=host,
        port=int(getattr(settings, "SMTP_PORT", 587)),
        sender=str(getattr(settings, "EMAIL_FROM", "no-reply@valora.local")),
        username=getattr(settings, "SMTP_USERNAME", None),
        # SecretStr -> str only at the moment of use.
        password=password.get_secret_value() if password is not None else None,
        use_starttls=bool(getattr(settings, "SMTP_USE_STARTTLS", True)),
    )


__all__ = [
    "EmailMessage",
    "EmailSender",
    "NullEmailSender",
    "SmtpEmailSender",
    "build_email_sender",
]
