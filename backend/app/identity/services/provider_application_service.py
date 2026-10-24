"""Collect provider applications and provision approved applicants."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.common.validators import normalise_email
from app.core.config import get_settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ServiceUnavailableException,
)
from app.core.security import hash_password
from app.identity.models.user import User
from app.identity.repositories.estate_membership_event_repository import (
    EstateMembershipEventRepository,
)
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.provider_application_repository import (
    ProviderApplicationRepository,
)
from app.identity.repositories.provider_invitation_repository import (
    ProviderInvitationRepository,
)
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.auth import AuthResponse
from app.identity.schemas.provider_invitation import (
    ProviderInvitationAcceptRequest,
    ProviderApplicationCreateRequest,
    ProviderApplicationResponse,
)
from app.identity.services.auth_service import AuthService
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.notifications.email import EmailMessage, EmailSender, NullEmailSender, build_email_sender
from app.property.repositories.estate_repository import EstateRepository
from app.providers.repositories.service_provider_repository import ServiceProviderRepository

logger = logging.getLogger(__name__)
INVITATION_TTL = timedelta(days=7)
INVALID_INVITATION_MESSAGE = "That provider invitation is not valid."


class ProviderApplicationService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        sender: EmailSender | None = None,
        base_url: str | None = None,
    ) -> None:
        self._db = db
        self._invitations = ProviderInvitationRepository(db)
        self._applications = ProviderApplicationRepository(db)
        self._users = UserRepository(db)
        self._providers = ServiceProviderRepository(db)
        self._memberships = EstateMembershipRepository(db)
        self._events = EstateMembershipEventRepository(db)
        self._estates = EstateRepository(db)
        self._authorization = EstateAuthorizationService(db)
        settings = get_settings()
        self._sender = sender if sender is not None else build_email_sender(settings)
        self._base_url = (
            base_url if base_url is not None else settings.APP_BASE_URL
        ).rstrip("/")

    async def apply(
        self, payload: ProviderApplicationCreateRequest
    ) -> ProviderApplicationResponse:
        estate = await self._estates.get_by_id(payload.estate_id)
        if estate is None or not estate.is_public or estate.is_demo:
            raise NotFoundException("That estate is not accepting public applications.")

        email = normalise_email(str(payload.email))
        user = await self._users.get_by_email(email)
        provider = await self._providers.get_by_email(email)
        if user is not None and (
            user.role != UserRole.service_provider.value
            or provider is None
            or provider.user_id != user.user_id
            or await self._memberships.has_estate_access(
                user_id=user.user_id, estate_id=estate.estate_id
            )
        ):
            raise ConflictException("An application could not be submitted for this email.")
        if (
            (user is None and provider is not None)
            or await self._applications.has_pending(estate_id=estate.estate_id, email=email)
        ):
            raise ConflictException("An application could not be submitted for this email.")

        try:
            application = await self._applications.add(
                estate_id=estate.estate_id,
                full_name=payload.full_name,
                email=email,
                trade=payload.trade,
                phone=payload.phone,
                note=payload.note,
                status="pending",
            )
            await self._db.commit()
            await self._db.refresh(application)
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException("An application could not be submitted for this email.")

        return self._application_response(application, estate_name=estate.name)

    async def list_applications(
        self,
        actor: User,
        *,
        estate_id: int,
        status: str | None,
    ) -> list[ProviderApplicationResponse]:
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        rows = await self._applications.list_for_estate(estate_id=estate_id, status=status)
        estate = await self._estates.get_by_id(estate_id)
        return [
            self._application_response(row, estate_name=estate.name if estate else None)
            for row in rows
        ]

    async def approve(
        self, actor: User, *, estate_id: int, application_id: int
    ) -> ProviderApplicationResponse:
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        if isinstance(self._sender, NullEmailSender):
            raise ServiceUnavailableException(
                "Provider setup emails are not configured. The application remains pending."
            )

        application = await self._applications.get_by_id_in_estate(
            application_id=application_id, estate_id=estate_id, for_update=True
        )
        if application is None:
            raise NotFoundException("Provider application not found.")
        if application.status != "pending":
            raise ConflictException("This provider application has already been reviewed.")
        existing_user = await self._users.get_by_email(application.email)
        if existing_user is not None:
            existing_provider = await self._providers.get_by_user_id(
                existing_user.user_id
            )
            if (
                existing_user.role != UserRole.service_provider.value
                or existing_provider is None
                or await self._memberships.has_estate_access(
                    user_id=existing_user.user_id, estate_id=estate_id
                )
            ):
                raise ConflictException(
                    "An account now uses this email and cannot be provisioned for this application."
                )
        estate = await self._estates.get_by_id(estate_id)
        if estate is None:
            raise NotFoundException("That estate was not found.")

        token = secrets.token_urlsafe(32)
        now = utcnow()
        expires_at = now + INVITATION_TTL
        await self._invitations.revoke_active_for_email(
            estate_id=estate_id, email=application.email
        )
        invitation = await self._invitations.add(
            application_id=application.application_id,
            estate_id=estate_id,
            created_by_user_id=actor.user_id,
            email=application.email,
            full_name=application.full_name,
            trade=application.trade,
            phone=application.phone,
            token_digest=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
        application.status = "approved"
        application.reviewed_by_user_id = actor.user_id
        application.reviewed_at = now
        await self._applications.save(application)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException("This provider application has already been reviewed.")

        setup_url = f"{self._base_url}/provider/accept-invitation#token={token}"
        existing_user = await self._users.get_by_email(application.email)
        setup_instructions = (
            "Open the secure link to activate your access to this estate. If you already "
            "have a VALORA provider account, the link will sign you in and add the estate. "
            "If this is your first VALORA provider account, choose a password on the setup page."
            if existing_user is not None
            else "Choose a password using this secure link within seven days to activate your "
            "provider account and estate access."
        )
        message = EmailMessage(
            to=(application.email,),
            subject=f"Your provider application to {estate.name} was approved",
            body=(
                f"Hello {application.full_name},\n\n"
                f"{estate.name} has approved your application to work as a {application.trade} provider.\n"
                f"{setup_instructions}\n\n"
                f"{setup_url}\n\n"
                "If you were not expecting this email, contact the estate administrator."
            ),
        )
        try:
            await self._sender.send(message)
        except Exception as exc:
            logger.exception(
                "provider approval email delivery failed for estate_id=%s application_id=%s",
                estate_id,
                application_id,
            )
            try:
                await self._db.rollback()
                invitation = await self._invitations.get_by_token_digest_for_update(
                    token_digest=hashlib.sha256(token.encode("utf-8")).hexdigest()
                )
                application = await self._applications.get_by_id_in_estate(
                    application_id=application_id,
                    estate_id=estate_id,
                    for_update=True,
                )
                if invitation is None or application is None:
                    raise RuntimeError(
                        "The provider invitation could not be restored after email failure."
                    )
                invitation.revoked_at = utcnow()
                application.status = "pending"
                application.reviewed_by_user_id = None
                application.reviewed_at = None
                await self._db.commit()
            except Exception:
                logger.exception(
                    "failed to restore pending provider application after email failure "
                    "(estate_id=%s application_id=%s)",
                    estate_id,
                    application_id,
                )
                raise
            raise ServiceUnavailableException(
                "Approval could not be completed because the setup email was not delivered. The application remains pending."
            ) from exc

        return self._application_response(application, estate_name=estate.name)

    async def reject(
        self, actor: User, *, estate_id: int, application_id: int
    ) -> ProviderApplicationResponse:
        await self._authorization.require_role(
            actor=actor,
            estate_id=estate_id,
            allowed_roles=(UserRole.hoa_admin.value,),
        )
        application = await self._applications.get_by_id_in_estate(
            application_id=application_id, estate_id=estate_id, for_update=True
        )
        if application is None:
            raise NotFoundException("Provider application not found.")
        if application.status != "pending":
            raise ConflictException("This provider application has already been reviewed.")
        estate = await self._estates.get_by_id(estate_id)
        application.status = "rejected"
        application.reviewed_by_user_id = actor.user_id
        application.reviewed_at = utcnow()
        await self._applications.save(application)
        await self._db.commit()
        return self._application_response(application, estate_name=estate.name if estate else None)

    @staticmethod
    def _application_response(
        application, *, estate_name: str | None
    ) -> ProviderApplicationResponse:
        return ProviderApplicationResponse(
            application_id=application.application_id,
            estate_id=application.estate_id,
            estate_name=estate_name,
            full_name=application.full_name,
            email=application.email,
            trade=application.trade,
            phone=application.phone,
            note=application.note,
            status=application.status,
            created_at=application.created_at,
            reviewed_at=application.reviewed_at,
        )

    async def accept(self, payload: ProviderInvitationAcceptRequest) -> AuthResponse:
        token_digest = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
        invitation = await self._invitations.get_by_token_digest_for_update(
            token_digest=token_digest
        )
        now = utcnow()
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or invitation.expires_at <= now
        ):
            raise NotFoundException(INVALID_INVITATION_MESSAGE)

        email = normalise_email(invitation.email)
        user = await self._users.get_by_email(email)
        try:
            if user is None:
                if payload.password is None:
                    raise BadRequestException(
                        "Choose a password to activate your new provider account."
                    )
                user = await self._users.add(
                    full_name=invitation.full_name,
                    email=email,
                    password_hash=hash_password(payload.password),
                    role=UserRole.service_provider.value,
                    phoneno=invitation.phone,
                )
                await self._providers.add(
                    user_id=user.user_id,
                    full_name=invitation.full_name,
                    trade=invitation.trade,
                    phone=invitation.phone,
                    email=email,
                    verified=False,
                    emergency_available=False,
                )
            else:
                provider = await self._providers.get_by_user_id(user.user_id)
                if (
                    user.role != UserRole.service_provider.value
                    or provider is None
                ):
                    raise ConflictException(
                        "This invitation cannot be used with the existing account."
                    )
                if await self._memberships.has_estate_access(
                    user_id=user.user_id, estate_id=invitation.estate_id
                ):
                    raise ConflictException(
                        "This provider already has access to the estate."
                    )
            await self._memberships.add(
                user_id=user.user_id,
                estate_id=invitation.estate_id,
                property_id=None,
                membership_role=UserRole.service_provider.value,
            )
            await self._events.record(
                estate_id=invitation.estate_id,
                user_id=user.user_id,
                membership_role=UserRole.service_provider.value,
                property_id=None,
                event_type="joined",
                actor_user_id=invitation.created_by_user_id,
            )
            await self._invitations.mark_accepted(invitation, accepted_at=now)
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException(
                "This invitation could not be used because the account or membership already exists."
            )

        await self._db.refresh(user)
        return AuthService._build_auth_response(user)
