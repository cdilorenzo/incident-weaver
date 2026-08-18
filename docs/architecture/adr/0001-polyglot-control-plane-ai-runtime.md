# ADR 0001: Separate deterministic control plane from Python AI runtime

- Status: Accepted
- Date: 2026-08-18

## Context

The project needs to demonstrate both enterprise software architecture and modern Python AI engineering without making language choice an end in itself.

## Decision

Use ASP.NET Core for the deterministic control plane and Python/FastAPI for the AI runtime.

The control plane owns lifecycle, policy, approval, privileged execution, and audit. The Python runtime owns model interaction, retrieval, read-only tool orchestration, and structured AI output.

Communication between them uses an explicit HTTP contract.

## Consequences

Positive:

- trust and responsibility boundaries are visible,
- existing enterprise/.NET strengths remain meaningful,
- Python AI libraries can evolve behind the runtime boundary,
- provider/framework changes do not require control-plane changes.

Trade-offs:

- two runtimes must be built and tested,
- cross-service contracts require deliberate versioning,
- local development needs orchestration.

## Rejected alternatives

- all-.NET: reduces Python AI engineering visibility and limits experimentation value for this showcase,
- all-Python: weakens the intended control-plane architecture story,
- many microservices: adds operational size without increasing architecture depth.
