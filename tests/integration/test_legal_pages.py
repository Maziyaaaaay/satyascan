import pytest


@pytest.mark.asyncio
async def test_privacy_policy_is_served(app_client):
    client, _ = app_client
    response = await client.get("/privacy")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Privacy Policy" in response.text


@pytest.mark.asyncio
async def test_terms_of_service_is_served(app_client):
    client, _ = app_client
    response = await client.get("/terms")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Terms of Service" in response.text
