"""Unit tests for the connector/provider contracts (CONN-001).

These exercise connector implementations directly (not through MCP) to
prove contract behavior, error semantics, and structural read/write
separation independent of the MCP transport layer.
"""

import pytest

from connectors.config import select_read_connector, select_write_connector
from connectors.contracts import (
    ReadOperationsConnector,
    UnknownInstanceError,
    UnknownServiceError,
    UnsupportedCapabilityError,
    WriteOperationsConnector,
)
from connectors.mock_connector import MockReadConnector, MockWriteConnector


def test_mock_read_connector_satisfies_read_protocol() -> None:
    connector: ReadOperationsConnector = MockReadConnector()
    assert connector.get_service_health("checkout-api")["service"] == "checkout-api"


def test_mock_write_connector_satisfies_write_protocol() -> None:
    connector: WriteOperationsConnector = MockWriteConnector()
    result = connector.restart_instance("action-001", "checkout-api", "instance-3")
    assert result["status"] == "restarted"


def test_read_and_write_protocols_expose_disjoint_capability_surfaces() -> None:
    read_methods = {name for name in dir(ReadOperationsConnector) if not name.startswith("_")}
    write_methods = {name for name in dir(WriteOperationsConnector) if not name.startswith("_")}

    assert "restart_instance" not in read_methods
    assert not {"get_service_health", "get_logs", "get_deployment", "get_known_incidents"} & write_methods


def test_unknown_service_raises_typed_connector_error() -> None:
    connector = MockReadConnector()
    with pytest.raises(UnknownServiceError, match="Unknown service"):
        connector.get_service_health("inventory-api")


def test_unknown_instance_raises_typed_connector_error() -> None:
    connector = MockWriteConnector()
    with pytest.raises(UnknownInstanceError, match="Unknown instance"):
        connector.restart_instance("action-001", "checkout-api", "instance-99")


def test_select_read_connector_defaults_to_mock() -> None:
    connector = select_read_connector()
    assert isinstance(connector, MockReadConnector)


def test_select_write_connector_defaults_to_mock() -> None:
    connector = select_write_connector()
    assert isinstance(connector, MockWriteConnector)


def test_select_read_connector_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown read connector"):
        select_read_connector("datadog")


def test_select_write_connector_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown write connector"):
        select_write_connector("kubernetes")


def test_unsupported_capability_error_is_a_connector_error_subtype() -> None:
    with pytest.raises(UnsupportedCapabilityError):
        raise UnsupportedCapabilityError("not implemented by this connector")
