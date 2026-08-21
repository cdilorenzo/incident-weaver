# IncidentWeaver

> Production-oriented reference architecture for safe AI incident investigation and guarded remediation.

IncidentWeaver is a compact, architecture-first reference implementation for investigating an operational incident with evidence, constrained tool use, deterministic policy, explicit approval, and auditable privileged execution. It is not presented as a production AIOps product or an autonomous remediation platform.

## Current implementation status

This repository currently implements the architecture through the privileged-execution and audit slice described in the V1 issue backlog. The design remains intentionally small and bounded to one incident scenario: HTTP 500 failures in `checkout-api` after deployment `1.8.4`.

The implemented flow is:

```text
request
  -> .NET Control Plane
  -> Python AI Runtime
  -> RAG / curated knowledge
  -> exactly four read-only MCP capabilities
  -> grounded InvestigationResult
  -> structured ActionProposal
  -> deterministic policy
  -> explicit approval
  -> privileged .NET executor
  -> isolated Write MCP restart capability
  -> audit
```

The repository demonstrates the trust boundary explicitly: the AI runtime may investigate and propose, but the .NET control plane owns deterministic authorization, approval state, and privileged execution.

## Trust boundary

The central rule is simple:

**Python may investigate and propose. .NET owns deterministic authorization/state and privileged execution.**

- the AI runtime has read-only operational capability
- the Write MCP is on a separate network
- the AI runtime is not attached to that write network
- approval does not itself execute
- privileged execution occurs only through the Control Plane
- model output is treated as untrusted input

## Architecture at a glance

```text
Client
  |
  v
ASP.NET Core Control Plane
  |  investigation request
  v
Python AI Runtime
  |  read-only MCP and retrieval
  v
Grounded InvestigationResult + ActionProposal
  |
  v
Deterministic policy + approval state
  |
  v
Privileged .NET executor
  |
  v
Isolated Write MCP restart capability
  |
  v
Audit record
```

The AI runtime never owns state-changing credentials or write capability.

## Current stack and status

### Implemented

- .NET 10 / ASP.NET Core Control Plane
- Python 3.13 / FastAPI AI Runtime
- Pydantic AI behind project-owned interfaces
- MCP read/write separation for the simulation
- PostgreSQL + pgvector-backed retrieval and knowledge access
- structured `ActionProposal` / deterministic policy / approval flow
- isolated privileged Write MCP execution
- audit records for execution lifecycle
- Docker Compose local topology
- strict Pyright checks and repository validation harness
- custom Copilot agents and path-specific repository instructions

### Still planned for V1

- prompt-injection and security evaluation suite
- OpenTelemetry observability
- CI enforcement
- final architecture/reference documentation polish

## Local development and Compose

Start the local stack with Docker Compose:

```bash
docker compose up --build
```

The only host-accessible local entry point in the current Compose topology is the Control Plane:

- `http://localhost:8080` for the public control-plane endpoint

The AI runtime and MCP services are intentionally internal-only in the Docker network topology and are not exposed directly on localhost. The public local entry point is the Control Plane, which calls the AI runtime over the internal Compose network.

Use the canonical Python bootstrap and validation flow from the repository root:

```bash
python scripts/bootstrap-dev.py
python scripts/validate.py
```

The bootstrap script creates `.venv` with the project dependencies pinned in `requirements-dev.lock.txt`. Configure VS Code/Pylance to use the repository `.venv` interpreter.

Validate the Compose configuration without starting services:

```bash
docker compose config
```

## Agent engineering harness

This repository also demonstrates the engineering harness used to modify and review the software itself. It includes repository-level guidance, path-specific Python and .NET instructions, least-privilege custom agents, and clear separation of duties between developer, reviewer, and security reviewer roles. The project explicitly emphasizes direct evidence over proxy evidence, a deterministic completion gate, strict Python typing, and a single repository quality-gate entry point.

See:

- [AGENTS.md](AGENTS.md)
- [.github/copilot-instructions.md](.github/copilot-instructions.md)

## What is deliberately not included

IncidentWeaver intentionally stays within a narrow V1 scope. It does not include:

- autonomous remediation
- multi-agent orchestration
- Kubernetes or platform complexity
- production OAuth or SSO
- general-purpose vendor integrations
- a broad AIOps platform

This is a focused reference architecture and validation harness rather than a general product surface.

## Repository layout

```text
.github/              Copilot instructions, custom agents, reusable prompts
docs/                 V1 scope, architecture, ADRs, issue specifications
contracts/             Cross-service contract guidance
src/control-plane/     ASP.NET Core control plane
src/ai-runtime/        Python AI runtime
src/ops-mcp/           MCP adapters for read and write surfaces
tests/                 Tests grouped by runtime
evaluations/           AI evaluation datasets and runners
knowledge/             Curated operational knowledge base
scripts/               Bootstrap and repository validation
```

## License

MIT
