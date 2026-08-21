import asyncio
import importlib.util
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "src" / "ops-mcp" / "write_server.py"

spec = importlib.util.spec_from_file_location("ops_mcp_write_server", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server = module.server

EXPECTED_TOOLS = {"restart_instance"}
FORBIDDEN_TOOLS = {"get_service_health", "get_logs", "get_deployment", "get_known_incidents", "restart_service", "deploy"}


def _structured_result(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    result = asyncio.run(server.call_tool(tool_name, arguments))
    assert isinstance(result, tuple)
    assert len(result) == 2
    structured = result[1]
    assert isinstance(structured, dict)
    return structured


def test_write_mcp_exposes_only_restart_instance() -> None:
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert names == EXPECTED_TOOLS
    assert names.isdisjoint(FORBIDDEN_TOOLS)


def test_invalid_service_is_rejected() -> None:
    with pytest.raises(ToolError, match="checkout-api"):
        asyncio.run(server.call_tool("restart_instance", {"action_id": "action-001", "service": "payments-api", "instance": "instance-3"}))


def test_unknown_instance_is_rejected() -> None:
    with pytest.raises(ToolError, match="instance"):
        asyncio.run(server.call_tool("restart_instance", {"action_id": "action-001", "service": "checkout-api", "instance": "instance-99"}))


def test_canonical_write_request_succeeds() -> None:
    result = _structured_result(
        "restart_instance",
        {"action_id": "action-001", "service": "checkout-api", "instance": "instance-3"},
    )

    assert result["action_id"] == "action-001"
    assert result["service"] == "checkout-api"
    assert result["instance"] == "instance-3"
    assert result["status"] == "restarted"
