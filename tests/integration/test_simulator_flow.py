import base64

import pytest


@pytest.mark.asyncio
async def test_simulator_page_serves_html(app_client):
    client, _ = app_client
    response = await client.get("/simulator")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SatyaScan" in response.text


@pytest.mark.asyncio
async def test_simulator_text_message_returns_verdict_and_explanation(app_client):
    client, _ = app_client
    response = await client.post(
        "/simulator/message",
        json={"session_id": "test-session", "text": "Drinking hot water cures COVID", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("true", "false", "misleading", "unverifiable", "satire")
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert data["explanation"]


@pytest.mark.asyncio
async def test_simulator_malayalam_explanation(app_client):
    client, _ = app_client
    response = await client.post(
        "/simulator/message",
        json={"session_id": "test-session-ml", "text": "Drinking hot water cures COVID", "language": "ml"},
    )
    data = response.json()
    assert any("ഀ" <= ch <= "ൿ" for ch in data["explanation"])


@pytest.mark.asyncio
async def test_simulator_image_message(app_client):
    client, _ = app_client
    image_b64 = base64.b64encode(b"fake-image-bytes-for-testing").decode("ascii")
    response = await client.post(
        "/simulator/message",
        json={"session_id": "test-session-img", "image_base64": image_b64, "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["explanation"]
    assert data["image_match_count"] is not None
    assert data["image_ocr_text"]


@pytest.mark.asyncio
async def test_simulator_response_includes_rationale_and_labeled_sources(app_client):
    client, _ = app_client
    response = await client.post(
        "/simulator/message",
        json={"session_id": "test-session-rationale", "text": "Vaccines cause the disease they prevent"},
    )
    data = response.json()
    assert data["rationale"]
    if data["sources"]:
        assert all("url" in s and "domain" in s for s in data["sources"])


@pytest.mark.asyncio
async def test_webhook_and_simulator_produce_equivalent_verdict_for_same_claim(app_client):
    """Both client entrypoints funnel through verification_service.process_incoming
    -> the same pipeline, so identical input under the (deterministic) mock
    providers must yield the identical verdict/confidence - proving the two
    client paths exercise the same internal logic."""
    client, _ = app_client
    claim = "The moon landing was staged in a studio"

    webhook_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "+910000000001", "id": "wamid.PARITY", "type": "text", "text": {"body": claim}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    webhook_response = await client.post("/webhook/whatsapp", json=webhook_payload)
    assert webhook_response.status_code == 200

    simulator_response = await client.post(
        "/simulator/message", json={"session_id": "parity-session", "text": claim, "language": "en"}
    )
    simulator_data = simulator_response.json()

    from sqlalchemy import select

    from app.db.base import get_session_factory
    from app.models.verification import Verification

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification).order_by(Verification.created_at))
        verifications = result.scalars().all()

    # This test's DB is isolated (fresh temp SQLite per app_client), so the
    # webhook call is the only verification created before the simulator call.
    assert len(verifications) == 2
    webhook_verification = verifications[0]
    assert webhook_verification.claim_text == verifications[1].claim_text
    # The mock LLM's intent classification is a deterministic hash of the
    # prompt, so this specific claim may land on chitchat/unclear and
    # short-circuit (verdict stays None) for both paths - either way, the
    # two client paths must agree with each other.
    webhook_verdict = webhook_verification.verdict.value if webhook_verification.verdict else None
    assert webhook_verdict == simulator_data["verdict"]
    assert webhook_verification.confidence_score == simulator_data["confidence_score"]
