# IncidentWeaver

> Evidence-driven AI incident investigation with guarded remediation.

IncidentWeaver is an open-source reference architecture for building safe AI operations assistants over existing enterprise systems.

The project demonstrates how a production-oriented agentic system can investigate an operational incident, collect evidence from trusted sources, propose a remediation, and cross a state-changing execution boundary only after deterministic policy checks and explicit human approval.

## Design principle

**Architecture depth over architecture size.**

The repository intentionally optimizes for a small number of deeply implemented architectural concerns rather than a broad feature set.

## V1 scenario

A developer reports:

> Checkout API returns HTTP 500 since deployment 1.8.4. What happened?

The system should:

1. retrieve relevant operational knowledge,
2. inspect deployment, health, logs, and known incidents through read-only MCP tools,
3. correlate the evidence,
4. return a structured investigation result with citations,
5. propose a remediation when justified,
6. require deterministic policy evaluation and explicit approval for state-changing actions,
7. execute an approved action outside the AI runtime,
8. write an auditable record of the decision and execution.

## Architecture at a glance

```text
Client
  |
  v
ASP.NET Core Control Plane
  |  investigation request
  v
Python AI Runtime ----> Read-only MCP capability ----> Mock Operations System
  |
  | InvestigationResult + ActionProposal
  v
ASP.NET Policy / Approval / Audit
  |
  | approved action only
  v
Privileged Action Executor ----> Write MCP capability ----> Mock Operations System
```

The AI runtime never owns state-changing credentials or capabilities.

## Planned V1 stack

- .NET 10 / ASP.NET Core for the control plane
- Python 3.13+ / FastAPI for the AI runtime
- Pydantic AI behind project-owned abstractions
- Model Context Protocol for operations tools
- PostgreSQL + pgvector for retrieval in a later slice
- OpenTelemetry for traces and structured telemetry
- Docker Compose for local development
- GitHub Actions for CI

## Repository layout

```text
.github/              Copilot instructions, custom agents, reusable prompts
docs/                 V1 scope, architecture, ADRs, issue specifications
contracts/             Cross-service contract guidance
src/control-plane/     ASP.NET Core control plane
src/ai-runtime/        Python AI runtime
src/ops-mcp/           MCP adapter over the simulated operations system
tests/                 Tests grouped by runtime
evaluations/           AI evaluation datasets and runners
knowledge/             Small curated operational knowledge base
```

## Status

The repository is currently in the architecture and bootstrap phase. Product implementation starts with the small slices documented under `docs/issues/`.

## Local development

Start both runtime services with Docker Compose:

```bash
docker compose up --build
```

The control plane health endpoint is available at `http://localhost:8080/health`, and the AI runtime health endpoint is available at `http://localhost:8000/health`.

Run the .NET build and tests from the repository root:

```bash
dotnet build
dotnet test
```

Run the Python tests from the repository root:

```bash
python scripts/bootstrap-dev.py
python scripts/validate.py
```

The bootstrap command creates `.venv` with both Python projects, their development extras, and the pinned quality-gate dependencies from `requirements-dev.lock.txt`. Configure VS Code/Pylance to use the repository `.venv` interpreter.

Validate the Compose configuration without starting services:

```bash
docker compose config
```

## License

MIT
