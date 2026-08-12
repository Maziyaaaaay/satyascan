import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import FeedbackRating
from app.models.feedback import Feedback
from app.models.verification import Verification

router = APIRouter()


class FeedbackRequest(BaseModel):
    verification_id: uuid.UUID
    rating: FeedbackRating
    comment: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Verification).where(Verification.id == body.verification_id))
    verification = result.scalar_one_or_none()
    if verification is None:
        raise HTTPException(status_code=404, detail="verification not found")

    feedback = Feedback(verification_id=verification.id, rating=body.rating, comment=body.comment)
    db.add(feedback)
    await db.flush()
    return {"status": "recorded", "feedback_id": str(feedback.id)}
