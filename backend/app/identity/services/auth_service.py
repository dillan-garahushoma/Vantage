"""Authentication application service — orchestrates registration and login use cases."""
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.common.validators import normalise_email
from app.core.config import get_settings
from app.core.exceptions import ConflictException, CredentialsException, RateLimitException, ForbiddenException
from app.core.security import create_access_token, hash_password, verify_password
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.login_attempt_repository import LoginAttemptRepository
from app.identity.repositories.user_repository import UserRepository
from app.identity.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse, ProvisionAccountRequest
from app.property.repositories.estate_repository import EstateRepository
from app.providers.repositories.service_provider_repository import ServiceProviderRepository


# Precomputed bcrypt hash for constant-time dummy comparison when user is not found
DUMMY_PASSWORD_HASH = "$2b$12$e80e1yJ0M.685i37g0nE3.YtB9Q.q51Nrk2GZ01/5eU2mB2z4Q8/."


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = UserRepository(db)
        self._attempt_repo = LoginAttemptRepository(db)
        self._estate_repo = EstateRepository(db)
        self._membership_repo = EstateMembershipRepository(db)
        self._provider_repo = ServiceProviderRepository(db)
        self._settings = get_settings()

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        if payload.account_type != 'resident':
            raise ForbiddenException('Public registration creates residents only.')
        return await self._create_account(payload)

    async def provision(self, payload: ProvisionAccountRequest, operator: User) -> UserResponse:
        if operator.role != UserRole.platform_admin.value:
            raise ForbiddenException('Only an operator may provision trusted accounts.')
        return (await self._create_account(payload)).user

    async def _create_account(self, payload: ProvisionAccountRequest) -> AuthResponse:
        email = normalise_email(payload.email)

        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise ConflictException("An account with this email already exists.")

        password_hash = hash_password(payload.password)

        if payload.account_type == "estate_admin":
            return await self._register_estate_admin(payload, email=email, password_hash=password_hash)
        if payload.account_type == "service_provider":
            return await self._register_service_provider(
                payload, email=email, password_hash=password_hash
            )

        # resident: the original, single-row registration path, unchanged.
        user = await self._repo.create(
            full_name=payload.full_name,
            email=email,
            password_hash=password_hash,
            role=UserRole.resident.value,
            phoneno=payload.phoneno,
            unit_no=payload.unit_no,
        )

        return self._build_auth_response(user)

    async def _register_estate_admin(
        self, payload: RegisterRequest, *, email: str, password_hash: str
    ) -> AuthResponse:
        """Register an estate admin and their estate in ONE transaction.

        The user (role hoa_admin), the estate (is_demo=false) and an estate-level
        membership (hoa_admin, no property) are added and flushed together, then
        committed once. A duplicate estate name is a 409 and leaves no orphan user.
        """
        estate_payload = payload.estate
        assert estate_payload is not None  # guaranteed by the schema validator
        name = estate_payload.name.strip()

        if await self._estate_repo.get_by_name(name) is not None:
            raise ConflictException("An estate with this name already exists.")

        try:
            user = await self._repo.add(
                full_name=payload.full_name,
                email=email,
                password_hash=password_hash,
                role=UserRole.hoa_admin.value,
                phoneno=payload.phoneno,
            )
            estate = await self._estate_repo.add(
                name=name,
                suburb=estate_payload.suburb.strip(),
                city=estate_payload.city.strip(),
                province=estate_payload.province.strip(),
                description=estate_payload.description,
                is_demo=False,
            )
            await self._membership_repo.add(
                user_id=user.user_id,
                estate_id=estate.estate_id,
                property_id=None,
                membership_role=UserRole.hoa_admin.value,
            )
            await self._db.commit()
        except IntegrityError:
            # A concurrent signup took the estate name between the check and the
            # commit; nothing of ours may survive.
            await self._db.rollback()
            raise ConflictException("An estate with this name already exists.")

        await self._db.refresh(user)
        return self._build_auth_response(user)

    async def _register_service_provider(
        self, payload: RegisterRequest, *, email: str, password_hash: str
    ) -> AuthResponse:
        """Register a service provider user and their linked profile in ONE transaction.

        The user (role service_provider) and a provider profile (user_id linked,
        email = the account's, verified=false, emergency_available=false) are
        added together. No estate membership is created: provider access to an
        estate is provisioned separately.
        """
        provider_payload = payload.provider
        assert provider_payload is not None  # guaranteed by the schema validator

        if await self._provider_repo.get_by_email(email) is not None:
            raise ConflictException("A service provider with this email already exists.")

        try:
            user = await self._repo.add(
                full_name=payload.full_name,
                email=email,
                password_hash=password_hash,
                role=UserRole.service_provider.value,
                phoneno=payload.phoneno,
            )
            await self._provider_repo.add(
                user_id=user.user_id,
                full_name=payload.full_name.strip(),
                trade=provider_payload.trade.strip(),
                phone=provider_payload.phone.strip(),
                email=email,
                verified=False,
                emergency_available=False,
            )
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException("A service provider with this email already exists.")

        await self._db.refresh(user)
        return self._build_auth_response(user)

    async def login(
        self, payload: LoginRequest, *, ip_address: str | None = None
    ) -> AuthResponse:
        email = normalise_email(payload.email)

        window_start = utcnow() - timedelta(minutes=self._settings.LOGIN_LOCKOUT_WINDOW_MINUTES)
        recent_failures = await self._attempt_repo.count_recent_failures(
            email=email, since=window_start
        )
        if recent_failures >= self._settings.LOGIN_MAX_FAILED_ATTEMPTS:
            raise RateLimitException(
                "Too many failed login attempts. Please try again later."
            )

        user = await self._repo.get_by_email(email)

        if user is None:
            verify_password(payload.password, DUMMY_PASSWORD_HASH)
            await self._record_attempt(email=email, ip_address=ip_address, successful=False)
            raise CredentialsException("Invalid email or password.")

        if not verify_password(payload.password, user.password_hash):
            await self._record_attempt(email=email, ip_address=ip_address, successful=False)
            raise CredentialsException("Invalid email or password.")

        if user.role in ('investor', 'estate_agent', 'casual_visitor'):
            raise ForbiddenException('This account role has been retired. Contact the estate office.')

        await self._record_attempt(email=email, ip_address=ip_address, successful=True)
        return self._build_auth_response(user)

    async def _record_attempt(
        self, *, email: str, ip_address: str | None, successful: bool
    ) -> None:
        await self._attempt_repo.record(
            email=email, ip_address=ip_address, successful=successful
        )
        await self._db.commit()

    async def get_current_user(self, user_id: int) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise CredentialsException("User not found.")
        return UserResponse.model_validate(user)

    @staticmethod
    def _build_auth_response(user: User) -> AuthResponse:
        token = create_access_token({"sub": str(user.user_id), "role": user.role,
                                     "version": getattr(user, 'auth_version', 0) or 0})
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
