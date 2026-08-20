from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool
from pydantic_ai.tools import ToolDefinition

import app as app_module
from agent import create_investigation_agent


READ_TOOLS = {
    "get_service_health",
    "get_deployment",
    "get_logs",
    "get_known_incidents",
}


class RecordingReadToolset(AbstractToolset[None]):
    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def id(self) -> str:
        return "recording-ops-read"

    async def get_tools(self, ctx: Any) -> dict[str, ToolsetTool[None]]:
        schemas = {
            "get_service_health": {"type": "object", "properties": {"service": {"type": "string"}}},
            "get_deployment": {"type": "object", "properties": {"service": {"type": "string"}}},
            "get_logs": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "time_range": {
                        "type": "object",
                        "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
                    },
                },
            },
            "get_known_incidents": {"type": "object", "properties": {"service": {"type": "string"}}},
        }
        return {
            name: ToolsetTool(
                self,
                ToolDefinition(name=name, parameters_json_schema=schema),
                max_retries=1,
                args_validator=TypeAdapter(dict[str, Any]).validator,
            )
            for name, schema in schemas.items()
        }

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: Any, tool: ToolsetTool[None]
    ) -> dict[str, Any]:
        self.calls.append(name)
        return {
            "source": name,
            "service": "checkout-api",
            "observed": f"Evidence returned by {name}.",
        }


def test_single_investigation_agent_is_constructed_with_only_read_tools() -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(), toolset)

    assert agent.name == "investigation-agent"
    assert toolset in agent.toolsets


def test_canonical_investigation_uses_all_four_tools_and_maps_request_identity(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(
        TestModel(
            custom_output_args={
                "summary": "The deployment caused a dependency startup failure.",
                "evidence": [
                    {"source": "get_logs", "summary": "PaymentGatewayClient failed on instance-3."},
                    {"source": "get_service_health", "summary": "instance-3 is unhealthy."},
                ],
            }
        ),
        toolset,
    )
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "request-owned-id",
                "question": "Checkout API returns HTTP 500. What happened?",
                "service": "checkout-api",
                "deployment": "1.8.4",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["investigationId"] == "request-owned-id"
    assert body["actionProposal"] is None
    assert body["evidence"][0]["source"] == "get_logs"
    assert set(toolset.calls) == READ_TOOLS
    assert len(toolset.calls) == 4


def test_agent_has_no_write_or_unlisted_tools() -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(), toolset)

    assert READ_TOOLS == {
        "get_service_health",
        "get_deployment",
        "get_logs",
        "get_known_incidents",
    }
    assert not {"restart_service", "rollback", "deploy"}.intersection(READ_TOOLS)


def test_unknown_service_fails_without_invented_diagnosis() -> None:
    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "unknown-service",
                "question": "What happened?",
                "service": "inventory-api",
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unknown service. Supported service: checkout-api."}


def test_model_or_mcp_failure_is_a_safe_service_error(monkeypatch: Any) -> None:
    def fail() -> object:
        raise RuntimeError("provider or MCP failure details must not escape")

    monkeypatch.setattr(app_module, "create_runtime_agent", fail)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "failure-case",
                "question": "What happened?",
                "service": "checkout-api",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Investigation service unavailable."}