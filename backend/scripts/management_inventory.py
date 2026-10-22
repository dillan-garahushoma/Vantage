"""Read-only role/archive counts. No emails, user IDs or secrets are emitted."""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.identity.models.user import User  # noqa: E402
from app.identity.models.estate_membership import EstateMembership  # noqa: E402
from app.property.models.investment_scenario import InvestmentScenario  # noqa: E402
from app.property.models.market import MarketingAuthority, MarketingRequest, MarketListing, MarketTransaction  # noqa: E402
import app.db.database  # noqa: E402, F401


async def inventory():
    engine = create_async_engine(get_settings().DATABASE_URL, echo=False)
    try:
        async with async_sessionmaker(engine)() as db:
            roles = (await db.execute(select(User.role, func.count()).group_by(User.role))).all()
            memberships = (await db.execute(select(EstateMembership.membership_role, func.count())
                .group_by(EstateMembership.membership_role))).all()
            archive = {}
            for model in (InvestmentScenario, MarketingAuthority, MarketingRequest, MarketListing, MarketTransaction):
                archive[model.__tablename__] = await db.scalar(select(func.count()).select_from(model))
            print(json.dumps({'account_role_counts': dict(roles), 'membership_role_counts': dict(memberships),
                'retained_archive_counts': archive, 'writes': 0}, indent=2))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(inventory())
