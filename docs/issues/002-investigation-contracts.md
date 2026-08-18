# Issue 002: Define investigation contracts and service boundary

## Goal

Define the typed HTTP contract between the control plane and AI runtime before adding model behavior.

## Scope

- Define request/response models for starting an AI investigation.
- Define `InvestigationResult`, `EvidenceItem`, `Citation`, and optional `ActionProposal` as project concepts.
- Add a private/internal AI-runtime endpoint that accepts an investigation request and returns a deterministic stub result.
- Add a control-plane client adapter that calls the AI-runtime endpoint.
- Add contract-focused tests on both sides.
- Document example JSON payloads under `contracts/`.

## Out of scope

- real LLM calls,
- MCP tool calls,
- retrieval,
- action authorization or execution,
- persistence.

## Architecture constraints

- Framework/provider types must not appear in the wire contract.
- `ActionProposal` is data only and carries no approval/execution semantics.
- The contract should contain stable identifiers for evidence/citations rather than raw framework objects.

## Acceptance criteria

- A control-plane endpoint can trigger the deterministic AI-runtime stub through HTTP.
- Response deserialization is strongly typed on both sides.
- Invalid payloads fail clearly.
- Tests cover the happy path and at least one invalid-contract case.
- No provider SDK dependency is introduced.
