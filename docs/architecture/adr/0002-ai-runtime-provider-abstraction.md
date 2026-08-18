# ADR 0002: Keep Pydantic AI and model providers behind project-owned boundaries

- Status: Accepted
- Date: 2026-08-18

## Context

The project should support a cloud provider initially while remaining capable of adding Azure OpenAI, OpenAI, Anthropic, or local/OpenAI-compatible models later.

## Decision

Use Pydantic AI as the initial AI orchestration implementation, but keep it inside the AI runtime infrastructure layer.

Application contracts and domain concepts must not expose Pydantic AI or provider SDK types.

V1 implements one real provider adapter. Additional providers are added only through later issues after the seam is proven.

## Consequences

- agent/application logic can be tested with deterministic model substitutes,
- provider migration does not leak across service boundaries,
- the project avoids a custom mega-abstraction that duplicates the framework.
