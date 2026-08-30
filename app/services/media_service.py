import hashlib
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import (
    AI_REASONING_MAX_LEN,
    C2PA_GENERATOR_MAX_LEN,
    C2PA_SOURCE_TYPE_MAX_LEN,
    C2PA_SUMMARY_MAX_LEN,
    Image,
)
from app.models.mixins import utcnow
from app.models.verification import Verification

OCR_EXCERPT_MAX_LEN = 500


async def record_image_metadata(db: AsyncSession, verification: Verification, image_bytes: bytes) -> Image:
    """Hash the image and create its DB record. The raw bytes live only in
    memory for the duration of this request's pipeline run and are never
    written to disk, so temp_path stays unset and deleted_at is stamped
    immediately - there is nothing on disk to clean up afterward."""
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    image = Image(verification_id=verification.id, image_hash=image_hash, deleted_at=utcnow())
    db.add(image)
    await db.flush()
    return image


async def finalize_image_summary(
    db: AsyncSession,
    image: Image,
    ocr_text: Optional[str],
    match_count: int,
    ai_generated_probability: Optional[float] = None,
    ai_generated_reasoning: Optional[str] = None,
    c2pa_has_manifest: bool = False,
    c2pa_generator: Optional[str] = None,
    c2pa_digital_source_type: Optional[str] = None,
    c2pa_is_ai_indicated: bool = False,
    c2pa_summary: Optional[str] = None,
) -> None:
    image.ocr_text_excerpt = (ocr_text or "")[:OCR_EXCERPT_MAX_LEN] or None
    image.reverse_search_match_count = match_count
    image.ai_generated_probability = ai_generated_probability
    image.ai_generated_reasoning = (ai_generated_reasoning or "")[:AI_REASONING_MAX_LEN] or None
    image.c2pa_has_manifest = c2pa_has_manifest
    image.c2pa_generator = (c2pa_generator or "")[:C2PA_GENERATOR_MAX_LEN] or None
    image.c2pa_digital_source_type = (c2pa_digital_source_type or "")[:C2PA_SOURCE_TYPE_MAX_LEN] or None
    image.c2pa_is_ai_indicated = c2pa_is_ai_indicated
    image.c2pa_summary = (c2pa_summary or "")[:C2PA_SUMMARY_MAX_LEN] or None
    await db.flush()
