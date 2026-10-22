"""ONB MASTER P2 — estate profile, photo uploads and the public directory.

Non-DB tests cover the pipeline itself (decode, pixel cap, EXIF/GPS stripping,
transparency, resize, naming) and the rules that must hold before anything is
touched (the 12-photo ceiling, the 5 MB ceiling, the content-type check, a
non-admin being refused before a single query).

Integration tests (`@pytest.mark.integration`) drive the real HTTP endpoints on
the throwaway database: an upload that lands a re-encoded JPEG on disk, a GPS
EXIF image that comes out clean, a traversal filename that is ignored, the file
removed on delete, and the public directory - which is unauthenticated - showing
only published estates, exact key sets, and the score only when opted in.

Every test points ``UPLOAD_DIR`` at a temporary directory, so nothing is written
into the repository tree.
"""
from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.operator_fixtures import signup_fixture
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    PayloadTooLargeException,
)
from app.property.domain.photo_pipeline import (
    FULL_MAX_SIDE,
    MAX_PIXELS,
    MAX_UPLOAD_BYTES,
    PUBLIC_ID_LENGTH,
    THUMB_MAX_SIDE,
    encode_photo_pair,
    generate_public_id,
    photo_path,
)
from app.property.repositories.estate_repository import EstateRepository
from app.property.schemas.estate_profile import EstateProfileUpdate
from app.property.schemas.public_directory import (
    PublicEstateDetailResponse,
    PublicEstateListItem,
    PublicLivingScoreSummary,
    PublicPhotoResponse,
)
from app.property.services.estate_photo_service import (
    MAX_PHOTOS_PER_ESTATE,
    EstatePhotoService,
)

BASE = "/api/v1"
PASSWORD = "correct-horse-battery-9"

GPS_IFD_TAG = 0x8825
MODEL_TAG = 0x0110


# --------------------------------------------------------------------------- #
# Image helpers
# --------------------------------------------------------------------------- #


def _jpeg_bytes(size=(800, 600), color=(10, 120, 200)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes(size=(64, 48), color=(255, 0, 0, 128)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _gps_jpeg_bytes() -> bytes:
    """A real JPEG carrying a camera model and GPS latitude/longitude."""
    exif = Image.Exif()
    exif[MODEL_TAG] = "VALORA-TEST-CAMERA"
    gps = exif.get_ifd(GPS_IFD_TAG)
    gps[1] = "S"
    gps[2] = (25, 45, 0)
    gps[3] = "E"
    gps[4] = (28, 11, 0)
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), (30, 60, 90)).save(
        buffer, format="JPEG", exif=exif.tobytes()
    )
    return buffer.getvalue()


def _exif_of(data: bytes) -> Image.Exif:
    with Image.open(io.BytesIO(data)) as image:
        return image.getexif()


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Point every service at a temporary UPLOAD_DIR, and reset the cache after."""
    from app.core.config import get_settings

    target = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(target))
    get_settings.cache_clear()
    yield target
    get_settings.cache_clear()


# --------------------------------------------------------------------------- #
# The pipeline, without a database
# --------------------------------------------------------------------------- #


def test_public_id_is_a_long_urlsafe_random_handle() -> None:
    first = generate_public_id()
    second = generate_public_id()
    assert len(first) == PUBLIC_ID_LENGTH == 32
    assert first != second
    assert set(first) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )


def test_photo_paths_use_only_the_random_id() -> None:
    public_id = "AbCdEfGhIjKlMnOpQrStUvWxYz012345"
    assert photo_path("uploads", public_id).name == f"{public_id}.jpg"
    assert photo_path("uploads", public_id, thumb=True).name == f"{public_id}_thumb.jpg"
    # The upload's own filename never appears: it cannot reach the filesystem.
    assert ".." not in str(photo_path("uploads", public_id))
    assert "/" not in photo_path("uploads", public_id).name


def test_encode_photo_pair_strips_exif_and_gps() -> None:
    source = _gps_jpeg_bytes()
    assert _exif_of(source).get_ifd(GPS_IFD_TAG)  # the source really carries GPS

    full, thumb, width, height = encode_photo_pair(source)

    for encoded in (full, thumb):
        rewrite = _exif_of(encoded)
        assert not rewrite.get_ifd(GPS_IFD_TAG)
        assert rewrite.get(MODEL_TAG) is None
        assert len(rewrite) == 0
    assert (width, height) == (320, 240)


def test_encode_photo_pair_flattens_transparency_onto_white() -> None:
    full, _thumb, _width, _height = encode_photo_pair(_png_bytes(color=(255, 0, 0, 0)))

    with Image.open(io.BytesIO(full)) as image:
        assert image.mode == "RGB"
        # Fully transparent red becomes white - not black, and not a palette.
        assert image.getpixel((10, 10)) == (255, 255, 255)


def test_encode_photo_pair_caps_the_longest_side() -> None:
    full, thumb, width, height = encode_photo_pair(_jpeg_bytes(size=(2500, 100)))

    assert (width, height) == (2500, 100)  # the stored dimensions are the real ones
    with Image.open(io.BytesIO(full)) as image:
        assert max(image.size) == FULL_MAX_SIDE
    with Image.open(io.BytesIO(thumb)) as image:
        assert max(image.size) == THUMB_MAX_SIDE


def test_encode_photo_pair_rejects_a_renamed_non_image() -> None:
    with pytest.raises(BadRequestException):
        encode_photo_pair(b"this is a text file with a .jpg name")
    with pytest.raises(BadRequestException):
        encode_photo_pair(b"")


def test_encode_photo_pair_rejects_a_declared_pixel_bomb(monkeypatch) -> None:
    """The pixel cap is enforced on the declared size, before any decode."""
    monkeypatch.setattr(
        "app.property.domain.photo_pipeline.MAX_PIXELS", 100
    )
    with pytest.raises(BadRequestException) as error:
        encode_photo_pair(_jpeg_bytes(size=(64, 48)))  # 3072 pixels > 100
    assert "too large" in error.value.detail


def test_encode_photo_pair_rejects_pillows_own_bomb_guard(monkeypatch) -> None:
    """Pillow's MAX_IMAGE_PIXELS stays armed as the second line of defence."""
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)  # restored by monkeypatch
    with pytest.raises(BadRequestException) as error:
        encode_photo_pair(_jpeg_bytes(size=(200, 200)))
    assert "too large" in error.value.detail


def test_the_pixel_cap_is_sane() -> None:
    assert MAX_PIXELS == 40_000_000
    assert MAX_UPLOAD_BYTES == 5 * 1024 * 1024


# --------------------------------------------------------------------------- #
# Service rules, before anything is touched
# --------------------------------------------------------------------------- #


def _service(monkeypatch, *, count: int = 0, authorization=None):
    repo = SimpleNamespace(
        count_for_estate=AsyncMock(return_value=count),
        next_position=AsyncMock(return_value=count),
        add=AsyncMock(return_value=SimpleNamespace(
            photo_id=1, public_id="x" * 32, content_type="image/jpeg",
            width=1, height=1, bytes=1, caption=None, position=0,
            created_at=None,
        )),
    )
    monkeypatch.setattr(
        "app.property.services.estate_photo_service.EstatePhotoRepository",
        lambda _db: repo,
    )
    monkeypatch.setattr(
        "app.property.services.estate_photo_service.EstateAuthorizationService",
        lambda _db: authorization or SimpleNamespace(require_role=AsyncMock()),
    )
    return EstatePhotoService(object(), upload_dir="unused-for-these-tests"), repo


@pytest.mark.asyncio
async def test_photo_service_refuses_the_thirteenth_photo(monkeypatch) -> None:
    service, repo = _service(monkeypatch, count=MAX_PHOTOS_PER_ESTATE)

    with pytest.raises(ConflictException) as error:
        await service.upload_photo(
            SimpleNamespace(user_id=1, role="hoa_admin"),
            estate_id=1,
            filename="pool.jpg",
            content_type="image/jpeg",
            data=_jpeg_bytes(),
        )
    assert str(MAX_PHOTOS_PER_ESTATE) in error.value.detail
    repo.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_photo_service_refuses_an_oversize_upload(monkeypatch) -> None:
    service, repo = _service(monkeypatch)

    with pytest.raises(PayloadTooLargeException):
        await service.upload_photo(
            SimpleNamespace(user_id=1, role="hoa_admin"),
            estate_id=1,
            filename="huge.jpg",
            content_type="image/jpeg",
            data=b"x" * (MAX_UPLOAD_BYTES + 1),
        )
    repo.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_photo_service_refuses_an_unsupported_content_type(monkeypatch) -> None:
    service, repo = _service(monkeypatch)

    with pytest.raises(BadRequestException):
        await service.upload_photo(
            SimpleNamespace(user_id=1, role="hoa_admin"),
            estate_id=1,
            filename="doc.pdf",
            content_type="application/pdf",
            data=_jpeg_bytes(),
        )
    repo.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_photo_service_denies_a_non_admin_before_touching_anything(monkeypatch) -> None:
    authorization = SimpleNamespace(
        require_role=AsyncMock(side_effect=ForbiddenException("no"))
    )
    service, repo = _service(monkeypatch, authorization=authorization)

    with pytest.raises(ForbiddenException):
        await service.upload_photo(
            SimpleNamespace(user_id=9, role="resident"),
            estate_id=1,
            filename="pool.jpg",
            content_type="image/jpeg",
            data=_jpeg_bytes(),
        )
    # Not even the count was read, and nothing was written.
    repo.count_for_estate.assert_not_awaited()
    authorization.require_role.assert_awaited_once()


def test_estate_profile_update_rejects_the_name_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EstateProfileUpdate.model_validate({"name": "A New Name"})
    with pytest.raises(ValidationError):
        EstateProfileUpdate.model_validate({"is_public": True, "unexpected": 1})
    parsed = EstateProfileUpdate.model_validate({"is_public": True})
    assert parsed.is_public is True
    assert parsed.show_living_score is None
    assert parsed.description is None


def test_public_statement_selects_only_published_estates() -> None:
    sql = str(
        EstateRepository.public_statement(q="centurion").compile(
            dialect=postgresql.dialect()
        )
    )
    assert "estates.is_public IS true" in sql
    # PostgreSQL keeps ILIKE native rather than lowering both sides.
    assert "estates.name ILIKE" in sql
    assert "estates.suburb ILIKE" in sql and "estates.city ILIKE" in sql
    assert "ORDER BY estates.name ASC, estates.estate_id ASC" in sql


def test_public_dtos_are_allow_lists() -> None:
    assert set(PublicEstateListItem.model_fields) == {
        "estate_id",
        "name",
        "suburb",
        "city",
        "province",
        "description",
        "unit_count",
        "cover_photo_public_id",
    }
    assert set(PublicEstateDetailResponse.model_fields) == {
        "estate_id",
        "name",
        "suburb",
        "city",
        "province",
        "description",
        "unit_count",
        "photos",
        "living_score",
    }
    assert set(PublicPhotoResponse.model_fields) == {"public_id", "caption"}
    assert set(PublicLivingScoreSummary.model_fields) == {
        "overall_score",
        "status",
        "as_of",
        "engine_version",
        "data_origin",
    }
    # None of the published shapes can carry any of these, at all.
    forbidden = {
        "unit_no",
        "street_address",
        "email",
        "phone",
        "user_id",
        "members",
        "complaints",
        "incidents",
        "join_code",
        "membership_id",
        "photo_id",
        "uploaded_by",
    }
    for model in (
        PublicEstateListItem,
        PublicEstateDetailResponse,
        PublicPhotoResponse,
        PublicLivingScoreSummary,
    ):
        assert not (set(model.model_fields) & forbidden)


# --------------------------------------------------------------------------- #
# Integration harness
# --------------------------------------------------------------------------- #


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _estate_world(client, *, name: str, email: str, units=("A-1",)):
    registration = await signup_fixture(client,
        f"{BASE}/auth/register",
        json={
            "full_name": "Estate Admin",
            "email": email,
            "password": PASSWORD,
            "account_type": "estate_admin",
            "estate": {
                "name": name,
                "suburb": "Centurion",
                "city": "Pretoria",
                "province": "Gauteng",
                "description": "A quiet complex with a pool.",
            },
        },
    )
    assert registration.status_code == 201, registration.text
    headers = _bearer(registration.json()["access_token"])
    estates = await client.get(f"{BASE}/auth/estates", headers=headers)
    estate_id = estates.json()["estates"][0]["estate_id"]
    if units:
        units_response = await client.post(
            f"{BASE}/properties/bulk?estate_id={estate_id}",
            json={
                "units": [
                    {"unit_no": unit_no, "street_address": f"{unit_no} Ridge Close"}
                    for unit_no in units
                ]
            },
            headers=headers,
        )
        assert units_response.status_code == 201, units_response.text
    return headers, estate_id


async def _upload(client, headers, estate_id: int, *, data: bytes, filename: str, caption=None,
                  content_type: str = "image/jpeg"):
    files = {"file": (filename, data, content_type)}
    form = {"caption": caption} if caption is not None else None
    return await client.post(
        f"{BASE}/estates/photos?estate_id={estate_id}", files=files, data=form, headers=headers
    )


# --------------------------------------------------------------------------- #
# Integration: uploads
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_stores_a_re_encoded_jpeg_and_refuses_the_thirteenth(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(async_client, name="Photo Estate", email="p2_admin@example.com")

    uploaded = await _upload(
        async_client, admin, estate_id, data=_jpeg_bytes(size=(2400, 1200)), filename="pool.jpg",
        caption="  The pool at dusk  ",
    )
    assert uploaded.status_code == 201, uploaded.text
    photo = uploaded.json()
    public_id = photo["public_id"]
    assert len(public_id) == 32
    assert photo["caption"] == "The pool at dusk"  # trimmed
    assert photo["width"] == 2400 and photo["height"] == 1200  # stored, real dimensions
    assert photo["content_type"] == "image/jpeg"

    full_file = upload_dir / f"{public_id}.jpg"
    thumb_file = upload_dir / f"{public_id}_thumb.jpg"
    assert full_file.is_file() and thumb_file.is_file()
    with Image.open(full_file) as image:
        assert image.format == "JPEG"
        assert max(image.size) == FULL_MAX_SIDE
        assert len(image.getexif()) == 0
    with Image.open(thumb_file) as image:
        assert max(image.size) == THUMB_MAX_SIDE

    listed = await async_client.get(
        f"{BASE}/estates/photos?estate_id={estate_id}", headers=admin
    )
    assert listed.status_code == 200, listed.text
    assert [row["photo_id"] for row in listed.json()] == [photo["photo_id"]]

    other_admin, other_estate = await _estate_world(
        async_client, name="Other Photo Estate", email="p2_other@example.com"
    )
    cross = await _upload(
        async_client, other_admin, estate_id, data=_jpeg_bytes(), filename="x.jpg"
    )
    assert cross.status_code == 403, cross.text
    read_cross = await async_client.get(
        f"{BASE}/estates/photos?estate_id={estate_id}", headers=other_admin
    )
    assert read_cross.status_code == 403, read_cross.text

    # The estate ceiling: 12 photos, and the 13th is a 409.
    for index in range(MAX_PHOTOS_PER_ESTATE - 1):
        response = await _upload(
            async_client, admin, estate_id, data=_jpeg_bytes(size=(60, 40)), filename="more.jpg"
        )
        assert response.status_code == 201, (index, response.text)
    assert len(
        (await async_client.get(f"{BASE}/estates/photos?estate_id={estate_id}", headers=admin)).json()
    ) == MAX_PHOTOS_PER_ESTATE

    thirteenth = await _upload(
        async_client, admin, estate_id, data=_jpeg_bytes(size=(60, 40)), filename="more.jpg"
    )
    assert thirteenth.status_code == 409, thirteenth.text
    assert f"maximum of {MAX_PHOTOS_PER_ESTATE}" in thirteenth.json()["detail"]["message"]

    # Re-caption and reorder, then delete one: the files go with the row.
    first = (await async_client.get(f"{BASE}/estates/photos?estate_id={estate_id}", headers=admin)).json()[0]
    patched = await async_client.patch(
        f"{BASE}/estates/photos/{first['photo_id']}?estate_id={estate_id}",
        json={"caption": "Front gate", "position": 5},
        headers=admin,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["caption"] == "Front gate"
    assert patched.json()["position"] == 5

    deleted = await async_client.delete(
        f"{BASE}/estates/photos/{photo['photo_id']}?estate_id={estate_id}", headers=admin
    )
    assert deleted.status_code == 204, deleted.text
    assert not full_file.exists()
    assert not thumb_file.exists()
    remaining = await async_client.get(
        f"{BASE}/estates/photos?estate_id={estate_id}", headers=admin
    )
    assert photo["photo_id"] not in [row["photo_id"] for row in remaining.json()]

    # Deleting it again is a 404, and so is a photo id from another estate.
    assert (
        await async_client.delete(
            f"{BASE}/estates/photos/{photo['photo_id']}?estate_id={estate_id}", headers=admin
        )
    ).status_code == 404
    assert (
        await async_client.delete(
            f"{BASE}/estates/photos/{first['photo_id']}?estate_id={other_estate}",
            headers=other_admin,
        )
    ).status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_gps_photo_comes_out_with_no_exif(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="GPS Estate", email="p2_gps@example.com"
    )
    source = _gps_jpeg_bytes()
    assert _exif_of(source).get_ifd(GPS_IFD_TAG)

    uploaded = await _upload(
        async_client, admin, estate_id, data=source, filename="holiday.jpg",
        caption="Front garden",
    )
    assert uploaded.status_code == 201, uploaded.text
    stored = (upload_dir / f"{uploaded.json()['public_id']}.jpg").read_bytes()
    rewrite = _exif_of(stored)
    assert not rewrite.get_ifd(GPS_IFD_TAG)
    assert rewrite.get(MODEL_TAG) is None
    assert len(rewrite) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_traversal_filename_is_ignored(
    db_session, async_client, upload_dir, tmp_path
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Traversal Estate", email="p2_traversal@example.com"
    )

    uploaded = await _upload(
        async_client, admin, estate_id, data=_jpeg_bytes(size=(80, 60)),
        filename="../../../../evil.jpg",
    )
    assert uploaded.status_code == 201, uploaded.text
    public_id = uploaded.json()["public_id"]

    assert (upload_dir / f"{public_id}.jpg").is_file()
    assert not (tmp_path / "evil.jpg").exists()
    assert not (upload_dir.parent / "evil.jpg").exists()
    assert not (tmp_path / ".." / "evil.jpg").exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_renamed_non_image_is_rejected_over_http(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Not An Image Estate", email="p2_notimage@example.com"
    )

    rejected = await _upload(
        async_client, admin, estate_id, data=b"plain text pretending", filename="photo.jpg"
    )
    assert rejected.status_code == 400, rejected.text
    assert "not an image" in rejected.json()["detail"]["message"]
    assert not upload_dir.exists() or not list(upload_dir.iterdir())


# --------------------------------------------------------------------------- #
# Integration: the public directory
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_directory_lists_only_published_estates(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Public Estate", email="p2_public@example.com", units=("A-1", "A-2")
    )
    _private_admin, private_estate = await _estate_world(
        async_client, name="Private Estate", email="p2_private@example.com"
    )

    # Nothing is public until the estate says so.
    empty = await async_client.get(f"{BASE}/public/estates")
    assert empty.status_code == 200, empty.text
    assert empty.json()["total"] == 0
    assert (await async_client.get(f"{BASE}/public/estates/{estate_id}")).status_code == 404

    profile = await async_client.get(
        f"{BASE}/estates/profile?estate_id={estate_id}", headers=admin
    )
    assert profile.json()["is_public"] is False
    assert profile.json()["show_living_score"] is False

    published = await async_client.patch(
        f"{BASE}/estates/profile?estate_id={estate_id}",
        json={"is_public": True, "description": "Family complex with a pool"},
        headers=admin,
    )
    assert published.status_code == 200, published.text
    assert published.json()["is_public"] is True

    await _upload(
        async_client, admin, estate_id, data=_jpeg_bytes(size=(100, 80)), filename="cover.jpg",
        caption="The pool",
    )

    listing = await async_client.get(f"{BASE}/public/estates")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] == 1
    assert body["page"] == 1 and body["size"] == 20
    item = body["items"][0]
    assert set(item) == set(PublicEstateListItem.model_fields)
    assert item["estate_id"] == estate_id
    assert item["name"] == "Public Estate"
    assert item["suburb"] == "Centurion"
    assert item["city"] == "Pretoria"
    assert item["province"] == "Gauteng"
    assert item["unit_count"] == 2
    assert len(item["cover_photo_public_id"]) == 32

    # Search matches name, suburb and city - and the private estate never appears.
    by_name = await async_client.get(f"{BASE}/public/estates?q=public")
    by_suburb = await async_client.get(f"{BASE}/public/estates?q=centurion")
    by_city = await async_client.get(f"{BASE}/public/estates?q=pretoria")
    assert by_name.json()["total"] == 1
    assert by_suburb.json()["total"] == 1
    assert by_city.json()["total"] == 1
    assert (await async_client.get(f"{BASE}/public/estates?q=Private")).json()["total"] == 0

    # page_size is capped at 50.
    assert (await async_client.get(f"{BASE}/public/estates?page_size=51")).status_code == 422

    # A private estate's detail is a 404, exactly like an unknown one.
    assert (
        await async_client.get(f"{BASE}/public/estates/{private_estate}")
    ).status_code == 404
    assert (await async_client.get(f"{BASE}/public/estates/999999")).status_code == 404

    detail = await async_client.get(f"{BASE}/public/estates/{estate_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert set(payload) == set(PublicEstateDetailResponse.model_fields)
    assert payload["description"] == "Family complex with a pool"
    assert payload["unit_count"] == 2
    assert len(payload["photos"]) == 1
    assert set(payload["photos"][0]) == {"public_id", "caption"}
    assert payload["living_score"] is None  # opted out, and not scored anyway


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_detail_publishes_the_score_only_when_opted_in(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Scored Estate", email="p2_scored@example.com"
    )
    await async_client.patch(
        f"{BASE}/estates/profile?estate_id={estate_id}",
        json={"is_public": True, "show_living_score": True},
        headers=admin,
    )

    # Opted in but never scored: still no score block.
    before = await async_client.get(f"{BASE}/public/estates/{estate_id}")
    assert before.json()["living_score"] is None

    recalculated = await async_client.post(
        f"{BASE}/analytics/living-score/recalculate?estate_id={estate_id}", headers=admin
    )
    assert recalculated.status_code == 201, recalculated.text
    snapshot = recalculated.json()

    after = await async_client.get(f"{BASE}/public/estates/{estate_id}")
    summary = after.json()["living_score"]
    assert set(summary) == set(PublicLivingScoreSummary.model_fields)
    assert summary["status"] == snapshot["status"]
    assert summary["as_of"] == snapshot["as_of"]
    assert summary["engine_version"] == snapshot["engine_version"]
    assert summary["overall_score"] == snapshot["overall_score"]
    # A real (non-demo) estate, so the origin is "live" and the badge stays off.
    assert summary["data_origin"] == "live"
    # None of the internal detail is published.
    assert "components" not in summary and "drivers" not in summary

    # Opting back out removes the block, and the snapshot stays stored.
    await async_client.patch(
        f"{BASE}/estates/profile?estate_id={estate_id}",
        json={"show_living_score": False},
        headers=admin,
    )
    assert (
        await async_client.get(f"{BASE}/public/estates/{estate_id}")
    ).json()["living_score"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_photos_are_served_with_nosniff_and_a_cache(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Photo Serve Estate", email="p2_serve@example.com"
    )
    uploaded = await _upload(
        async_client, admin, estate_id, data=_jpeg_bytes(size=(900, 700)), filename="gate.jpg"
    )
    public_id = uploaded.json()["public_id"]

    full = await async_client.get(f"{BASE}/public/photos/{public_id}?size=full")
    assert full.status_code == 200, full.text
    assert full.headers["content-type"] == "image/jpeg"
    assert full.headers["x-content-type-options"] == "nosniff"
    assert full.headers["cache-control"] == "public, max-age=3600"
    with Image.open(io.BytesIO(full.content)) as image:
        # Never enlarged: a 900x700 upload stays 900x700 (the cap is a ceiling).
        assert image.size == (900, 700)
        assert max(image.size) <= FULL_MAX_SIDE

    thumb = await async_client.get(f"{BASE}/public/photos/{public_id}?size=thumb")
    assert thumb.status_code == 200
    with Image.open(io.BytesIO(thumb.content)) as image:
        assert max(image.size) == THUMB_MAX_SIDE

    assert (await async_client.get(f"{BASE}/public/photos/{public_id}?size=huge")).status_code == 422
    assert (await async_client.get(f"{BASE}/public/photos/does-not-exist")).status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_profile_is_readable_by_members_and_writable_only_by_admins(
    db_session, async_client, upload_dir
) -> None:
    admin, estate_id = await _estate_world(
        async_client, name="Profile Estate", email="p2_profile@example.com", units=("A-1",)
    )
    code = (
        await async_client.post(f"{BASE}/join-codes?estate_id={estate_id}", json={}, headers=admin)
    ).json()["code"]
    resident_registration = await signup_fixture(async_client,
        f"{BASE}/auth/register",
        json={"full_name": "Resident", "email": "p2_resident@example.com", "password": PASSWORD},
    )
    resident = _bearer(resident_registration.json()["access_token"])
    assert (
        await async_client.post(
            f"{BASE}/memberships/join", json={"code": code, "unit_no": "A-1"}, headers=resident
        )
    ).status_code == 201

    readable = await async_client.get(
        f"{BASE}/estates/profile?estate_id={estate_id}", headers=resident
    )
    assert readable.status_code == 200, readable.text
    assert readable.json()["name"] == "Profile Estate"
    assert readable.json()["description"] == "A quiet complex with a pool."

    denied = await async_client.patch(
        f"{BASE}/estates/profile?estate_id={estate_id}",
        json={"is_public": True},
        headers=resident,
    )
    assert denied.status_code == 403, denied.text

    # A resident is the wrong role for an upload, too.
    assert (
        await _upload(async_client, resident, estate_id, data=_jpeg_bytes(), filename="x.jpg")
    ).status_code == 403

    # The name is not editable, and an unknown field is rejected, not ignored.
    assert (
        await async_client.patch(
            f"{BASE}/estates/profile?estate_id={estate_id}",
            json={"name": "Renamed"},
            headers=admin,
        )
    ).status_code == 422
    assert (
        await async_client.patch(
            f"{BASE}/estates/profile?estate_id={estate_id}",
            json={"is_public": True, "is_publc": True},
            headers=admin,
        )
    ).status_code == 422

    # An admin of another estate sees a 403 on both verbs.
    other_admin, _other = await _estate_world(
        async_client, name="Some Other Estate", email="p2_other_admin@example.com"
    )
    assert (
        await async_client.get(
            f"{BASE}/estates/profile?estate_id={estate_id}", headers=other_admin
        )
    ).status_code == 403
