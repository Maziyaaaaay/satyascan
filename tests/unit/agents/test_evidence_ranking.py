import pytest

from app.agents import evidence_ranking
from app.agents.state import ExtractedClaim, ImageAnalysisResult, SearchResult
from app.providers.base import FactCheckResult, ReverseImageMatch


@pytest.mark.asyncio
async def test_ranks_evidence_from_fact_checks(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="hot water cures covid")]
    base_state.search = SearchResult(
        fact_checks=[
            FactCheckResult(claim_text="hot water cures covid", rating="False", publisher="Alt News", url="https://a.example/1"),
            FactCheckResult(claim_text="hot water cures covid", rating="True", publisher="Boom", url="https://b.example/2"),
        ]
    )
    result = await evidence_ranking.run(base_state, providers)
    assert len(result.ranked_evidence) == 2
    assert {e.rank for e in result.ranked_evidence} == {1, 2}
    assert all(0.0 <= e.relevance_score <= 1.0 for e in result.ranked_evidence)
    assert {e.stance.value for e in result.ranked_evidence} == {"contradicts", "supports"}


@pytest.mark.asyncio
async def test_no_evidence_sources_returns_empty_list(base_state, providers):
    result = await evidence_ranking.run(base_state, providers)
    assert result.ranked_evidence == []


@pytest.mark.asyncio
async def test_image_only_message_never_embeds_an_empty_query_text(base_state, providers):
    # Regression test: an image sent with no caption and no OCR-extractable
    # text used to leave both input_text and every claim empty, so
    # query_text fell through to "" - Gemini's real embed_content rejects
    # an empty string outright ("'content' argument must not be empty"),
    # which crashed the whole verification in production (image-only
    # messages with no caption). Confirmed live against Python 3.11 + the
    # real Gemini key before this fix.
    base_state.claims = []
    base_state.input_text = None
    base_state.image_analysis = ImageAnalysisResult(
        ocr_text=None, reverse_matches=[ReverseImageMatch(url="https://example.com/1", match_confidence=0.9)]
    )

    embedded_texts = []
    original_embed = providers.llm.embed

    async def spy_embed(texts):
        embedded_texts.append(texts)
        return await original_embed(texts)

    providers.llm.embed = spy_embed

    result = await evidence_ranking.run(base_state, providers)

    assert embedded_texts, "embed() should have been called"
    query_text = embedded_texts[0][0]
    assert query_text, "query_text passed to embed() must never be empty"
    assert len(result.ranked_evidence) == 1


@pytest.mark.asyncio
async def test_verification_collection_is_deleted_after_ranking(base_state, providers):
    # Regression test for a real production outage: each verification's
    # Chroma collection is write-once/query-once and was never being
    # deleted, so it accumulated on the persistent volume forever - this
    # was confirmed live as the actual cause of a
    # "sqlite3.OperationalError: database or disk is full" crash.
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="hot water cures covid")]
    base_state.search = SearchResult(
        fact_checks=[FactCheckResult(claim_text="hot water cures covid", rating="False", url="https://a.example/1")]
    )

    result = await evidence_ranking.run(base_state, providers)
    assert result.ranked_evidence

    collection = f"verification-{base_state.verification_id.hex}"
    leftover = await providers.vectorstore.query(collection, embedding=[0.1] * 8, top_k=5)
    assert leftover == [], "the per-verification collection must not survive past this agent"
