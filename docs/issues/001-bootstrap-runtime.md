# Issue 001: Bootstrap control plane and AI runtime

## Goal

Create the smallest runnable polyglot skeleton that proves the .NET control-plane and Python AI-runtime boundary without implementing AI behavior.

## Scope

### Control plane

- Create a .NET 10 solution/project under `src/control-plane`.
- Add an ASP.NET Core API with `/health`.
- Add a test project under `tests/control-plane`.
- Add one test that validates the health endpoint or application startup.

### AI runtime

- Create a Python 3.13+ project under `src/ai-runtime`.
- Use FastAPI with a `/health` endpoint.
- Use a modern `pyproject.toml`-based dependency definition.
- Add pytest tests under `tests/ai-runtime`.
- Add one health/startup test.

### Local orchestration

- Add Dockerfiles for both runtimes.
- Add a root `compose.yaml` that starts only these two services.
- Add health checks where practical.
- Document local start/test commands in the README.

## Out of scope

- LLM SDKs or Pydantic AI,
- MCP,
- RAG or databases,
- action proposals,
- authentication/authorization,
- approval workflow,
- OpenTelemetry,
- CI/CD,
- product UI.

## Architecture constraints

- Follow ADR 0001.
- The control plane must not reference Python/AI framework packages.
- Do not create speculative clean-architecture layers with no behavior yet.
- Keep each runtime to the minimum structure needed for later slices.

## Acceptance criteria

- Both services start locally.
- Both `/health` endpoints return success.
- .NET tests pass.
- Python tests pass.
- Docker Compose can start the two services without external credentials.
- No AI/provider/MCP dependency exists yet.
- README contains exact local run and test commands.

## Suggested validation

```text
dotnet build
dotnet test
python -m pytest
docker compose config
docker compose up --build
```

## Copilot entry point

Use `.github/prompts/bootstrap-runtime.prompt.md`.
