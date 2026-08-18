# System Architecture

## Architectural style

IncidentWeaver is a small polyglot system with a deterministic control plane and an isolated probabilistic AI runtime.

## Components

### ASP.NET Core Control Plane

Responsibilities:

- public API boundary,
- investigation lifecycle,
- correlation/request identity,
- policy evaluation,
- approval state,
- privileged action execution,
- audit record ownership.

The control plane does not perform model reasoning.

### Python AI Runtime

Responsibilities:

- model-provider adapter selection,
- investigation-agent orchestration,
- retrieval,
- read-only MCP tool usage,
- evidence synthesis,
- structured `InvestigationResult` creation.

The AI runtime can propose but cannot authorize or execute a state-changing action.

### Operations MCP Adapter

Responsibilities:

- expose deterministic simulated operations capabilities,
- separate read and write capability surfaces,
- validate tool inputs,
- return structured tool results.

The same implementation may be deployed/configured as separate read and write capability endpoints, but the AI runtime receives access only to the read surface.

### PostgreSQL / pgvector

Introduced only when needed by the retrieval slice. Local development may use one PostgreSQL instance, but logical data ownership and credentials remain separated by component.

## Main investigation flow

```text
1. Client -> Control Plane: start investigation
2. Control Plane -> AI Runtime: investigation request
3. AI Runtime -> Read MCP: health/log/deployment/incident queries
4. AI Runtime -> Retrieval: relevant runbooks and knowledge
5. AI Runtime -> Control Plane: structured InvestigationResult
6. Control Plane: validate and persist result
7. Control Plane: evaluate ActionProposal with deterministic policy
8. User: approve or reject
9. Control Plane -> privileged executor -> Write MCP
10. Control Plane: persist audit and execution result
```

## Cross-service contract rule

The HTTP contract between control plane and AI runtime is project-owned. Framework-specific model types must not cross the boundary. JSON/OpenAPI is the transport representation; each runtime owns its local typed model.

## Deployment principle

V1 optimizes for local Docker Compose and clear boundaries, not independent microservice scaling. Process separation exists only where it makes a trust or technology boundary explicit.
