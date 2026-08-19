import asyncio
import importlib.util
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "src" / "ops-mcp" / "server.py"

spec = importlib.util.spec_from_file_location("ops_mcp_server", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server = module.server

EXPECTED_TOOLS = {
    "get_service_health",
    "get_logs",
    "get_deployment",
    "get_known_incidents",
}
FORBIDDEN_TOOLS = {
    "restart_service",
    "restart_instance",
    "create_support_ticket",
    "deploy",
    "rollback",
    "execute_command",
    "write_file",
    "arbitrary_http_request",
    "execute_http_request",
}


def _structured_result(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    result = asyncio.run(server.call_tool(tool_name, arguments))
    assert isinstance(result, tuple)
    assert len(result) == 2
    structured = result[1]
    assert isinstance(structured, dict)
    return structured


def test_mcp_tool_discovery_lists_all_four_expected_read_tools() -> None:
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert names == EXPECTED_TOOLS


def test_tool_set_contains_only_read_capabilities_and_no_mutation_tools() -> None:
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert names.issubset(EXPECTED_TOOLS)
    assert names.isdisjoint(FORBIDDEN_TOOLS)
    assert names == EXPECTED_TOOLS


def test_get_service_health_checkout_api_returns_canonical_state() -> None:
    result = _structured_result("get_service_health", {"service": "checkout-api"})

    assert result["service"] == "checkout-api"
    assert result["instances"] == [
        {"instance": "instance-1", "status": "healthy", "healthy": True},
        {"instance": "instance-2", "status": "healthy", "healthy": True},
        {
            "instance": "instance-3",
            "status": "unhealthy",
            "healthy": False,
            "notes": "Dependency initialization failed during startup; startup did not complete successfully.",
        },
    ]


def test_unknown_service_handling_is_explicit() -> None:
    with pytest.raises(ToolError, match="Unknown service"):
        asyncio.run(server.call_tool("get_service_health", {"service": "inventory-api"}))


def test_get_logs_returns_deterministic_canonical_log_data() -> None:
    result = _structured_result(
        "get_logs",
        {
            "service": "checkout-api",
            "time_range": {"start": "2026-08-18T10:00:00Z", "end": "2026-08-18T10:20:00Z"},
        },
    )

    assert result["service"] == "checkout-api"
    assert result["entries"][0]["event_id"] == "checkout-api-1"
    assert result["entries"][0]["instance"] == "instance-3"
    assert "PaymentGatewayClient" in result["entries"][0]["message"]
    assert len(result["entries"]) == 4


def test_invalid_time_ranges_fail_clearly() -> None:
    with pytest.raises(ToolError, match="Invalid time range"):
        asyncio.run(
            server.call_tool(
                "get_logs",
                {
                    "service": "checkout-api",
                    "time_range": {"start": "2026-08-18T10:20:00Z", "end": "2026-08-18T10:00:00Z"},
                },
            )
        )


def test_get_deployment_returns_canonical_version_and_metadata() -> None:
    result = _structured_result("get_deployment", {"service": "checkout-api"})

    assert result["service"] == "checkout-api"
    assert result["version"] == "1.8.4"
    assert result["deployed_at"] == "2026-08-18T10:03:00Z"
    assert result["status"] == "deployed"


def test_get_known_incidents_returns_canonical_historical_incident() -> None:
    result = _structured_result("get_known_incidents", {"service": "checkout-api"})

    assert result["service"] == "checkout-api"
    assert result["incidents"][0]["incident_id"] == "INC-142"
    assert result["incidents"][0]["service"] == "checkout-api"
    assert "PaymentGatewayClient" in result["incidents"][0]["summary"]
    assert "restart" in result["incidents"][0]["remediation"].lower()


def test_repeated_calls_with_same_inputs_return_equivalent_results() -> None:
    first = _structured_result("get_deployment", {"service": "checkout-api"})
    second = _structured_result("get_deployment", {"service": "checkout-api"})

    assert first == second


def test_tool_outputs_are_structured_and_not_llm_generated_text() -> None:
    result = _structured_result(
        "get_logs",
        {"service": "checkout-api", "time_range": {"start": "2026-08-18T10:00:00Z", "end": "2026-08-18T10:20:00Z"}},
    )

    assert isinstance(result, dict)
    assert "entries" in result
    assert all(isinstance(entry, dict) for entry in result["entries"])
    assert all({"timestamp", "service", "instance", "severity", "message"}.issubset(entry) for entry in result["entries"])
