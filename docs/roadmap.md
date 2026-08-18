# V1 Roadmap

The backlog is intentionally ordered so every slice creates a small, reviewable architectural capability.

1. Bootstrap .NET control plane and Python AI runtime.
2. Define investigation contracts and the control-plane/AI-runtime boundary.
3. Implement deterministic mock operations data and read-only MCP tools.
4. Add model-provider configuration and the first Pydantic AI adapter.
5. Implement the single investigation agent using read-only tools.
6. Add the curated knowledge base, embeddings, retrieval, and citations.
7. Add structured `ActionProposal`, deterministic policy, and approval state.
8. Add privileged write execution through the write MCP capability and audit.
9. Add prompt-injection and AI evaluation suites.
10. Add OpenTelemetry, CI quality gates, architecture validation, and polished reference documentation.

Do not parallelize later slices into earlier ones simply because a dependency or library is already being touched.
