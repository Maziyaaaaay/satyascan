import pytest


@pytest.mark.asyncio
async def test_submit_feedback_for_existing_verification(app_client):
    client, _ = app_client
    verify_response = await client.post(
        "/simulator/message", json={"session_id": "feedback-session", "text": "Some claim to check"}
    )
    verify_response.raise_for_status()

    from sqlalchemy import select

    from app.db.base import get_session_factory
    from app.models.verification import Verification

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verification = result.scalars().first()

    response = await client.post(
        "/feedback", json={"verification_id": str(verification.id), "rating": "helpful", "comment": "Thanks!"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"


@pytest.mark.asyncio
async def test_submit_feedback_for_unknown_verification_returns_404(app_client):
    client, _ = app_client
    response = await client.post(
        "/feedback",
        json={"verification_id": "00000000-0000-0000-0000-000000000000", "rating": "helpful"},
    )
    assert response.status_code == 404
