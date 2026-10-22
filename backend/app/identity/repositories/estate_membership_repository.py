from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.property.models.property import Property


class EstateMembershipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def lock_in_estate(self, *, membership_id: int, estate_id: int):
        return (await self._db.execute(select(EstateMembership).where(
            EstateMembership.membership_id == membership_id,
            EstateMembership.estate_id == estate_id).with_for_update())).scalar_one_or_none()

    async def flush(self) -> None:
        await self._db.flush()

    async def has_estate_access(self, *, user_id: int, estate_id: int) -> bool:
        result = await self._db.execute(
            select(EstateMembership.membership_id).where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def has_membership_role_for_user(
        self, *, user_id: int, membership_role: str
    ) -> bool:
        result = await self._db.execute(
            select(EstateMembership.membership_id)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.membership_role == membership_role,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def list_for_user_and_estate(
        self, *, user_id: int, estate_id: int
    ) -> list[EstateMembership]:
        result = await self._db.execute(
            select(EstateMembership)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
            .order_by(EstateMembership.membership_id)
        )
        return list(result.scalars().all())

    async def get_for_user_and_estate(
        self, *, user_id: int, estate_id: int
    ) -> EstateMembership | None:
        result = await self._db.execute(
            select(EstateMembership)
            .where(
                EstateMembership.user_id == user_id,
                EstateMembership.estate_id == estate_id,
            )
            .order_by(EstateMembership.membership_id)
            .limit(1)
        )
        return result.scalars().first()

    async def list_for_user(self, *, user_id: int) -> list[EstateMembership]:
        """Every membership row for a user, across all estates, in stable order."""
        result = await self._db.execute(
            select(EstateMembership)
            .where(EstateMembership.user_id == user_id)
            .order_by(EstateMembership.estate_id, EstateMembership.membership_id)
        )
        return list(result.scalars().all())

    async def list_estate_ids(
        self, *, user_id: int, membership_role: str | None = None
    ) -> list[int]:
        """The distinct estate ids a user holds a membership in.

        Used for cross-entity eligibility checks (may this resident review that
        provider?) where the answer is set intersection, not a single estate.
        """
        stmt = select(EstateMembership.estate_id).where(
            EstateMembership.user_id == user_id
        )
        if membership_role is not None:
            stmt = stmt.where(EstateMembership.membership_role == membership_role)
        result = await self._db.execute(stmt.distinct())
        return [row[0] for row in result.all()]

    async def get_for_user_and_property(
        self, *, user_id: int, property_id: int
    ) -> EstateMembership | None:
        result = await self._db.execute(
            select(EstateMembership).where(
                EstateMembership.user_id == user_id,
                EstateMembership.property_id == property_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> EstateMembership:
        membership = EstateMembership(**fields)
        self._db.add(membership)
        await self._db.commit()
        await self._db.refresh(membership)
        return membership

    async def add(self, **fields: object) -> EstateMembership:
        """Add a membership without committing; the caller commits once."""
        membership = EstateMembership(**fields)
        self._db.add(membership)
        await self._db.flush()
        return membership

    async def list_contacts_for_role(
        self, *, estate_id: int, membership_role: str
    ) -> list[tuple[str | None, str]]:
        """The (name, email) of every member holding one role in one estate.

        This is how the estate's own HOA administrators are found for a
        notification: the recipients are the administrators' own account
        addresses, resolved from persisted membership rather than a configured
        address that could belong to the wrong estate. Only rows whose user still
        has an email are returned.
        """
        result = await self._db.execute(
            select(User.full_name, User.email)
            .join(EstateMembership, EstateMembership.user_id == User.user_id)
            .where(
                EstateMembership.estate_id == estate_id,
                EstateMembership.membership_role == membership_role,
                User.email.is_not(None),
            )
            .order_by(User.user_id)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_id_in_estate(
        self, *, membership_id: int, estate_id: int
    ) -> EstateMembership | None:
        """Fetch one membership only when it belongs to the requested estate.

        An estate-scoped lookup is what turns a foreign-estate id into a 404 and
        never into a 403 that would confirm the row exists.
        """
        result = await self._db.execute(
            select(EstateMembership).where(
                EstateMembership.membership_id == membership_id,
                EstateMembership.estate_id == estate_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _members_statement(*, estate_id: int, role: str | None):
        stmt = (
            select(
                EstateMembership.membership_id,
                EstateMembership.membership_role,
                EstateMembership.created_at,
                User.user_id,
                User.full_name,
                User.email,
                Property.unit_no,
            )
            .join(User, User.user_id == EstateMembership.user_id, isouter=True)
            .join(Property, Property.unit_id == EstateMembership.property_id, isouter=True)
            .where(EstateMembership.estate_id == estate_id)
        )
        if role is not None:
            stmt = stmt.where(EstateMembership.membership_role == role)
        # Newest first, with the id as a stable tie-break within a timestamp.
        return stmt.order_by(
            EstateMembership.created_at.desc(), EstateMembership.membership_id.desc()
        )

    async def list_members_for_estate(
        self,
        *,
        estate_id: int,
        role: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ):
        """One page of members with their account and unit labels."""
        result = await self._db.execute(
            self._members_statement(estate_id=estate_id, role=role)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def count_members_for_estate(self, *, estate_id: int, role: str | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(EstateMembership)
            .where(EstateMembership.estate_id == estate_id)
        )
        if role is not None:
            stmt = stmt.where(EstateMembership.membership_role == role)
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    async def delete(self, membership: EstateMembership) -> None:
        """Remove a membership row without committing; the caller commits once."""
        await self._db.delete(membership)
        await self._db.flush()
