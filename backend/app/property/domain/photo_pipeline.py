"""The photograph pipeline: what we accept, what we store, and under what name.

This module is pure - no database, no request, no settings object - so the rules
that protect residents (and the server) can be tested directly:

* **Only decodable images.** The declared content type is a hint, never proof:
  the bytes are handed to Pillow and must decode. A renamed ``.jpg`` that is not
  an image is rejected here, not stored.
* **A pixel cap before the decode.** A decompression bomb is a small file that
  decodes into a huge bitmap, so the declared dimensions are checked *before*
  ``load()`` and anything over :data:`MAX_PIXELS` is refused outright. Pillow's
  own ``MAX_IMAGE_PIXELS`` guard stays in place as a second line of defence and
  its ``DecompressionBombError`` is reported as the same clean refusal.
* **Re-encoded, always.** Every accepted upload becomes JPEG on the way to disk:
  transparency is composited onto white, EXIF (and therefore GPS) is dropped, and
  a phone photo's orientation tag is baked into the pixels before it is dropped.
  Nothing of the original file survives except its picture.
* **Two sizes.** Full (longest side at most :data:`FULL_MAX_SIDE`) and a
  thumbnail (at most :data:`THUMB_MAX_SIDE`) for the public grid.
* **A random name.** The stored filename is :func:`generate_public_id` - 32
  characters from ``secrets`` - and the uploaded filename is never used for
  anything, so no path from the client can reach the filesystem.
"""
from __future__ import annotations

import io
import secrets
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.exceptions import BadRequestException

#: Image content types we are willing to look at. Everything is stored as JPEG.
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

#: Largest upload we will even read into memory (5 MB).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

#: Largest number of pixels we will decode (40 MP). Above this the declared
#: dimensions are refused before any decode is attempted.
MAX_PIXELS = 40_000_000

#: Longest side of the stored full image and of the thumbnail.
FULL_MAX_SIDE = 1920
THUMB_MAX_SIDE = 480

JPEG_QUALITY = 85

#: Length of a photo's public id: 24 random bytes, base64url without padding.
PUBLIC_ID_BYTES = 24
PUBLIC_ID_LENGTH = 32

STORED_CONTENT_TYPE = "image/jpeg"

NOT_AN_IMAGE_MESSAGE = "That file is not an image we can read."
TOO_MANY_PIXELS_MESSAGE = "That image is too large to process."


def generate_public_id() -> str:
    """A fresh, unguessable 32-character handle for one photograph."""
    public_id = secrets.token_urlsafe(PUBLIC_ID_BYTES)
    assert len(public_id) == PUBLIC_ID_LENGTH  # guarded by a test as well
    return public_id


def photo_filename(public_id: str, *, thumb: bool = False) -> str:
    """The file one photo is stored as. Only the random id is used."""
    return f"{public_id}_thumb.jpg" if thumb else f"{public_id}.jpg"


def photo_path(upload_dir: str | Path, public_id: str, *, thumb: bool = False) -> Path:
    """Where one photo lives under ``UPLOAD_DIR``."""
    return Path(upload_dir) / photo_filename(public_id, thumb=thumb)


def _to_rgb(image: Image.Image) -> Image.Image:
    """Flatten to RGB, compositing any transparency onto white."""
    # Bake the EXIF orientation into the pixels first: the tag is about to be
    # dropped with the rest of the metadata, and a sideways photo would stay
    # sideways forever.
    oriented = ImageOps.exif_transpose(image)
    if oriented.mode in ("RGBA", "LA", "PA") or (
        oriented.mode == "P" and "transparency" in oriented.info
    ):
        rgba = oriented.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return oriented.convert("RGB")


def _encode_jpeg(image: Image.Image, max_side: int) -> bytes:
    """Re-encode one size as JPEG with no EXIF of any kind."""
    resized = image.copy()
    resized.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    # No ``exif=`` argument: nothing but pixels is written.
    resized.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


def encode_photo_pair(data: bytes) -> tuple[bytes, bytes, int, int]:
    """Decode one upload and return ``(full_jpeg, thumb_jpeg, width, height)``.

    Raises :class:`BadRequestException` (400) for anything that is not a readable
    image, for an empty file, and for an image whose declared size exceeds
    :data:`MAX_PIXELS`. ``width``/``height`` are the stored (full) dimensions.
    """
    if not data:
        raise BadRequestException("The uploaded file is empty.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            declared_width, declared_height = image.size
            if declared_width <= 0 or declared_height <= 0:
                raise BadRequestException(NOT_AN_IMAGE_MESSAGE)
            # Before load(): a bomb is refused on its header, not after the
            # decoder has already allocated the bitmap.
            if declared_width * declared_height > MAX_PIXELS:
                raise BadRequestException(TOO_MANY_PIXELS_MESSAGE)
            image.load()
            frame = _to_rgb(image)
    except BadRequestException:
        raise
    except Image.DecompressionBombError as exc:  # Pillow's own guard
        raise BadRequestException(TOO_MANY_PIXELS_MESSAGE) from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise BadRequestException(NOT_AN_IMAGE_MESSAGE) from exc

    full = _encode_jpeg(frame, FULL_MAX_SIDE)
    thumbnail = _encode_jpeg(frame, THUMB_MAX_SIDE)
    return full, thumbnail, frame.width, frame.height
