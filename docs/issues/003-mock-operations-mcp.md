# Issue 003: Add deterministic mock operations data and read-only MCP tools

## Goal

Expose the evidence needed for the canonical incident through deterministic read-only MCP tools.

## Scope

Create a simulated operations data set for `checkout-api` and deployment `1.8.4`.

Expose these read-only tools:

- `get_service_health(service)`
- `get_logs(service, time_range)`
- `get_deployment(service)`
- `get_known_incidents(service)`

Use structured inputs and outputs. Add tests for valid requests, unknown services, invalid time ranges, and deterministic canonical-incident results.

Configure an MCP read surface that the AI runtime can later consume.

## Out of scope

- `restart_service`,
- any other state-changing tool,
- LLM integration,
- RAG,
- approval workflow,
- production authentication.

## Architecture constraints

- Follow ADR 0004.
- No write tool may be visible on the read MCP surface.
- Treat tool output as structured data.
- Keep the simulated data small and human-readable in the repository.

## Acceptance criteria

- All four read tools are discoverable and callable through MCP.
- No state-changing tool is discoverable on the read endpoint.
- Canonical incident data supports the intended diagnosis but does not hard-code a final natural-language answer.
- Tests prove deterministic behavior and read-only tool exposure.
