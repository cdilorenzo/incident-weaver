# ADR 0006: Stable operations connector/provider contracts (CONN-001)

- Status: Accepted
- Date: 2026-09-03

## Context

IncidentWeaver's read/write operational capabilities (`get_service_health`,
`get_logs`, `get_deployment`, `get_known_incidents`, `restart_instance`) are
currently implemented directly inside the MCP tool functions in
`src/ops-mcp/server.py` and `src/ops-mcp/write_server.py`, backed by a
hard-coded in-memory dataset for `checkout-api`.

Integrating a real operational system (Kubernetes, Grafana/Loki, Datadog,
Splunk, Azure Monitor, ArgoCD, ServiceNow, PagerDuty, etc.) without a stable
seam would force vendor-specific branching directly into the MCP tool
layer, coupling the core to specific vendors and risking accidental
privilege expansion. This changes a structural boundary (how operational
data enters the system), so an ADR is warranted.

This design is intentionally minimal. It is not a plugin marketplace, not a
dynamic tool-loading mechanism, and it implements exactly one additional
(illustrative, non-production) example beyond the existing mock.

## Decision

Introduce a `connectors` package (`src/ops-mcp/connectors/`) that defines
two disjoint Python `Protocol` contracts and a small set of typed errors.
The existing MCP tool layer becomes a thin adapter that only translates
between the MCP wire format and a configured connector; it contains no
vendor-specific logic.

```text
IncidentWeaver Core (MCP tool layer: server.py / write_server.py)
            |
            v
   connectors.contracts (ReadOperationsConnector / WriteOperationsConnector)
            |
   +--------+-----------------+------------------------+
   |                          |                         |
MockReadConnector /   KubernetesReadConnector /   (future vendor,
MockWriteConnector    KubernetesWriteConnector      out of scope for V1)
(wired in today)      (illustrative only, not wired in)
```

### Contracts

```python
class ReadOperationsConnector(Protocol):
    def get_service_health(self, service: str) -> ServiceHealth: ...
    def get_logs(self, service: str, time_range: TimeRange) -> LogResult: ...
    def get_deployment(self, service: str) -> Deployment: ...
    def get_known_incidents(self, service: str) -> KnownIncidentResult: ...

class WriteOperationsConnector(Protocol):
    def restart_instance(self, action_id: str, service: str, instance: str) -> RestartResult: ...
```

`ReadOperationsConnector` and `WriteOperationsConnector` are separate
`Protocol`s with no shared members. A component typed against one cannot
structurally reach the other. This mirrors and reinforces ADR 0004 at the
connector layer, not just at the MCP transport/deployment layer.

Request/response shapes (`ServiceHealth`, `Deployment`, `LogResult`,
`KnownIncidentResult`, `RestartResult`, `TimeRange`, …) live in
`connectors/models.py` as `TypedDict`s, matching the existing MCP tool
schema style, and are the only structured data a connector may return.

### Error model

`connectors/contracts.py` defines a small typed error hierarchy, all
subclasses of `ConnectorError`:

| Error | Meaning |
| --- | --- |
| `UnknownServiceError` | The `service` identifier is not known to this connector. |
| `UnknownInstanceError` | The `instance` identifier is not known to this connector. |
| `InvalidTimeRangeError` | The requested time range is malformed or `start >= end`. |
| `UnsupportedCapabilityError` | This connector does not implement the requested capability at all. |
| `TransientProviderError` | The underlying provider failed in a way that may succeed on retry (timeout, connectivity, rate limit). |

The MCP tool layer does not catch these; FastMCP already converts any
raised exception into a `ToolError` carrying the original message, so
callers see a clear, typed failure without the tool layer needing
vendor-specific `except` branches. Distinguishing `UnsupportedCapabilityError`
(permanent, capability not offered) from `TransientProviderError`
(retryable) lets future policy/retry logic (outside this issue's scope)
make that distinction later without redesigning the contract.

### Must every connector implement every read capability?

No. A connector must expose all four read methods (so failures are typed
and explicit, never an `AttributeError`), but any method may raise
`UnsupportedCapabilityError` if the backing vendor genuinely has no
equivalent (see the Kubernetes example: no log backend, no incident
history). Unsupported capabilities must fail loudly, never return
fabricated or empty-but-successful data.

### Identifiers

- **`service`**: an opaque string naming a logical service the way
  IncidentWeaver's core already refers to it (e.g. `checkout-api`). A
  connector owns mapping this onto its own vendor concept (Kubernetes
  namespace/deployment name, Datadog service tag, etc.). The core never
  interprets or rewrites it.
- **`instance`**: an opaque string naming one addressable unit of that
  service (e.g. `instance-3`, or a Kubernetes pod name). The write
  capability requires a non-empty, non-wildcard instance; a connector must
  reject wildcarding before ever reaching a vendor API, so "restart
  everything" can never be expressed at this layer.

### Vendor-specific metadata

Response models carry an optional `vendor_metadata: dict[str, str]` field
for pass-through, non-authoritative vendor context (e.g. Kubernetes pod
phase, namespace). It is informational only: policy, approval, and
diagnosis must never depend on its presence, and it must never carry
credentials or secrets.

### Credential ownership

Each connector implementation owns constructing and using its own
credentials, sourced from its own configuration (env vars, mounted
secrets, cloud identity, kubeconfig, etc.). Credentials never appear in a
request/response model, never appear in a `ConnectorError` message, and
never cross into the AI runtime or control plane. This preserves the
existing "provider credentials do not enter model-visible content"
invariant.

### Configuration ownership

`connectors/config.py` owns *selecting* which connector implementation is
active for a given running MCP process, via
`INCIDENTWEAVER_OPS_READ_CONNECTOR` / `INCIDENTWEAVER_OPS_WRITE_CONNECTOR`
environment variables (defaulting to `mock`). Only connectors safe to run
without external accounts are registered in the selectable set today. This
keeps configuration ownership inside the ops-mcp process boundary — neither
the AI runtime nor the control plane ever selects or configures a
connector.

### Normalization responsibilities

The connector implementation normalizes vendor-native data into the shared
`connectors.models` shapes. The MCP tool layer performs no normalization;
it only forwards the connector's already-normalized result.

### Deployment: in-process vs. behind MCP

Connectors run **in-process inside the existing ops-mcp service**, behind
the already-stable MCP tool functions. MCP remains the transport/process
boundary between the AI runtime, the control plane, and operational data
(ADR 0004); connectors are an internal seam within that boundary, not a new
external process type. This keeps the process topology (`ops-mcp`,
`ops-mcp-write`) and existing MCP contracts unchanged while still allowing
a real vendor SDK to be added as a connector dependency later without
touching the MCP tool layer.

### Which existing MCP contracts remain stable?

The four read tool signatures (`get_service_health`, `get_logs`,
`get_deployment`, `get_known_incidents`) and the one write tool signature
(`restart_instance`) are unchanged by this design and remain the stable
external contract (issue 003 acceptance criteria continue to hold
unchanged; see the existing test suite in `tests/ops-mcp/`).

### Preventing connectors from expanding privileged authority

- The MCP tool set exposed by `server.py` / `write_server.py` is defined
  statically in code; a connector has no mechanism to register, add, or
  rename an MCP tool. Dynamic tool loading is explicitly out of scope.
- `server.py` is wired only against `ReadOperationsConnector`;
  `write_server.py` is wired only against `WriteOperationsConnector`. There
  is no type or runtime path from one to the other.
- A connector may execute an already-authorized operation
  (`restart_instance`); it has no method to evaluate policy or approval,
  and none is added by this design. Policy and approval remain entirely
  inside the control plane (ADR 0003, trust boundary 3/4).

## Mapping: existing Mock implementation

`connectors/mock_connector.py` hosts `MockReadConnector` /
`MockWriteConnector`, containing exactly the same deterministic
`checkout-api` / deployment `1.8.4` dataset and validation rules that
previously lived directly in `server.py` / `write_server.py`. `server.py`
and `write_server.py` now do nothing but declare the MCP tool schema and
delegate to a connector selected by `connectors/config.py` (defaulting to
mock). Existing tests in `tests/ops-mcp/test_ops_mcp.py` and
`test_write_mcp.py` pass unchanged, proving behavioral compatibility.

## Mapping: hypothetical Kubernetes implementation

`connectors/kubernetes_example.py` provides `KubernetesReadConnector` /
`KubernetesWriteConnector`, illustrating the shape of a real
implementation without depending on a real cluster or the Kubernetes SDK:

- `service` maps to a Kubernetes namespace/deployment name.
- `instance` maps to a pod name.
- `get_service_health` maps pod phase (`Running`, `CrashLoopBackOff`, …) to
  `InstanceHealth`.
- `get_deployment` maps a deployment's image tag to `version`.
- `restart_instance` maps to deleting exactly one named pod (the
  Deployment/ReplicaSet controller recreates it), never a broader
  rollout/scale operation.
- `get_logs` / `get_known_incidents` raise `UnsupportedCapabilityError`,
  since this illustrative client has no log backend or ITSM integration —
  a production implementation would delegate those to a logs/ITSM
  connector instead of fabricating data.

Both classes depend only on a small `KubernetesClient` protocol
(`list_pods`, `get_deployment_image_tag`, `delete_pod`), which a production
implementation would satisfy with a thin wrapper around
`kubernetes.client`. This module is **not** wired into `server.py` /
`write_server.py` and is exercised in tests only via a fake client
(`tests/ops-mcp/test_kubernetes_example_connector.py`), per the issue's
explicit non-goal of shipping a production Kubernetes integration.

## Testing strategy

- Connector implementations are tested directly against the `Protocol`
  contracts, independent of MCP (`test_connectors_contracts.py`,
  `test_kubernetes_example_connector.py`), so vendor-specific tests never
  need a running MCP server or real vendor account.
- A connector under test is always a fake/deterministic implementation of
  its dependency protocol (e.g. `FakeKubernetesClient`), consistent with
  the repository's "deterministic fake models/collaborators in unit tests"
  convention.
- Existing MCP-level tests continue to prove tool discovery, read/write
  tool-set separation, and end-to-end request/response behavior through
  FastMCP.

## Rejected alternatives

- **Generic dynamic plugin/tool-loading framework.** Rejected: explicit
  non-goal; would let a connector introduce arbitrary tools reachable by
  the AI runtime, weakening least privilege for no V1 benefit.
- **One combined `OperationsConnector` protocol with all five methods.**
  Rejected: would let a single object structurally satisfy both read and
  write, reintroducing the exact risk ADR 0004 was written to prevent.
- **Connectors as separate out-of-process services reachable only via a
  second MCP hop.** Rejected for V1: adds a process and network hop with
  no immediate benefit, since MCP already provides the required
  read/write process boundary; revisit only if a specific connector needs
  independent scaling or isolation.
- **Letting connectors return `None`/empty results for unsupported
  capabilities.** Rejected: indistinguishable from "genuinely no data
  found"; would let a caller silently misinterpret missing support as a
  clean negative result. An explicit `UnsupportedCapabilityError` is
  required instead.
- **A full production Kubernetes connector in this issue.** Rejected:
  explicitly out of scope; the illustrative example proves the abstraction
  fits without adding a real cluster dependency, credential handling, or
  vendor SDK to the repository.

## Consequences

- Vendor-specific knowledge is isolated to individual connector modules;
  `server.py` / `write_server.py` and the contracts themselves stay
  vendor-neutral.
- Adding a real vendor later means adding one new connector module plus a
  registration entry in `connectors/config.py`; the MCP tool layer and its
  tests do not change.
- Read/write separation is now enforced at two independent layers
  (protocol typing here, MCP process/deployment separation per ADR 0004),
  making an accidental privilege leak harder to introduce.
- Connector-level errors are explicit and typed, improving testability and
  future policy decisions (e.g. retry-on-transient) without changing the
  contract again.
