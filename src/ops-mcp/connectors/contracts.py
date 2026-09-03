"""Protocol contracts and error semantics for operational connectors.

A connector is a provider-specific implementation of a fixed capability
surface. Read and write capabilities are separate protocols so that a
component wired with a `ReadOperationsConnector` structurally cannot reach
any state-changing operation, matching ADR 0004 and ADR 0006.

Ownership rules enforced by this module:

- Identifiers (`service`, `instance`) are opaque strings owned by the
  connector; the MCP tool layer never interprets or rewrites them.
- Normalization from vendor-native data into the shared wire models
  (`connectors.models`) is the connector's responsibility, not the MCP
  tool layer's.
- Credentials are constructed and held by the connector implementation
  from its own configuration; they never appear in a request/response
  model and never cross into the AI runtime or control plane.
"""

from typing import Protocol

from .models import Deployment, KnownIncidentResult, LogResult, RestartResult, ServiceHealth, TimeRange


class ConnectorError(Exception):
    """Base type for all connector-raised errors.

    Distinct from Python built-in exceptions so MCP tool code and tests can
    reason about connector failure semantics without depending on a
    specific vendor implementation.
    """


class UnknownServiceError(ConnectorError):
    """The requested service identifier is not known to this connector."""


class UnknownInstanceError(ConnectorError):
    """The requested instance identifier is not known to this connector."""


class InvalidTimeRangeError(ConnectorError):
    """The requested time range is malformed or logically invalid."""


class UnsupportedCapabilityError(ConnectorError):
    """This connector does not implement the requested capability.

    Raised instead of silently returning empty/fabricated data. Not every
    connector must offer meaningful support for every read capability
    (design question 3); when it cannot, it must fail explicitly.
    """


class TransientProviderError(ConnectorError):
    """The underlying provider failed in a way that may succeed on retry.

    Distinguishes retryable infrastructure failures (timeouts,
    connectivity, rate limiting) from permanent validation failures such as
    `UnknownServiceError`. Retry policy itself is out of scope for the
    connector; it only reports the failure category.
    """


class ReadOperationsConnector(Protocol):
    """Read-only operational evidence capability.

    Implementations must never mutate operational state. This is the only
    protocol the AI runtime's read MCP surface may be wired against.
    """

    def get_service_health(self, service: str) -> ServiceHealth:
        """Return instance-level health for `service`."""
        ...

    def get_logs(self, service: str, time_range: TimeRange) -> LogResult:
        """Return log entries for `service` within the bounded `time_range`."""
        ...

    def get_deployment(self, service: str) -> Deployment:
        """Return current deployment metadata for `service`."""
        ...

    def get_known_incidents(self, service: str) -> KnownIncidentResult:
        """Return known historical incidents for `service`."""
        ...


class WriteOperationsConnector(Protocol):
    """Privileged write capability.

    Must remain unreachable from the AI runtime (ADR 0003, ADR 0004). A
    connector may execute an already-authorized operation; it may not
    decide whether the operation is authorized. Policy and human approval
    are evaluated upstream by the control plane before this is ever
    invoked.
    """

    def restart_instance(self, action_id: str, service: str, instance: str) -> RestartResult:
        """Restart exactly one explicitly identified instance of `service`."""
        ...
