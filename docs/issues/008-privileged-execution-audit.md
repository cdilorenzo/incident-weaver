# Issue 008: Privileged write execution through MCP and audit

## Goal

Add one explicitly privileged remediation path, `restart_instance`, that can only be executed by the ASP.NET control plane through a dedicated write-only MCP surface. The AI runtime remains a read-only investigator and never receives write capability, credentials, or execution authority.

## Scope

- add a dedicated write MCP service exposing exactly one mutation tool: `restart_instance`
- keep the read-only AI-runtime MCP surface unchanged at four tools
- ensure the Control Plane owns approval, execution, freshness, and audit state
- add a privileged .NET executor that calls the write MCP using authoritative proposal values only
- add execution lifecycle transitions and replay protection
- record deterministic execution audit records with system-owned metadata
- expose a minimal audit inspection endpoint
- update Docker Compose topology to physically separate read and write MCP networks

## Out of scope

- deploy, rollback, restart_service, arbitrary shell execution, or generic tool dispatch
- AI runtime execution awareness or write capability
- durable workflows, OAuth, or RBAC work
- full vendor integrations or production observability features

## Write capability boundary

The only valid privileged action is:

- `restart_instance`

The Control Plane may invoke a dedicated write MCP surface only after:

1. the runtime returns a structured `ActionProposal`
2. deterministic policy evaluates it as allowed
3. a human approves the exact immutable proposal
4. the proposal is still fresh and unexpired
5. the request is executed through the control-plane-owned executor

The AI runtime is never given write MCP configuration or a write client.

## Execution state machine

The V1 lifecycle is extended narrowly:

- `PolicyDenied` -> terminal
- `PendingApproval` -> `Approved` or `Rejected`
- `Approved` -> `Executing` -> `Executed`
- `Approved` -> `Executing` -> `ExecutionFailed`
- `Approved` -> `Expired` when stale
- `Rejected`, `PolicyDenied`, `Executed`, `ExecutionFailed`, and `Expired` remain terminal for this slice

Only an `Approved` and still-fresh action may begin execution. Beginning execution is atomic and single-winner by state transition. No automatic retry occurs.

## Replay protection

Two simultaneous execute requests for the same `ActionId` must result in at most one MCP write invocation.

Replay protection occurs in the control plane state store using an atomic transition: `Approved` -> `Executing` is the winning step. The state machine denies re-entry once execution starts or completes.

## Failure and unknown-outcome behavior

A timeout or remote failure must never report success. The execution state moves to `ExecutionFailed`, a deterministic failure reason is recorded, and the caller gets a safe explicit result. A timeout may represent an unknown remote outcome; the state machine does not retry automatically.

## Audit ownership

The ASP.NET control plane owns audit records. A new `IAuditStore` keeps deterministic lifecycle metadata only. Audit records are process-local in V1 and do not write into the AI runtime retrieval database.

Record types include:

- execution requested
- execution started
- execution succeeded
- execution failed
- execution expired

Each record contains only trustable lifecycle facts such as `AuditId`, `ActionId`, `InvestigationId`, event type, action type, service, target, timestamp, deterministic status/reason code.

## Network separation

The deployment topology keeps the write surface isolated:

- `control-plane` attaches to `control-ai` and `control-write`
- `ai-runtime` attaches only to `control-ai` and `ai-read`
- `ops-mcp` remains read-only and attached to `ai-read`
- `ops-mcp-write` is attached only to `control-write`
- no host port is published for the write MCP server
- the AI runtime is not configured with a write MCP endpoint

## Acceptance criteria

- only `restart_instance` is discoverable on the write MCP surface
- the read-only MCP server still exposes only four tools
- invalid service or instance targets are rejected by the write server
- valid canonical `checkout-api` / `instance-3` requests succeed
- the control plane refuses execution when the action is not `Approved` or is stale
- execution transitions are atomic and replay-safe
- execution success and failure are audited
- the public audit endpoint returns deterministic records in order
- the AI runtime has no write capability or write network attachment
- compose topology and tests enforce the separation

## Validation

Run:

- `dotnet format --verify-no-changes`
- `dotnet build`
- `dotnet test`
- `python -m pytest`
- `docker compose config`
- `git diff --check`

Additional verification includes:

- approval does not automatically execute
- only a fresh `Approved` action may execute
- only a single write invocation occurs per action
- the write MCP tool set is exactly the singleton `restart_instance`
- the AI runtime has zero write capability
- success and failure outcomes are audited
- no automatic retry is triggered
