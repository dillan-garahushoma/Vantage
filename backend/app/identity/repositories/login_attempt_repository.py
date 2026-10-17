"""Login attempt repository — persistence for authentication security monitoring.

Records every authentication attempt so the auth service can enforce a
per-account failure window (rate limiting) and so operators have an audit
trail. Repositories flush; the service commits.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.login_attempt import LoginAttempts


class LoginAttemptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        *,
        email: str,
        ip_address: str | None,
        successful: bool,
    ) -> None:
        """Stage one attempt for insertion. The calling service commits."""
        self._db.add(
            LoginAttempts(email=email, ip_address=ip_address, successful=successful)
        )
        await self._db.flush()

    async def count_recent_failures(self, *, email: str, since: datetime) -> int:
        """Count failed attempts for an email at or after ``since`` (UTC)."""
        result = await self._db.execute(
            select(func.count())
            .select_from(LoginAttempts)
            .where(
                LoginAttempts.email == email,
                LoginAttempts.successful.is_(False),
                LoginAttempts.attempted_at >= since,
            )
        )
        return int(result.scalar_one())
