import tempfile

import pytest

from app.vectorstore.chroma_store import ChromaStore
from app.vectorstore.base import VectorStoreItem


@pytest.fixture
def store():
    tmp_dir = tempfile.mkdtemp()
    return ChromaStore(persist_dir=tmp_dir)


@pytest.mark.asyncio
async def test_query_empty_collection_returns_no_matches(store):
    matches = await store.query("evidence", embedding=[0.1] * 16, top_k=5)
    assert matches == []


@pytest.mark.asyncio
async def test_upsert_then_query_returns_closest_match_first(store):
    items = [
        VectorStoreItem(id="a", text="hot water cures covid", embedding=[1.0, 0.0, 0.0], metadata={"rank": 1}),
        VectorStoreItem(id="b", text="unrelated claim about elections", embedding=[0.0, 1.0, 0.0], metadata={"rank": 2}),
        VectorStoreItem(id="c", text="drinking hot water helps colds", embedding=[0.9, 0.1, 0.0], metadata={"rank": 3}),
    ]
    await store.upsert("evidence", items)

    matches = await store.query("evidence", embedding=[1.0, 0.0, 0.0], top_k=2)

    assert len(matches) == 2
    assert matches[0].id == "a"
    assert matches[0].metadata["rank"] == 1


@pytest.mark.asyncio
async def test_collections_are_isolated(store):
    await store.upsert(
        "collection_x", [VectorStoreItem(id="x1", text="x item", embedding=[1.0, 0.0])]
    )
    matches = await store.query("collection_y", embedding=[1.0, 0.0], top_k=5)
    assert matches == []


@pytest.mark.asyncio
async def test_upsert_with_empty_list_is_a_noop(store):
    await store.upsert("evidence", [])
    matches = await store.query("evidence", embedding=[1.0, 0.0], top_k=5)
    assert matches == []


@pytest.mark.asyncio
async def test_delete_collection_removes_it(store):
    # Regression test for a real production outage: evidence_ranking.py
    # creates one persistent collection per verification and never reused
    # it again after querying, so it must be deleted or it accumulates on
    # disk forever (confirmed live as the cause of a
    # "database or disk is full" crash).
    await store.upsert("evidence", [VectorStoreItem(id="a", text="x", embedding=[1.0, 0.0])])
    assert await store.query("evidence", embedding=[1.0, 0.0], top_k=5)

    await store.delete_collection("evidence")

    matches = await store.query("evidence", embedding=[1.0, 0.0], top_k=5)
    assert matches == []


@pytest.mark.asyncio
async def test_delete_collection_on_nonexistent_collection_does_not_raise(store):
    await store.delete_collection("never-created")
