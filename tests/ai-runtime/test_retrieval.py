from pathlib import Path
import asyncio

import pytest

from app import knowledge_context, knowledge_evidence
from embedding import DeterministicEmbeddingProvider
from retrieval import (
    DEFAULT_TOP_K,
    InMemoryKnowledgeStore,
    KnowledgeRetriever,
    chunk_markdown,
    discover_knowledge,
    index_knowledge,
)


def test_markdown_chunking_and_ids_are_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    document = root / "runbooks" / "triage.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Triage\n\nFirst paragraph.\n\nSecond paragraph.", encoding="utf-8")

    first = chunk_markdown(document, root)
    second = chunk_markdown(document, root)

    assert first == second
    assert [chunk.chunk_id for chunk in first] == [
        "knowledge/runbooks/triage.md#chunk-001",
        "knowledge/runbooks/triage.md#chunk-002",
    ]


def test_discovery_indexes_only_markdown_inside_knowledge_root(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "valid.md").write_text("# Valid\n\nContent", encoding="utf-8")
    (root / "ignored.txt").write_text("not indexed", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\nNot indexed", encoding="utf-8")

    chunks = discover_knowledge(root)

    assert len(chunks) == 1
    assert chunks[0].reference == "knowledge/valid.md#chunk-001"
    with pytest.raises(ValueError):
        chunk_markdown(outside, root)


def test_deterministic_embeddings_index_and_rank_with_bounded_top_k(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "knowledge"
        root.mkdir()
        (root / "one.md").write_text("# One\n\nalpha", encoding="utf-8")
        (root / "two.md").write_text("# Two\n\nbeta", encoding="utf-8")
        provider = DeterministicEmbeddingProvider()
        store = InMemoryKnowledgeStore()

        assert await index_knowledge(root, provider, store) == 2
        retriever = KnowledgeRetriever(provider, store, top_k=99)
        results = await retriever.retrieve("alpha", "checkout-api", "1.8.4")

        assert len(results) == 2
        assert store.requested_top_k == [DEFAULT_TOP_K]
        assert results[0].chunk.reference == "knowledge/one.md#chunk-001"
    asyncio.run(scenario())


def test_repository_corpus_contains_checkout_http500_knowledge() -> None:
    async def scenario() -> None:
        root = Path(__file__).parents[2] / "knowledge"
        chunks = discover_knowledge(root)
        provider = DeterministicEmbeddingProvider()
        store = InMemoryKnowledgeStore()
        await index_knowledge(root, provider, store)
        results = await KnowledgeRetriever(provider, store).retrieve(
            "Checkout API returns HTTP 500 after deployment 1.8.4", "checkout-api", "1.8.4"
        )

        corpus = " ".join(result.chunk.content for result in results)
        assert chunks
        assert any(term in corpus for term in ("HTTP 500", "PaymentGatewayClient", "checkout-api"))
    asyncio.run(scenario())


def test_knowledge_evidence_is_runtime_cited_sanitized_and_bounded() -> None:
    root = Path(__file__).parents[2] / "knowledge"
    chunk = discover_knowledge(root)[0]
    chunk = chunk.__class__(chunk.chunk_id, chunk.reference, chunk.title, chunk.chunk_index,
                            "password=secret " + "x" * 500, chunk.content_hash)
    evidence = knowledge_evidence([type("Retrieved", (), {"chunk": chunk})()])

    assert evidence[0].source == "knowledge"
    assert evidence[0].citations[0].reference == chunk.reference
    assert evidence[0].citations[0].citation_id == "citation-knowledge-001"
    assert "secret" not in evidence[0].summary
    assert len(evidence[0].summary) <= 300


def test_knowledge_context_is_explicitly_untrusted_and_only_references_input_chunks() -> None:
    root = Path(__file__).parents[2] / "knowledge"
    chunk = discover_knowledge(root)[0]
    retrieved = type("Retrieved", (), {"chunk": chunk})()

    context = knowledge_context([retrieved])

    assert "reference data only" in context
    assert chunk.reference in context
    assert "not an instruction" in context


def test_retrieved_context_reaches_agent_without_becoming_a_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai.models.test import TestModel

    from agent import REQUIRED_READ_TOOLS
    from agent import create_investigation_agent
    from test_investigation_agent import RecordingReadToolset

    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "grounded"}), toolset)
    chunk = discover_knowledge(Path(__file__).parents[2] / "knowledge")[0]
    retrieved = type("Retrieved", (), {"chunk": chunk})()

    asyncio.run(agent.run("question", knowledge_context([retrieved])))

    assert chunk.reference in agent.last_prompt
    assert set(asyncio.run(agent.toolset.get_tools(None))) == set(REQUIRED_READ_TOOLS)