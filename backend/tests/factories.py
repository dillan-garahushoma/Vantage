from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.security import hash_password
from app.identity.models.estate_membership import EstateMembership
from app.identity.models.user import User
from app.identity.repositories.estate_membership_repository import EstateMembershipRepository
from app.identity.repositories.user_repository import UserRepository
from app.property.models.estate import Estate
from app.property.models.property import Property
from app.property.repositories.property_repository import PropertyRepository
from app.providers.models.service_provider import ServiceProvider
from app.providers.repositories.service_provider_repository import ServiceProviderRepository


@dataclass
class EstateWorld:
    estate_a: Estate
    estate_b: Estate
    # Estate A actors
    hoa_admin_a: User
    resident_a1: User
    resident_a2: User
    provider_user_a: User
    provider_profile_a: ServiceProvider
    property_a1: Property
    property_a2: Property
    property_a3: Property
    # Estate B actors
    hoa_admin_b: User
    resident_b1: User
    resident_b2: User
    provider_user_b: User
    provider_profile_b: ServiceProvider
    property_b1: Property
    property_b2: Property
    # Cross & Multi-unit users
    cross_user: User  # hoa_admin in Estate A, resident in Estate B
    # resident_a1 has memberships in both property_a1 and property_a3 in Estate A


async def build_two_estate_world(db: AsyncSession) -> EstateWorld:
    user_repo = UserRepository(db)
    membership_repo = EstateMembershipRepository(db)
    property_repo = PropertyRepository(db)
    provider_repo = ServiceProviderRepository(db)

    # 1. Estates
    estate_a = Estate(
        name="Zambezi Country Estate",
        suburb="Montana",
        city="Pretoria",
        province="Gauteng",
        description="Secure residential estate in Pretoria North",
    )
    estate_b = Estate(
        name="Silver Lakes Golf Estate",
        suburb="Silver Lakes",
        city="Pretoria",
        province="Gauteng",
        description="Golf and wildlife estate in Pretoria East",
    )
    db.add_all([estate_a, estate_b])
    await db.commit()
    await db.refresh(estate_a)
    await db.refresh(estate_b)

    pw_hash = hash_password("ValidPassword123!")

    # 2. Users
    hoa_admin_a = await user_repo.create(
        full_name="Admin Zambezi",
        email="admin_a@valora.test",
        password_hash=pw_hash,
        role=UserRole.hoa_admin.value,
    )
    resident_a1 = await user_repo.create(
        full_name="Resident Alice",
        email="res_a1@valora.test",
        password_hash=pw_hash,
        role=UserRole.resident.value,
    )
    resident_a2 = await user_repo.create(
        full_name="Resident Aaron",
        email="res_a2@valora.test",
        password_hash=pw_hash,
        role=UserRole.resident.value,
    )
    provider_user_a = await user_repo.create(
        full_name="Plumber Pete",
        email="prov_a@valora.test",
        password_hash=pw_hash,
        role=UserRole.service_provider.value,
    )

    hoa_admin_b = await user_repo.create(
        full_name="Admin Silver Lakes",
        email="admin_b@valora.test",
        password_hash=pw_hash,
        role=UserRole.hoa_admin.value,
    )
    resident_b1 = await user_repo.create(
        full_name="Resident Bob",
        email="res_b1@valora.test",
        password_hash=pw_hash,
        role=UserRole.resident.value,
    )
    resident_b2 = await user_repo.create(
        full_name="Resident Brenda",
        email="res_b2@valora.test",
        password_hash=pw_hash,
        role=UserRole.resident.value,
    )
    provider_user_b = await user_repo.create(
        full_name="Electrician Emma",
        email="prov_b@valora.test",
        password_hash=pw_hash,
        role=UserRole.service_provider.value,
    )

    cross_user = await user_repo.create(
        full_name="Cross Estate User",
        email="cross@valora.test",
        password_hash=pw_hash,
        role=UserRole.hoa_admin.value,  # Global role hoa_admin
    )

    # `UserRepository.create` does not accept `hoa_approved` - it is not part of the
    # repository's provisioning contract - so the flag is applied to the models
    # after creation and committed once, which is all these fixtures ever needed.
    # (`hoa_approved` gates no authorisation: see docs/PILOT_RUNBOOK.md.)
    for user in (
        hoa_admin_a,
        resident_a1,
        resident_a2,
        provider_user_a,
        hoa_admin_b,
        resident_b1,
        resident_b2,
        provider_user_b,
        cross_user,
    ):
        user.hoa_approved = True
    await db.commit()

    # 3. Properties
    prop_a1 = await property_repo.create(
        estate_id=estate_a.estate_id,
        unit_no="A-101",
        complex_name=estate_a.name,
        street_address="101 Zambezi Drive",
        suburb="Montana",
        size_m2=Decimal("120.00"),
        bedrooms=3,
        bathrooms=2,
    )
    prop_a2 = await property_repo.create(
        estate_id=estate_a.estate_id,
        unit_no="A-102",
        complex_name=estate_a.name,
        street_address="102 Zambezi Drive",
        suburb="Montana",
        size_m2=Decimal("95.00"),
        bedrooms=2,
        bathrooms=1,
    )
    prop_a3 = await property_repo.create(
        estate_id=estate_a.estate_id,
        unit_no="A-103",
        complex_name=estate_a.name,
        street_address="103 Zambezi Drive",
        suburb="Montana",
        size_m2=Decimal("150.00"),
        bedrooms=4,
        bathrooms=3,
    )

    prop_b1 = await property_repo.create(
        estate_id=estate_b.estate_id,
        unit_no="B-201",
        complex_name=estate_b.name,
        street_address="201 Fairway Lane",
        suburb="Silver Lakes",
        size_m2=Decimal("180.00"),
        bedrooms=4,
        bathrooms=3,
    )
    prop_b2 = await property_repo.create(
        estate_id=estate_b.estate_id,
        unit_no="B-202",
        complex_name=estate_b.name,
        street_address="202 Fairway Lane",
        suburb="Silver Lakes",
        size_m2=Decimal("110.00"),
        bedrooms=2,
        bathrooms=2,
    )

    # 4. Service Providers
    provider_a = await provider_repo.create(
        full_name="Pete Plumbing Services",
        trade="plumbing",
        phone="0821234567",
        email="pete@peteplumbing.test",
        verified=True,
        emergency_available=True,
    )
    provider_b = await provider_repo.create(
        full_name="Emma Electrical",
        trade="electrical",
        phone="0837654321",
        email="emma@emmaelectrical.test",
        verified=True,
        emergency_available=True,
    )

    # `ServiceProviderRepository.create` does not take `user_id` either, so the link
    # between a provider profile and its provider user account is set on the models
    # afterwards, mirroring the flag handling above.
    provider_a.user_id = provider_user_a.user_id
    provider_b.user_id = provider_user_b.user_id
    await db.commit()

    # 5. Estate Memberships
    # Estate A
    await membership_repo.create(
        user_id=hoa_admin_a.user_id,
        estate_id=estate_a.estate_id,
        property_id=None,
        membership_role=UserRole.hoa_admin.value,
    )
    await membership_repo.create(
        user_id=resident_a1.user_id,
        estate_id=estate_a.estate_id,
        property_id=prop_a1.unit_id,
        membership_role=UserRole.resident.value,
    )
    # resident_a1 with two property memberships in the same estate:
    await membership_repo.create(
        user_id=resident_a1.user_id,
        estate_id=estate_a.estate_id,
        property_id=prop_a3.unit_id,
        membership_role=UserRole.resident.value,
    )
    await membership_repo.create(
        user_id=resident_a2.user_id,
        estate_id=estate_a.estate_id,
        property_id=prop_a2.unit_id,
        membership_role=UserRole.resident.value,
    )
    await membership_repo.create(
        user_id=provider_user_a.user_id,
        estate_id=estate_a.estate_id,
        property_id=None,
        membership_role=UserRole.service_provider.value,
    )

    # Estate B
    await membership_repo.create(
        user_id=hoa_admin_b.user_id,
        estate_id=estate_b.estate_id,
        property_id=None,
        membership_role=UserRole.hoa_admin.value,
    )
    await membership_repo.create(
        user_id=resident_b1.user_id,
        estate_id=estate_b.estate_id,
        property_id=prop_b1.unit_id,
        membership_role=UserRole.resident.value,
    )
    await membership_repo.create(
        user_id=resident_b2.user_id,
        estate_id=estate_b.estate_id,
        property_id=prop_b2.unit_id,
        membership_role=UserRole.resident.value,
    )
    await membership_repo.create(
        user_id=provider_user_b.user_id,
        estate_id=estate_b.estate_id,
        property_id=None,
        membership_role=UserRole.service_provider.value,
    )

    # Cross User: HOA admin in Estate A, Resident in Estate B
    await membership_repo.create(
        user_id=cross_user.user_id,
        estate_id=estate_a.estate_id,
        property_id=None,
        membership_role=UserRole.hoa_admin.value,
    )
    await membership_repo.create(
        user_id=cross_user.user_id,
        estate_id=estate_b.estate_id,
        property_id=prop_b2.unit_id,
        membership_role=UserRole.resident.value,
    )

    return EstateWorld(
        estate_a=estate_a,
        estate_b=estate_b,
        hoa_admin_a=hoa_admin_a,
        resident_a1=resident_a1,
        resident_a2=resident_a2,
        provider_user_a=provider_user_a,
        provider_profile_a=provider_a,
        property_a1=prop_a1,
        property_a2=prop_a2,
        property_a3=prop_a3,
        hoa_admin_b=hoa_admin_b,
        resident_b1=resident_b1,
        resident_b2=resident_b2,
        provider_user_b=provider_user_b,
        provider_profile_b=provider_b,
        property_b1=prop_b1,
        property_b2=prop_b2,
        cross_user=cross_user,
    )
