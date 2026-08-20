# Issue 006: Curated knowledge retrieval

## Goal

Add a small production-oriented RAG capability to the Python AI runtime using
repository-owned Markdown, Azure OpenAI embeddings, PostgreSQL/pgvector, and
runtime-owned citations.

## Scope

Deterministic Markdown chunking and indexing, one Azure embedding adapter,
bounded semantic retrieval before the existing investigation agent, and
sanitized knowledge evidence tied to retrieved chunks.

## Out of scope

Multiple agents, retrieval tools, prompt-injection evaluations, uploads,
crawling, reranking, hybrid search, write MCP, actions, approvals, and audit.

## Architecture and security constraints

Retrieval is AI-runtime-owned and the control plane has no database access.
The agent retains exactly four read-only MCP tools. Knowledge is untrusted
reference data, never instructions. The model cannot create citations or
action proposals, and no credentials, arbitrary paths, SQL, shell, or HTTP
capabilities cross the runtime boundary.

## Acceptance criteria

- Eight small fictional Markdown documents are indexed deterministically.
- Chunk IDs and references are stable and retrieval top-k is bounded.
- Azure embeddings are isolated behind `EmbeddingProvider`.
- Retrieval occurs before the one investigation agent and is included as delimited context.
- Runtime-generated citations reference only retrieved chunks and evidence is bounded/sanitized.
- Retrieval/index failures return a safe service error and never fabricate evidence.
- Existing exact-four-tool and `ActionProposal: null` invariants remain true.

## Validation commands

```text
python -m pytest
python -m build
docker compose config
git diff --check
```

With local credentials and Compose running, index explicitly with the
repository's indexing entry point; indexing is never performed on startup or
per investigation request.