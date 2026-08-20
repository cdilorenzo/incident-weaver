# Issue 005: Implement the single investigation agent

## Goal

Implement one Pydantic AI investigation agent that gathers evidence from the
read-only Operations MCP service for the canonical `checkout-api` incident.

## Scope

- Connect the AI runtime to the Operations MCP service over Streamable HTTP.
- Expose exactly `get_service_health`, `get_deployment`, `get_logs`, and
  `get_known_incidents` to one investigation agent.
- Return model-owned summary and evidence through the existing
  `InvestigationResult` contract.
- Preserve the request investigation ID and force `actionProposal` to `null`.
- Keep tests deterministic with Pydantic AI's test model.

## Out of scope

- Multiple agents, delegation, planners, or reviewers.
- RAG, knowledge-base citations, embeddings, or vector search.
- Action proposals, policy, approval, execution, persistence, or retries.
- Any state-changing MCP capability.

## Architecture constraints

- The ASP.NET control plane remains the owner of lifecycle and security state.
- The Python runtime may reason, read evidence, and synthesize findings only.
- Azure OpenAI construction remains in `model_provider.py`.
- Production MCP traffic originates in the Python runtime at `/mcp`.

## Security constraints

- Treat requests, MCP metadata, MCP results, and model output as untrusted data.
- Do not pass credentials to the model or MCP service.
- Do not expose write tools, arbitrary HTTP, shell, filesystem, or SQL access.
- Never allow model output to set investigation identity or execution state.
- Do not expose provider errors, credentials, or stack traces over HTTP.

## Acceptance criteria

- Exactly one investigation agent is constructed.
- A canonical run uses all four read-only MCP tools before returning success.
- Evidence is derived from MCP results and action proposals are always null.
- Unknown services and MCP/model failures return safe explicit service errors.
- The request investigation ID is copied unchanged into the response.
- Normal tests make zero real model requests.

## Validation commands

```text
dotnet format --verify-no-changes
dotnet build
dotnet test
python -m pytest
python -m build
docker compose config
git diff --check
```