"""The two residency emails, and who each one goes to.

The recipients are the estate's *own* HOA administrators - resolved from persisted
membership, never a configured address that could belong to the wrong complex. If
an estate has no administrator with an email address the send is skipped with a
warning; the request itself is already committed, and the admin approval queue is
the durable record, so a missing notification never loses a registration.

Every method returns whether delivery succeeded rather than raising: the caller
only uses that to stamp an idempotence timestamp. A relay outage must not fail the
resident's registration.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ResidencyRequestStatus, UserRole
from app.identity.models.estate_residency_request import EstateResidencyRequest
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.notifications.email import EmailMessage, EmailSender, NullEmailSender

logger = logging.getLogger(__name__)


def _format_timestamp(value: datetime | None) -> str:
    """A stable, unambiguous timestamp for an email body, in UTC."""
    if value is None:
        return "unknown"
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class ResidencyNotifier:
    """Builds and sends the new-request and decision emails for one estate."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        sender: EmailSender,
        base_url: str,
    ) -> None:
        self._memberships = EstateMembershipRepository(db)
        self._sender = sender
        self._base_url = base_url.rstrip("/")

    def _review_link(self, request: EstateResidencyRequest) -> str:
        # A stable deep link into the admin queue. It carries no secret: the page
        # it opens is behind authentication and an estate-admin check.
        return (
            f"{self._base_url}/admin/residency"
            f"?estate_id={request.estate_id}&request={request.request_id}"
        )

    async def _admin_recipients(self, estate_id: int) -> tuple[str, ...]:
        contacts = await self._memberships.list_contacts_for_role(
            estate_id=estate_id, membership_role=UserRole.hoa_admin.value
        )
        # Deduplicate case-insensitively while keeping a deterministic order.
        seen: dict[str, str] = {}
        for _, email in contacts:
            if email:
                seen.setdefault(email.strip().lower(), email.strip())
        return tuple(seen[key] for key in sorted(seen))

    async def notify_new_request(
        self,
        *,
        estate_name: str,
        request: EstateResidencyRequest,
    ) -> bool:
        """Tell the estate's administrators a registration awaits review."""
        recipients = await self._admin_recipients(request.estate_id)
        if not recipients:
            logger.warning(
                "residency request %s has no HOA-admin recipient for estate %s; "
                "it remains in the approval queue",
                request.request_id,
                request.estate_id,
            )
            return False

        subject = f"New resident registration awaiting review — {estate_name}"
        body = "\n".join(
            [
                "A new resident registration is waiting for your decision.",
                "",
                f"Estate:   {estate_name}",
                f"Unit:     {request.unit_no or 'to be assigned by the estate office'}",
                f"Applicant: {request.applicant_name}",
                f"Email:    {request.applicant_email}",
                f"Phone:    {request.applicant_phone or 'not supplied'}",
                f"Submitted: {_format_timestamp(request.created_at)}",
                "",
                f"Review it in the VALORA admin dashboard: {self._review_link(request)}",
                "",
                "Approve to grant the applicant resident access to this estate, or",
                "reject to decline it. No action is taken until you decide.",
            ]
        )
        return await self._deliver(
            EmailMessage(
                to=recipients,
                subject=subject,
                body=body,
                # A reply goes straight to the applicant, not to a no-reply box.
                reply_to=request.applicant_email,
            ),
            context=f"new-request {request.request_id}",
        )

    async def notify_decision(
        self,
        *,
        estate_name: str,
        request: EstateResidencyRequest,
    ) -> bool:
        """Tell the applicant the outcome of their own request."""
        if not request.applicant_email:
            return False

        approved = request.status == ResidencyRequestStatus.approved.value
        subject = (
            f"Your registration for {estate_name} was approved"
            if approved
            else f"Your registration for {estate_name} was not approved"
        )
        if approved:
            outcome = (
                "Your registration was approved. You now have resident access to "
                "this estate and can sign in to VALORA. Use the Enter estate link in "
                "your VALORA account to continue."
            )
        else:
            outcome = (
                "Your registration was not approved by the estate administrator.\n"
                "If you believe this is a mistake, contact your estate office."
            )
        lines = [
            f"Hello {request.applicant_name},",
            "",
            outcome,
            "",
            f"Estate:   {estate_name}",
            f"Unit:     {request.unit_no or 'to be assigned by the estate office'}",
            f"Decided:  {_format_timestamp(request.decided_at)}",
        ]
        if request.decision_note:
            lines += ["", f"Note from the estate: {request.decision_note}"]
        lines += [
            "",
            f"Reference: request #{request.request_id}",
        ]
        return await self._deliver(
            EmailMessage(
                to=(request.applicant_email,),
                subject=subject,
                body="\n".join(lines),
            ),
            context=f"decision {request.request_id}",
        )

    async def _deliver(self, message: EmailMessage, *, context: str) -> bool:
        """Send one message, swallowing failure into a logged warning.

        Returns True only when the sender accepted the message, which is when the
        caller stamps ``notified_at`` / ``decision_notified_at``. A False result is
        logged loudly and leaves the request untouched.
        """
        if isinstance(self._sender, NullEmailSender):
            return False
        try:
            await self._sender.send(message)
        except Exception:  # noqa: BLE001 - a relay failure must never fail the request
            logger.warning("could not send residency email (%s)", context)
            return False
        return True


__all__ = ["ResidencyNotifier"]
