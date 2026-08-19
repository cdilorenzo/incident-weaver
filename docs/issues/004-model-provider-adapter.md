# Issue 004: Add model provider configuration and the first Pydantic AI adapter

## Goal

Introduce explicit model-provider configuration and the first real Pydantic AI model adapter inside the Python AI runtime.

This slice establishes the model/provider seam.

It does NOT implement the investigation agent yet.

## Scope

### Configuration

- Add a small project-owned configuration model for the AI runtime.
- Support the minimum configuration required for Azure OpenAI.
- Read provider-specific values from environment variables.
- Validate required configuration explicitly and fail clearly when settings are missing or invalid.
- Keep Azure/OpenAI/Pydantic-specific types inside the AI runtime infrastructure implementation.

### Provider seam

- Add the smallest useful project-owned seam for model construction.
- Implement a single real V1 provider adapter for Azure OpenAI.
- Keep the provider adapter in the AI runtime infrastructure layer.
- Keep deterministic Slice 002 behavior unchanged unless this issue explicitly adds configuration-only infrastructure.

### Pydantic AI integration

- Add Pydantic AI as an infrastructure dependency for the AI runtime.
- Construct a Pydantic AI model using the supported Azure OpenAI integration.
- Do not add prompts, tools, MCP use, retrieval, or reasoning behavior yet.

## Out of scope

- investigation-agent orchestration,
- MCP tool calls from the model,
- system prompts for incident investigation,
- RAG,
- embeddings,
- vector storage,
- PostgreSQL,
- ActionProposal generation,
- policy evaluation,
- approval workflow,
- write MCP,
- privileged execution,
- provider failover,
- multiple providers,
- Anthropic,
- Ollama/local models,
- OpenAI as a second adapter,
- Azure Managed Identity or complex production credential flows,
- retry/resilience infrastructure,
- OpenTelemetry,
- evaluation suites.

## Architecture constraints

- Follow ADR 0001 and ADR 0002.
- Keep the control plane and AI runtime trust boundaries intact.
- The AI runtime must not gain write capability or credentials.
- Provider-specific SDK types must not leak through HTTP contracts or project domain models.
- The design should make a later second provider possible without exposing provider-specific SDK types beyond the AI runtime infrastructure layer.
- Do not add a generic provider registry, reflection-based factory, or speculative abstraction for future providers.

## Required configuration shape

Minimum Azure OpenAI settings for V1:

- provider
- deployment/model identifier
- Azure OpenAI endpoint
- API version
- API key

Use environment variables for secrets and deployment-specific settings. Secret values must never be committed to the repository.

## Acceptance criteria

- A valid Azure OpenAI configuration is accepted and parsed successfully.
- Missing required configuration fails clearly.
- Unsupported provider values fail clearly.
- The Azure OpenAI adapter/model can be constructed from valid settings.
- Provider-specific objects remain in the infrastructure/provider layer.
- Existing investigation endpoints remain deterministic and do not invoke the model.
- No test requires Azure or a real API key.
- The test suite performs zero accidental real model requests.

## Security requirements

- No secret values are committed.
- No secrets are included in exceptions or logs.
- No provider credential enters the HTTP contracts.
- No provider credential enters MCP.
- No model/provider capability gains access to write operations.
- The model layer remains untrusted relative to the deterministic control plane.

## Validation

Run the following checks:

```text
dotnet format --verify-no-changes
dotnet build
dotnet test
python -m pytest
python -m build
docker compose config
git diff --check
```

If Docker is unavailable, report Compose validation separately as an environment limitation.

## Copilot entry point

Implement the configuration model, provider seam, and Azure OpenAI adapter with deterministic tests while preserving the existing investigation stub.
