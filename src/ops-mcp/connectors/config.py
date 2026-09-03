"""Connector selection and configuration ownership.

The MCP process — not the AI runtime, not the control plane — owns which
connector implementation is active for a given deployment and how it is
configured/credentialed. Selection is driven by environment variables so
that no vendor credential or configuration value ever needs to pass through
the AI runtime or the control plane.

Only connectors that are safe to run without external accounts are
registered here. The illustrative Kubernetes example (see
`kubernetes_example.py`) is intentionally not registered; it demonstrates
the mapping without being wired into any running service.
"""

import os

from .contracts import ReadOperationsConnector, WriteOperationsConnector
from .mock_connector import MockReadConnector, MockWriteConnector

READ_CONNECTOR_ENV_VAR = "INCIDENTWEAVER_OPS_READ_CONNECTOR"
WRITE_CONNECTOR_ENV_VAR = "INCIDENTWEAVER_OPS_WRITE_CONNECTOR"

_READ_CONNECTORS = {"mock": MockReadConnector}
_WRITE_CONNECTORS = {"mock": MockWriteConnector}


def select_read_connector(name: str | None = None) -> ReadOperationsConnector:
    """Return the configured `ReadOperationsConnector` implementation."""
    key = (name or os.environ.get(READ_CONNECTOR_ENV_VAR, "mock")).strip().lower()
    try:
        factory = _READ_CONNECTORS[key]
    except KeyError:
        raise ValueError(f"Unknown read connector: {key}. Supported connectors: {sorted(_READ_CONNECTORS)}.") from None
    return factory()


def select_write_connector(name: str | None = None) -> WriteOperationsConnector:
    """Return the configured `WriteOperationsConnector` implementation."""
    key = (name or os.environ.get(WRITE_CONNECTOR_ENV_VAR, "mock")).strip().lower()
    try:
        factory = _WRITE_CONNECTORS[key]
    except KeyError:
        raise ValueError(f"Unknown write connector: {key}. Supported connectors: {sorted(_WRITE_CONNECTORS)}.") from None
    return factory()
