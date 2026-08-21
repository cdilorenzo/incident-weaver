from pathlib import Path
import asyncio
import sys
from types import SimpleNamespace

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from app import knowledge_context, knowledge_evidence
from embedding import DeterministicEmbeddingProvider
from retrieval import (
    DEFAULT_TOP_K,
    CURATED_KNOWLEDGE_DIRECTORIES,
    InMemoryKnowledgeStore,
    KnowledgeChunk,
    KnowledgeRetriever,
    PostgresKnowledgeStore,
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


def test_discovery_indexes_only_markdown_in_curated_directories(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "root.md").write_text("# Root\n\nNot indexed", encoding="utf-8")
    (root / "runbooks" / "valid.md").parent.mkdir()
    (root / "runbooks" / "valid.md").write_text("# Valid\n\nContent", encoding="utf-8")
    (root / "history" / "incident.md").parent.mkdir()
    (root / "history" / "incident.md").write_text("# Incident\n\nHistory", encoding="utf-8")
    (root / "runbooks" / "ignored.txt").write_text("not indexed", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\nNot indexed", encoding="utf-8")

    chunks = discover_knowledge(root)

    assert {chunk.reference for chunk in chunks} == {
        "knowledge/history/incident.md#chunk-001",
        "knowledge/runbooks/valid.md#chunk-001",
    }
    assert all(
        chunk.reference.removeprefix("knowledge/").split("/", 1)[0]
        in CURATED_KNOWLEDGE_DIRECTORIES
        for chunk in chunks
    )
    assert all("knowledge/root.md" not in chunk.reference for chunk in chunks)
    with pytest.raises(ValueError):
        chunk_markdown(outside, root)


def test_repository_discovery_contains_exactly_eight_curated_documents() -> None:
    root = Path(__file__).parents[2] / "knowledge"

    chunks = discover_knowledge(root)
    references = {chunk.reference.split("#", 1)[0] for chunk in chunks}

    assert len(references) == 8
    assert "knowledge/README.md" not in references
    assert all(
        reference.removeprefix("knowledge/").split("/", 1)[0]
        in CURATED_KNOWLEDGE_DIRECTORIES
        for reference in references
    )


def test_deterministic_embeddings_index_and_rank_with_bounded_top_k(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "knowledge"
        (root / "runbooks").mkdir(parents=True)
        (root / "runbooks" / "one.md").write_text("# One\n\nalpha", encoding="utf-8")
        (root / "history").mkdir()
        (root / "history" / "two.md").write_text("# Two\n\nbeta", encoding="utf-8")
        provider = DeterministicEmbeddingProvider()
        store = InMemoryKnowledgeStore()

        assert await index_knowledge(root, provider, store) == 2
        retriever = KnowledgeRetriever(provider, store, top_k=99)
        results = await retriever.retrieve("alpha", "checkout-api", "1.8.4")

        assert len(results) == 2
        assert store.requested_top_k == [DEFAULT_TOP_K]
        assert results[0].chunk.reference == "knowledge/runbooks/one.md#chunk-001"
    asyncio.run(scenario())


def test_indexing_replaces_stale_rows_and_is_idempotent(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "knowledge"
        document = root / "runbooks" / "current.md"
        document.parent.mkdir(parents=True)
        document.write_text("# Current\n\nCurrent content", encoding="utf-8")
        provider = DeterministicEmbeddingProvider()
        store = InMemoryKnowledgeStore()
        stale = KnowledgeChunk(
            "knowledge/README.md#chunk-001",
            "knowledge/README.md#chunk-001",
            "README",
            1,
            "stale documentation",
            "stale-hash",
        )
        await store.replace_all([(stale, [1.0] * provider.dimensions)])

        assert await index_knowledge(root, provider, store) == 1
        first_rows = store.rows.copy()
        assert set(first_rows) == {"knowledge/runbooks/current.md#chunk-001"}

        assert await index_knowledge(root, provider, store) == 1
        assert store.rows == first_rows
    asyncio.run(scenario())


def test_indexing_removes_deleted_documents_and_empty_corpus(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "knowledge"
        runbooks = root / "runbooks"
        runbooks.mkdir(parents=True)
        first = runbooks / "first.md"
        second = runbooks / "second.md"
        first.write_text("# First\n\nFirst content", encoding="utf-8")
        second.write_text("# Second\n\nSecond content", encoding="utf-8")
        provider = DeterministicEmbeddingProvider()
        store = InMemoryKnowledgeStore()

        assert await index_knowledge(root, provider, store) == 2
        second.unlink()
        assert await index_knowledge(root, provider, store) == 1
        assert set(store.rows) == {"knowledge/runbooks/first.md#chunk-001"}

        first.unlink()
        assert await index_knowledge(root, provider, store) == 0
        assert store.rows == {}
    asyncio.run(scenario())


def test_postgres_replacement_deletes_and_inserts_in_one_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    class RecordingConnection:
        def __init__(self) -> None:
            self.statements: list[tuple[str, tuple[object, ...] | None]] = []
            self.commits = 0
            self.rollback_observed = False

        def __enter__(self) -> "RecordingConnection":
            return self

        def __exit__(self, exception_type: object, *_: object) -> None:
            self.rollback_observed = exception_type is not None

        def execute(self, statement: object, parameters: tuple[object, ...] | None = None) -> None:
            self.statements.append((str(statement), parameters))

        def commit(self) -> None:
            self.commits += 1

    connection = RecordingConnection()
    def connect(_: object) -> RecordingConnection:
        return connection

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=connect))
    chunk = KnowledgeChunk("id", "reference", "title", 1, "content", "hash")

    asyncio.run(PostgresKnowledgeStore("dsn").replace_all([(chunk, [1.0, 2.0])]))

    assert connection.statements[0] == ("DELETE FROM knowledge_chunks", None)
    assert connection.statements[1][0].startswith("INSERT INTO knowledge_chunks")
    assert connection.commits == 1
    assert not connection.rollback_observed


def test_postgres_replacement_rolls_back_when_insertion_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingConnection:
        def __init__(self) -> None:
            self.committed_rows = ["old-index"]
            self.working_rows = list(self.committed_rows)
            self.commits = 0
            self.rollbacks = 0

        def __enter__(self) -> "FailingConnection":
            return self

        def __exit__(self, exception_type: object, *_: object) -> None:
            if exception_type is not None:
                self.working_rows = list(self.committed_rows)
                self.rollbacks += 1

        def execute(self, statement: object, parameters: tuple[object, ...] | None = None) -> None:
            if str(statement) == "DELETE FROM knowledge_chunks":
                self.working_rows.clear()
            else:
                raise RuntimeError("insert failed")

        def commit(self) -> None:
            self.committed_rows = list(self.working_rows)
            self.commits += 1

    connection = FailingConnection()
    def connect(_: object) -> FailingConnection:
        return connection

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=connect))
    chunk = KnowledgeChunk("id", "reference", "title", 1, "content", "hash")

    with pytest.raises(RuntimeError, match="insert failed"):
        asyncio.run(PostgresKnowledgeStore("dsn").replace_all([(chunk, [1.0, 2.0])]))

    assert connection.committed_rows == ["old-index"]
    assert connection.working_rows == ["old-index"]
    assert connection.commits == 0
    assert connection.rollbacks == 1


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
    ctx = RunContext(deps=None, model=TestModel(), usage=RunUsage())
    assert set(asyncio.run(agent.toolset.get_tools(ctx))) == set(REQUIRED_READ_TOOLS)