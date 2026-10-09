from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utcnow
from app.common.enums import UserRole
from app.community.models.announcement import Announcement
from app.community.repositories.announcement_repository import AnnouncementRepository
from app.community.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
    PaginatedAnnouncementsResponse,
)
from app.core.exceptions import NotFoundException
from app.identity.models.user import User
from app.identity.services.estate_authorization_service import EstateAuthorizationService


class AnnouncementService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AnnouncementRepository(db)
        self._estate_authorization = EstateAuthorizationService(db)

    async def list_announcements(
        self, user: User, *, page: int, page_size: int, estate_id: int, include_expired: bool = False
    ) -> PaginatedAnnouncementsResponse:
        access = await self._estate_authorization.resolve_access(user, estate_id=estate_id)
        show_expired = include_expired and access.is_estate_admin
        now = utcnow()
        items = await self._repo.search(
            offset=(page - 1) * page_size,
            limit=page_size,
            include_expired=show_expired,
            now=now,
            estate_id=estate_id,
        )
        total = await self._repo.count(include_expired=show_expired, now=now, estate_id=estate_id)
        return PaginatedAnnouncementsResponse(
            count=total,
            page=page,
            page_size=page_size,
            announcements=[AnnouncementResponse.model_validate(a) for a in items],
        )

    async def get_announcement(self, announcement_id: int, user: User, *, estate_id: int) -> AnnouncementResponse:
        access = await self._estate_authorization.resolve_access(user, estate_id=estate_id)
        announcement = await self._get_or_404(announcement_id, estate_id=estate_id)
        is_expired = announcement.expires_at is not None and announcement.expires_at <= utcnow()
        if is_expired and not access.is_estate_admin:
            raise NotFoundException(f"Announcement with id {announcement_id} was not found.")
        return AnnouncementResponse.model_validate(announcement)

    async def create_announcement(
        self, payload: AnnouncementCreate, admin: User, *, estate_id: int
    ) -> AnnouncementResponse:
        await self._estate_authorization.require_role(actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,))
        announcement = await self._repo.create(
            title=payload.title.strip(),
            message=payload.message.strip(),
            created_by=admin.user_id,
            estate_id=estate_id,
            expires_at=payload.expires_at,
        )
        return AnnouncementResponse.model_validate(announcement)

    async def update_announcement(
        self, announcement_id: int, payload: AnnouncementUpdate, admin: User, *, estate_id: int
    ) -> AnnouncementResponse:
        await self._estate_authorization.require_role(actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,))
        announcement = await self._get_or_404(announcement_id, estate_id=estate_id)
        changes = payload.model_dump(exclude_unset=True)
        for required_field in ("title", "message"):
            if required_field in changes and changes[required_field] is None:
                del changes[required_field]
        for field, value in changes.items():
            setattr(announcement, field, value)
        announcement = await self._repo.save(announcement)
        return AnnouncementResponse.model_validate(announcement)

    async def delete_announcement(self, announcement_id: int, admin: User, *, estate_id: int) -> None:
        await self._estate_authorization.require_role(actor=admin, estate_id=estate_id, allowed_roles=(UserRole.hoa_admin.value,))
        announcement = await self._get_or_404(announcement_id, estate_id=estate_id)
        await self._repo.delete(announcement)

    async def _get_or_404(self, announcement_id: int, *, estate_id: int) -> Announcement:
        announcement = await self._repo.get_by_id_in_estate(announcement_id=announcement_id, estate_id=estate_id)
        if announcement is None:
            raise NotFoundException(f"Announcement with id {announcement_id} was not found.")
        return announcement
