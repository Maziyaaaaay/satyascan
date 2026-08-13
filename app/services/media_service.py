import hashlib
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import AI_REASONING_MAX_LEN, Image
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
) -> None:
    image.ocr_text_excerpt = (ocr_text or "")[:OCR_EXCERPT_MAX_LEN] or None
    image.reverse_search_match_count = match_count
    image.ai_generated_probability = ai_generated_probability
    image.ai_generated_reasoning = (ai_generated_reasoning or "")[:AI_REASONING_MAX_LEN] or None
    await db.flush()
