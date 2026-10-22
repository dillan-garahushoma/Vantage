"""Small local account support; notices persist in the business transaction."""
import hashlib
import logging
import secrets
from datetime import timedelta
from app.common.datetime_utils import utcnow
from app.common.pagination import Page
from app.core.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException, RateLimitException
from app.core.security import hash_password
from app.identity.repositories.account_support_repository import AccountSupportRepository
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.account_support import NotificationResponse, PreferenceResponse
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.identity.services.join_attempt_limiter import JoinAttemptLimiter
from app.notifications.email import EmailMessage, NullEmailSender, build_email_sender

logger = logging.getLogger(__name__)
recovery_limiter = JoinAttemptLimiter()


class AccountSupportService:
    def __init__(self, db, *, sender=None):
        self._db = db
        self._repo = AccountSupportRepository(db)
        self._users = UserRepository(db)
        self._auth = EstateAuthorizationService(db)
        self._settings = get_settings()
        self._sender = sender if sender is not None else build_email_sender(self._settings)

    async def preferences(self, actor):
        row = await self._repo.preference(actor.user_id)
        return PreferenceResponse.model_validate(row) if row else PreferenceResponse()

    async def update_preferences(self, actor, payload):
        row = await self._repo.save_preference(actor.user_id, payload.maintenance_notifications)
        await self._db.commit()
        return PreferenceResponse.model_validate(row)

    async def notifications(self, actor, estate_id, page, size):
        await self._auth.resolve_access(actor, estate_id)
        rows, total = await self._repo.notifications(estate_id, actor.user_id, (page - 1) * size, size)
        return Page(items=[NotificationResponse.model_validate(row) for row in rows], total=total, page=page, size=size)

    async def mark_read(self, actor, estate_id, notification_id):
        await self._auth.resolve_access(actor, estate_id)
        row = await self._repo.notification(estate_id, actor.user_id, notification_id)
        if row is None:
            raise NotFoundException('Notification not found.')
        if row.read_at is None:
            row.read_at = utcnow()
            await self._repo.flush()
            await self._db.commit()
        return NotificationResponse.model_validate(row)

    async def request_recovery(self, email: str, *, requester: str):
        # Uniform response, including disabled mail and rate limiting. Tokens are
        # never returned by HTTP, logged or stored as plaintext.
        email = email.strip().lower()
        for key in (f'ip:{requester}', f'email:{email}'):
            try:
                recovery_limiter.ensure_allowed(key)
            except RateLimitException:
                return
        for key in (f'ip:{requester}', f'email:{email}'):
            recovery_limiter.record_failure(key)
        user = await self._users.get_by_email(email)
        if user is None or user.role not in ('resident', 'hoa_admin', 'service_provider', 'platform_admin'):
            return
        if isinstance(self._sender, NullEmailSender):
            return
        user = await self._repo.lock_user(user.user_id)
        token = secrets.token_urlsafe(32)
        await self._repo.add_grant(user_id=user.user_id,
            token_digest=hashlib.sha256(token.encode()).hexdigest(), expires_at=utcnow() + timedelta(minutes=30))
        try:
            await self._sender.send(EmailMessage(to=(user.email,), subject='VALORA account recovery',
                body=f'Use this one-time recovery code within 30 minutes:\n{token}\n'
                     'Submit it through VALORA account recovery. Ignore this message if you did not request it.'))
        except Exception:
            await self._db.rollback()
            logger.warning('Account recovery delivery failed; no grant was retained.')
            return
        await self._db.commit()

    async def confirm_recovery(self, payload):
        digest = hashlib.sha256(payload.token.encode()).hexdigest()
        grant = await self._repo.grant(digest)
        if grant is None or grant.used_at is not None or grant.expires_at <= utcnow():
            raise BadRequestException('Recovery code is invalid or expired.')
        user = await self._repo.lock_user(grant.user_id)
        if user is None or user.role not in ('resident', 'hoa_admin', 'service_provider', 'platform_admin'):
            raise BadRequestException('Recovery code is invalid or expired.')
        # Only grants issued since the latest successful password change survive.
        if user.password_changed_at and grant.expires_at - timedelta(minutes=30) <= user.password_changed_at:
            raise BadRequestException('Recovery code is invalid or expired.')
        user.password_hash = hash_password(payload.password.get_secret_value())
        user.password_changed_at = utcnow()
        user.auth_version += 1
        grant.used_at = utcnow()
        await self._repo.flush()
        await self._db.commit()
