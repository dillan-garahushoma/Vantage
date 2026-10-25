"""Archived sample estates cannot appear as operational production records."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ForbiddenException, NotFoundException
from app.identity.services.estate_authorization_service import EstateAuthorizationService
from app.property.repositories.estate_repository import EstateRepository
from app.property.services.public_directory_service import PublicDirectoryService


@pytest.fixture
def production(monkeypatch, tmp_path):
    settings = SimpleNamespace(ENVIRONMENT='production', UPLOAD_DIR=tmp_path)
    monkeypatch.setattr('app.core.config.get_settings', lambda: settings)
    monkeypatch.setattr('app.property.services.public_directory_service.get_settings', lambda: settings)
    return settings


def test_public_query_can_exclude_demo_estates_before_pagination():
    sql = str(EstateRepository.public_statement(include_demo=False)).lower()
    assert 'estates.is_demo is false' in sql


@pytest.mark.asyncio
async def test_production_directory_filters_both_the_page_and_total(production):
    service = PublicDirectoryService(AsyncMock())
    service._estates = SimpleNamespace(list_public=AsyncMock(return_value=[]), count_public=AsyncMock(return_value=0))
    assert await service.list_estates(page=2, page_size=6) == ([], 0)
    service._estates.list_public.assert_awaited_once_with(offset=6, limit=6, q=None, include_demo=False)
    service._estates.count_public.assert_awaited_once_with(q=None, include_demo=False)


@pytest.mark.asyncio
async def test_production_detail_refuses_demo_even_if_published(production):
    service = PublicDirectoryService(AsyncMock())
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(is_demo=True, is_public=True)))
    with pytest.raises(NotFoundException):
        await service.get_estate(7)


@pytest.mark.asyncio
async def test_production_photo_refuses_a_demo_estate(production):
    service = PublicDirectoryService(AsyncMock())
    service._photos = SimpleNamespace(get_by_public_id=AsyncMock(return_value=SimpleNamespace(estate_id=7)))
    service._estates = SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(is_demo=True)))
    with pytest.raises(NotFoundException):
        await service.read_photo('old-sample-photo', size='full')
    service._estates.get_by_id.assert_awaited_once_with(7)


def authorization_service():
    service = EstateAuthorizationService(AsyncMock())
    memberships = [SimpleNamespace(estate_id=n, membership_role='hoa_admin', property_id=None) for n in (7, 8)]
    service._memberships = SimpleNamespace(list_for_user=AsyncMock(return_value=memberships), list_for_user_and_estate=AsyncMock(return_value=memberships[:1]))
    demo = SimpleNamespace(name='Archived sample', suburb='Musgrave', city='Durban', province='KwaZulu-Natal', is_demo=True)
    live = SimpleNamespace(name='Live estate', suburb='Musgrave', city='Durban', province='KwaZulu-Natal', is_demo=False)
    service._estates = SimpleNamespace(get_many_by_ids=AsyncMock(return_value={7: demo, 8: live}), get_by_id=AsyncMock(return_value=demo))
    return service


@pytest.mark.asyncio
async def test_production_estate_picker_keeps_only_real_estate_memberships(production):
    service = authorization_service()
    accessible = await service.list_accessible_estates(SimpleNamespace(user_id=4, role='hoa_admin'))
    assert [estate.estate_id for estate in accessible] == [8]


@pytest.mark.asyncio
async def test_production_direct_access_to_demo_is_refused_despite_membership(production):
    service = authorization_service()
    with pytest.raises(ForbiddenException):
        await service.resolve_access(SimpleNamespace(user_id=4, role='hoa_admin'), 7)
