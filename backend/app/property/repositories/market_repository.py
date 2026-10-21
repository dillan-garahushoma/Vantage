"""Current property market queries. Every domain lookup includes estate_id."""
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.property.models.market import (MarketingAuthority, MarketingRequest, MarketListing,
                                       ListingPriceEvent, MarketTransaction, MarketEvent)
from app.property.models.property import Property


class MarketRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def lock_property(self, estate_id, property_id):
        return (await self._db.execute(select(Property).where(
            Property.estate_id == estate_id, Property.unit_id == property_id)
            .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()

    async def member_user(self, estate_id, user_id):
        return (await self._db.execute(select(User).join(EstateMembership,
            EstateMembership.user_id == User.user_id).where(
                EstateMembership.estate_id == estate_id, User.user_id == user_id).distinct())).scalar_one_or_none()

    async def active_authority(self, estate_id, property_id):
        return (await self._db.execute(select(MarketingAuthority).where(
            MarketingAuthority.estate_id == estate_id, MarketingAuthority.property_id == property_id,
            MarketingAuthority.revoked_at.is_(None)))).scalar_one_or_none()

    async def get(self, model, estate_id, key, *, refresh=False):
        column = model.__mapper__.primary_key[0]
        return (await self._db.execute(select(model).where(model.estate_id == estate_id, column == key)
            .execution_options(populate_existing=refresh))).scalar_one_or_none()

    async def listing_for_request(self, estate_id, request_id):
        return (await self._db.execute(select(MarketListing).where(
            MarketListing.estate_id == estate_id, MarketListing.request_id == request_id))).scalar_one_or_none()

    async def open_request(self, estate_id, property_id):
        return (await self._db.execute(select(MarketingRequest).where(
            MarketingRequest.estate_id == estate_id, MarketingRequest.property_id == property_id,
            MarketingRequest.status.in_(['pending', 'approved', 'listed'])))).scalar_one_or_none()

    async def add(self, model, **values):
        row = model(**values)
        self._db.add(row)
        await self._db.flush()
        return row

    async def flush(self):
        await self._db.flush()

    @staticmethod
    def participants(actor_id, is_admin, is_agent):
        if is_admin:
            return True
        return or_(MarketingRequest.requester_id == actor_id,
                   MarketingRequest.agent_id == actor_id if is_agent else False)

    async def collection(self, model, estate_id, *, actor_id, is_admin, is_agent,
                         offset, limit, purpose=None, entity_id=None, entity_type=None):
        stmt = select(model).where(model.estate_id == estate_id)
        if model is MarketingAuthority:
            if not is_admin:
                stmt = stmt.where(model.representative_id == actor_id)
        elif model is MarketingRequest:
            stmt = stmt.where(self.participants(actor_id, is_admin, is_agent))
        elif model is MarketListing:
            stmt = stmt.join(MarketingRequest, (MarketingRequest.request_id == model.request_id)
                             & (MarketingRequest.estate_id == estate_id)).where(or_(
                                 model.status == 'active', self.participants(actor_id, is_admin, is_agent)))
        elif model is MarketTransaction:
            stmt = stmt.join(MarketListing, (MarketListing.listing_id == model.listing_id)
                             & (MarketListing.estate_id == estate_id)).join(MarketingRequest,
                                 (MarketingRequest.request_id == MarketListing.request_id)
                                 & (MarketingRequest.estate_id == estate_id)).where(
                                     self.participants(actor_id, is_admin, is_agent))
        elif model is ListingPriceEvent:
            stmt = stmt.where(model.listing_id == entity_id)
        elif model is MarketEvent:
            stmt = stmt.where(model.entity_type == entity_type, model.entity_id == entity_id)
        if purpose is not None:
            stmt = stmt.where(model.purpose == purpose)
        total = (await self._db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self._db.execute(stmt.order_by(model.__mapper__.primary_key[0].desc())
            .offset(offset).limit(limit))).scalars().all()
        return rows, total
