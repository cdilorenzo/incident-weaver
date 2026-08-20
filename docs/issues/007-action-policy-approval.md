# Issue 007: Structured ActionProposal, deterministic policy, and approval state

## Goal

Allow the single investigation agent to return one advisory remediation draft as untrusted structured data. The ASP.NET Control Plane creates the authoritative immutable proposal, evaluates deterministic policy, and owns explicit approval state.

## Scope

- Add an AI-runtime `ActionProposalDraft` containing only `actionType`, `target`, and `rationale`.
- Sanitize and bound draft values before they cross the HTTP boundary.
- Generate the authoritative `ActionId` in the Control Plane.
- Bind proposals to the request-owned investigation and service and Control-Plane-owned evidence IDs.
- Deny unsupported or unsafe proposals with deterministic policy.
- Store proposal, policy, and approval state in a process-local thread-safe store.
- Expose action inspection, approval, and rejection endpoints.

## Out of scope

Write MCP, privileged execution, credentials, durable persistence, RBAC/OAuth, audit execution records, automatic remediation, replay protection, signing, and additional agents.

## Trust boundaries

Python may reason and propose. It cannot authorize, approve, execute, choose identity, create trusted evidence IDs, or provide lifecycle state. The Control Plane treats the draft and runtime evidence as hostile input and owns authoritative evidence identity, source classification used by policy, proposal binding, policy, approval, and state. Server-generated IDs establish ownership, not factual truth: Slice 007 does not provide independent cryptographic or source attestation of operational facts. No component executes an action in this slice.

## Proposal ownership

The runtime draft has no `ActionId`, `InvestigationId`, service, evidence IDs, policy result, approval state, or execution state. The Control Plane creates an immutable authoritative proposal with server-generated `ActionId`, request-owned investigation/service, validated action semantics, and evidence IDs selected from Control-Plane-bound evidence records. Runtime evidence IDs are transport data only and are never authoritative.

## Deterministic policy

Only `restart_instance` is supported. The service must match the validated request, the target must be one explicit `instance-*` target without wildcards or service-wide scope, rationale must be non-empty and bounded, all referenced evidence must exist, and the result must contain evidence from `get_service_health`, `get_logs`, `get_deployment`, and `get_known_incidents`. Policy never parses model prose or accepts a model policy result.

## Approval state machine

A proposal is either `PolicyDenied`, or, when allowed, `PendingApproval`. Pending proposals may transition exactly once to `Approved` or `Rejected`. Denied and terminal states cannot transition. There is no `Executed` state and approval has no execution side effect.

State is process-local and is not preserved across Control Plane restarts. The narrow store interface leaves persistence replaceable without changing the trust model.

## Acceptance criteria

- A canonical investigation can return a sanitized restart-instance draft without an ActionId.
- The Control Plane generates ActionId and owns investigation, service, and evidence bindings.
- Unsupported actions and wildcard targets remain inert data and are deterministically denied.
- Required operational evidence is required for policy approval.
- Allowed proposals enter PendingApproval; explicit approve/reject calls produce terminal state.
- Unknown actions return 404 and invalid transitions return 409.
- Approved proposals are not executed and no write MCP exists.
- Existing four read-only MCP tools, runtime-owned evidence/citations, retrieval, and offline tests remain intact.

## Validation

Run `dotnet format --verify-no-changes`, `dotnet build`, `dotnet test`, `python -m pytest`, `python -m build` from `src/ai-runtime`, `docker compose config`, and `git diff --check`. Verify that ActionId is generated only by the Control Plane, policy and approval state remain there, and no model or embedding requests occur in tests.
