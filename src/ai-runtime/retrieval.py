from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from embedding import EmbeddingProvider, EmbeddingSettings, AzureOpenAIEmbeddingProvider
from text_safety import sanitize_untrusted_text


MAX_CHUNK_LENGTH = 700
DEFAULT_TOP_K = 4
CURATED_KNOWLEDGE_DIRECTORIES = ("runbooks", "history")


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    reference: str
    title: str
    chunk_index: int
    content: str
    content_hash: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    score: float


class KnowledgeStore(Protocol):
    async def replace_all(self, chunks: Sequence[tuple[KnowledgeChunk, list[float]]]) -> None: ...

    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]: ...


def _split_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    pieces: list[str] = []
    for paragraph in paragraphs:
        while len(paragraph) > MAX_CHUNK_LENGTH:
            boundary = paragraph.rfind(" ", 0, MAX_CHUNK_LENGTH + 1)
            boundary = boundary if boundary > 0 else MAX_CHUNK_LENGTH
            pieces.append(paragraph[:boundary].strip())
            paragraph = paragraph[boundary:].strip()
        if paragraph:
            pieces.append(paragraph)
    return pieces


def chunk_markdown(path: Path, knowledge_root: Path) -> list[KnowledgeChunk]:
    """Chunk only repository-owned Markdown and derive stable references from its relative path."""

    resolved_root = knowledge_root.resolve()
    resolved_path = path.resolve()
    if resolved_path.parent != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError("Knowledge path must be inside the repository-owned knowledge directory")
    if resolved_path.suffix.lower() != ".md":
        raise ValueError("Only Markdown knowledge documents are indexable")

    relative = resolved_path.relative_to(resolved_root).as_posix()
    lines = resolved_path.read_text(encoding="utf-8").splitlines()
    title = resolved_path.stem.replace("-", " ").title()
    sections: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("#"):
            if current:
                sections.append("\n".join(current).strip())
                current = []
            heading = line.lstrip("#").strip()
            if heading:
                title = heading
        elif line.strip():
            current.append(line)
        elif current and current[-1] != "":
            current.append("")
    if current:
        sections.append("\n".join(current).strip())

    chunks: list[KnowledgeChunk] = []
    for section in sections:
        for content in _split_text(section):
            index = len(chunks) + 1
            reference = f"knowledge/{relative}#chunk-{index:03d}"
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunks.append(KnowledgeChunk(reference, reference, title, index, content, content_hash))
    return chunks


def discover_knowledge(root: Path) -> list[KnowledgeChunk]:
    paths = [
        path
        for directory in CURATED_KNOWLEDGE_DIRECTORIES
        for path in (root / directory).rglob("*.md")
    ]
    return [chunk for path in sorted(paths) for chunk in chunk_markdown(path, root)]


class InMemoryKnowledgeStore:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[KnowledgeChunk, list[float]]] = {}
        self.requested_top_k: list[int] = []

    async def replace_all(self, chunks: Sequence[tuple[KnowledgeChunk, list[float]]]) -> None:
        self.rows = {chunk.chunk_id: (chunk, vector) for chunk, vector in chunks}

    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        self.requested_top_k.append(top_k)
        bounded_k = min(max(top_k, 1), DEFAULT_TOP_K)
        def cosine(vector: list[float]) -> float:
            denominator = math.sqrt(sum(value * value for value in embedding)) * math.sqrt(sum(value * value for value in vector))
            return sum(left * right for left, right in zip(embedding, vector)) / denominator if denominator else 0
        ranked = sorted((RetrievedChunk(chunk, cosine(vector)) for chunk, vector in self.rows.values()), key=lambda item: (-item.score, item.chunk.chunk_id))
        return ranked[:bounded_k]


class PostgresKnowledgeStore:
    def __init__(self, dsn: str, dimensions: int = 1536) -> None:
        self.dsn = dsn
        self.dimensions = dimensions

    async def initialize(self) -> None:
        import psycopg
        with psycopg.connect(self.dsn) as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id TEXT PRIMARY KEY, reference TEXT NOT NULL, title TEXT NOT NULL,
                chunk_index INTEGER NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL,
                embedding vector({self.dimensions}) NOT NULL)""")
            connection.commit()

    async def replace_all(self, chunks: Sequence[tuple[KnowledgeChunk, list[float]]]) -> None:
        import psycopg
        with psycopg.connect(self.dsn) as connection:
            connection.execute("DELETE FROM knowledge_chunks")
            for chunk, vector in chunks:
                connection.execute("""INSERT INTO knowledge_chunks
                    (chunk_id, reference, title, chunk_index, content, content_hash, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET reference=EXCLUDED.reference,
                    title=EXCLUDED.title, chunk_index=EXCLUDED.chunk_index, content=EXCLUDED.content,
                    content_hash=EXCLUDED.content_hash, embedding=EXCLUDED.embedding""",
                    (chunk.chunk_id, chunk.reference, chunk.title, chunk.chunk_index, chunk.content,
                     chunk.content_hash, str(vector).replace(" ", "")))
            connection.commit()

    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        import psycopg
        bounded_k = min(max(top_k, 1), DEFAULT_TOP_K)
        with psycopg.connect(self.dsn) as connection:
            rows = connection.execute("""SELECT chunk_id, reference, title, chunk_index, content,
                content_hash, 1 - (embedding <=> %s::vector) AS score
                FROM knowledge_chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
                (str(embedding).replace(" ", ""), str(embedding).replace(" ", ""), bounded_k)).fetchall()
        return [RetrievedChunk(KnowledgeChunk(*row[:6]), float(row[6])) for row in rows]


class KnowledgeRetriever:
    def __init__(self, provider: EmbeddingProvider, store: KnowledgeStore, top_k: int = DEFAULT_TOP_K) -> None:
        self.provider = provider
        self.store = store
        self.top_k = min(max(top_k, 1), DEFAULT_TOP_K)

    async def retrieve(self, question: str, service: str, deployment: str | None) -> list[RetrievedChunk]:
        query = f"question: {question}\nservice: {service}\ndeployment: {deployment or 'none'}"
        return await self.store.search(await self.provider.embed(query), self.top_k)


async def index_knowledge(root: Path, provider: EmbeddingProvider, store: KnowledgeStore) -> int:
    chunks = discover_knowledge(root)
    await store.replace_all([(chunk, await provider.embed(chunk.content)) for chunk in chunks])
    return len(chunks)


def create_configured_retriever() -> KnowledgeRetriever:
    dsn = os.getenv("INCIDENTWEAVER_KNOWLEDGE_DSN")
    if not dsn:
        raise ValueError("Missing required retrieval configuration: INCIDENTWEAVER_KNOWLEDGE_DSN")
    dimensions = int(os.getenv("INCIDENTWEAVER_EMBEDDING_DIMENSIONS", "1536"))
    return KnowledgeRetriever(AzureOpenAIEmbeddingProvider(EmbeddingSettings.from_env()), PostgresKnowledgeStore(dsn, dimensions))