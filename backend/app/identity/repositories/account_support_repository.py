from sqlalchemy import func, select
from app.identity.models.account_support import AccountPreference, OperationalNotification, RecoveryGrant
from app.identity.models.user import User
from app.identity.models.estate_membership import EstateMembership


class AccountSupportRepository:
    def __init__(self, db):
        self._db = db

    async def preference(self, user_id: int):
        return await self._db.get(AccountPreference, user_id)

    async def save_preference(self, user_id: int, enabled: bool):
        row = await self.preference(user_id)
        if row is None:
            row = AccountPreference(user_id=user_id)
            self._db.add(row)
        row.maintenance_notifications = enabled
        await self._db.flush()
        return row

    async def notify(self, *, estate_id: int, user_ids: set[int], kind: str, resource_id: int):
        # Re-check persisted membership and preferences; no cross-estate recipients.
        recipients = (await self._db.execute(select(EstateMembership.user_id).join(
            User, User.user_id == EstateMembership.user_id).outerjoin(
            AccountPreference, AccountPreference.user_id == User.user_id).where(
                EstateMembership.estate_id == estate_id,
                EstateMembership.user_id.in_(user_ids),
                EstateMembership.membership_role.in_(['resident', 'hoa_admin', 'service_provider']),
                User.role.in_(['resident', 'hoa_admin', 'service_provider']),
                func.coalesce(AccountPreference.maintenance_notifications, True)).distinct())).scalars().all()
        self._db.add_all([OperationalNotification(estate_id=estate_id, user_id=user_id,
            kind=kind, resource_id=resource_id) for user_id in recipients])
        await self._db.flush()

    async def notify_admins(self, *, estate_id: int, kind: str, resource_id: int):
        ids = (await self._db.execute(select(EstateMembership.user_id).join(
            User, User.user_id == EstateMembership.user_id).where(
                EstateMembership.estate_id == estate_id,
                EstateMembership.membership_role == 'hoa_admin', User.role == 'hoa_admin'))).scalars().all()
        await self.notify(estate_id=estate_id, user_ids=set(ids), kind=kind, resource_id=resource_id)

    async def notifications(self, estate_id: int, user_id: int, offset: int, limit: int):
        filters = (OperationalNotification.estate_id == estate_id, OperationalNotification.user_id == user_id)
        total = await self._db.scalar(select(func.count()).select_from(OperationalNotification).where(*filters))
        rows = (await self._db.execute(select(OperationalNotification).where(*filters).order_by(
            OperationalNotification.notification_id.desc()).offset(offset).limit(limit))).scalars().all()
        return rows, total

    async def notification(self, estate_id: int, user_id: int, notification_id: int):
        return (await self._db.execute(select(OperationalNotification).where(
            OperationalNotification.estate_id == estate_id, OperationalNotification.user_id == user_id,
            OperationalNotification.notification_id == notification_id).with_for_update())).scalar_one_or_none()

    async def add_grant(self, **values):
        self._db.add(RecoveryGrant(**values))
        await self._db.flush()

    async def grant(self, digest: str):
        return (await self._db.execute(select(RecoveryGrant).where(
            RecoveryGrant.token_digest == digest).with_for_update())).scalar_one_or_none()

    async def lock_user(self, user_id: int):
        return (await self._db.execute(select(User).where(User.user_id == user_id)
            .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()

    async def flush(self):
        await self._db.flush()
