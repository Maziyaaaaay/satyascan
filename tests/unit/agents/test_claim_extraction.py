import pytest

from app.agents import claim_extraction


@pytest.mark.asyncio
async def test_extracts_at_least_one_claim(base_state, providers):
    base_state.input_text = "Forwarded: Drinking hot water cures COVID, share with everyone!"
    result = await claim_extraction.run(base_state, providers)
    assert len(result.claims) >= 1
    assert all(c.normalized_text for c in result.claims)


@pytest.mark.asyncio
async def test_empty_text_still_produces_a_claim_list(base_state, providers):
    base_state.input_text = ""
    result = await claim_extraction.run(base_state, providers)
    assert isinstance(result.claims, list)
