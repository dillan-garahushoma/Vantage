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


class AnnouncementService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AnnouncementRepository(db)

    async def list_announcements(
        self, user: User, *, page: int, page_size: int, include_expired: bool = False
    ) -> PaginatedAnnouncementsResponse:
        # only HOA admins may see expired announcements
        show_expired = include_expired and user.role == UserRole.hoa_admin.value
        now = utcnow()
        items = await self._repo.search(
            offset=(page - 1) * page_size,
            limit=page_size,
            include_expired=show_expired,
            now=now,
        )
        total = await self._repo.count(include_expired=show_expired, now=now)
        return PaginatedAnnouncementsResponse(
            count=total,
            page=page,
            page_size=page_size,
            announcements=[AnnouncementResponse.model_validate(a) for a in items],
        )

    async def get_announcement(self, announcement_id: int, user: User) -> AnnouncementResponse:
        announcement = await self._get_or_404(announcement_id)
        is_expired = announcement.expires_at is not None and announcement.expires_at <= utcnow()
        if is_expired and user.role != UserRole.hoa_admin.value:
            raise NotFoundException(f"Announcement with id {announcement_id} was not found.")
        return AnnouncementResponse.model_validate(announcement)

    async def create_announcement(
        self, payload: AnnouncementCreate, admin: User
    ) -> AnnouncementResponse:
        announcement = await self._repo.create(
            title=payload.title.strip(),
            message=payload.message.strip(),
            created_by=admin.user_id,
            expires_at=payload.expires_at,
        )
        return AnnouncementResponse.model_validate(announcement)

    async def update_announcement(
        self, announcement_id: int, payload: AnnouncementUpdate
    ) -> AnnouncementResponse:
        announcement = await self._get_or_404(announcement_id)
        changes = payload.model_dump(exclude_unset=True)
        for required_field in ("title", "message"):
            if required_field in changes and changes[required_field] is None:
                del changes[required_field]
        for field, value in changes.items():
            setattr(announcement, field, value)
        announcement = await self._repo.save(announcement)
        return AnnouncementResponse.model_validate(announcement)

    async def delete_announcement(self, announcement_id: int) -> None:
        announcement = await self._get_or_404(announcement_id)
        await self._repo.delete(announcement)

    async def _get_or_404(self, announcement_id: int) -> Announcement:
        announcement = await self._repo.get_by_id(announcement_id)
        if announcement is None:
            raise NotFoundException(f"Announcement with id {announcement_id} was not found.")
        return announcement
