from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool
from pydantic_ai.tools import ToolDefinition

import app as app_module
from agent import REQUIRED_READ_TOOLS, create_investigation_agent


class RecordingReadToolset(AbstractToolset[None]):
    def __init__(
        self,
        enabled_tools: set[str] | None = None,
        result_overrides: dict[str, Any] | None = None,
        extra_tools: set[str] | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.enabled_tools = set(REQUIRED_READ_TOOLS) if enabled_tools is None else enabled_tools
        self.result_overrides = result_overrides or {}
        self.extra_tools = extra_tools or set()

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
        schemas.update({name: {"type": "object", "properties": {}} for name in self.extra_tools})
        return {
            name: ToolsetTool(
                self,
                ToolDefinition(name=name, parameters_json_schema=schema),
                max_retries=1,
                args_validator=TypeAdapter(dict[str, Any]).validator,
            )
            for name, schema in schemas.items()
            if name in self.enabled_tools or name in self.extra_tools
        }

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: Any, tool: ToolsetTool[None]
    ) -> dict[str, Any]:
        self.calls.append(name)
        canonical_results = {
            "get_service_health": {
                "service": "checkout-api",
                "instances": [
                    {"instance": "instance-1", "status": "healthy", "healthy": True},
                    {"instance": "instance-2", "status": "healthy", "healthy": True},
                    {"instance": "instance-3", "status": "unhealthy", "healthy": False},
                ],
            },
            "get_deployment": {
                "service": "checkout-api",
                "version": "1.8.4",
                "deployed_at": "2026-08-18T10:03:00Z",
            },
            "get_logs": {
                "service": "checkout-api",
                "entries": [
                    {"instance": "instance-3", "message": "PaymentGatewayClient initialization failed."},
                    {"instance": "instance-3", "message": "Server startup failed."},
                    {"instance": "instance-3", "message": "HTTP 500 error observed after deployment 1.8.4."},
                ],
            },
            "get_known_incidents": {
                "service": "checkout-api",
                "incidents": [{"incident_id": "INC-142", "summary": "PaymentGatewayClient initialization issue."}],
            },
        }
        return {**canonical_results[name], **self.result_overrides.get(name, {})}


def test_single_investigation_agent_is_constructed_with_only_read_tools() -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(), toolset)

    assert agent.agent.name == "investigation-agent"
    assert agent.toolset.read_mcp is toolset


def test_canonical_investigation_uses_all_four_tools_and_maps_request_identity(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(
        TestModel(
            custom_output_args={"summary": "The deployment caused a dependency startup failure."}
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
    assert body["evidence"][0]["source"] == "get_service_health"
    evidence_text = " ".join(item["summary"] for item in body["evidence"])
    assert "instance-3" in evidence_text
    assert "1.8.4" in evidence_text
    assert "PaymentGatewayClient" in evidence_text
    assert "INC-142" in evidence_text
    assert set(toolset.calls) == set(REQUIRED_READ_TOOLS)
    assert len(toolset.calls) == 4


def test_agent_has_no_write_or_unlisted_tools() -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(), toolset)

    discovered = asyncio.run(agent.toolset.get_tools(None))
    assert set(discovered) == set(REQUIRED_READ_TOOLS)
    assert not {"restart_service", "rollback", "deploy", "execute_command"}.intersection(discovered)


def test_exact_read_tool_surface_is_visible_to_the_agent() -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(TestModel(), toolset)

    discovered = asyncio.run(agent.toolset.get_tools(None))

    assert set(discovered) == set(REQUIRED_READ_TOOLS)


def test_extra_tool_surface_fails_closed_before_agent_use() -> None:
    toolset = RecordingReadToolset(extra_tools={"restart_service"})
    agent = create_investigation_agent(TestModel(), toolset)

    with pytest.raises(RuntimeError, match="unexpected"):
        asyncio.run(agent.toolset.get_tools(None))


def test_missing_tool_surface_fails_closed_before_agent_use() -> None:
    toolset = RecordingReadToolset(enabled_tools=set(REQUIRED_READ_TOOLS) - {"get_logs"})
    agent = create_investigation_agent(TestModel(), toolset)

    with pytest.raises(RuntimeError, match="Missing"):
        asyncio.run(agent.toolset.get_tools(None))


def test_missing_required_tool_fails_instead_of_returning_success(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(enabled_tools=set(REQUIRED_READ_TOOLS) - {"get_logs"})
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "unsupported"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "missing-tool", "question": "What happened?", "service": "checkout-api"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Investigation service unavailable."}


def test_model_cannot_inject_trusted_evidence(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(
        TestModel(custom_output_args={"summary": "diagnosis", "evidence": [{"source": "fake", "summary": "fake"}]}),
        toolset,
    )
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "fake-evidence", "question": "What happened?", "service": "checkout-api"},
        )

    assert response.status_code == 503


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


def test_changed_tool_result_changes_only_corresponding_evidence(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(result_overrides={"get_deployment": {"version": "1.8.5"}})
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "diagnosis"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "changed-result", "question": "What happened?", "service": "checkout-api"},
        )

    assert response.status_code == 200
    deployment_evidence = next(item for item in response.json()["evidence"] if item["source"] == "get_deployment")
    assert "1.8.5" in deployment_evidence["summary"]


def test_unknown_mcp_fields_do_not_cross_evidence_boundary(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(
        result_overrides={
            "get_deployment": {
                "api_key": "secret-value",
                "password": "password-value",
                "internal_debug": "sensitive-debug-value",
            }
        }
    )
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "diagnosis"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "unknown-fields", "question": "What happened?", "service": "checkout-api"},
        )

    evidence_text = " ".join(item["summary"] for item in response.json()["evidence"])
    assert "secret-value" not in evidence_text
    assert "password-value" not in evidence_text
    assert "sensitive-debug-value" not in evidence_text


def test_credential_like_values_are_redacted_in_free_form_evidence(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(
        result_overrides={
            "get_logs": {
                "entries": [
                    {
                        "event_id": "sensitive-log",
                        "timestamp": "2026-08-18T10:05:42Z",
                        "instance": "instance-3",
                        "severity": "ERROR",
                        "message": (
                            "api_key=key-value password:pass-value access_token=token-value "
                            "authorization: Bearer bearer-value secret=secret-value"
                        ),
                        "internal_debug": "do-not-return",
                    }
                ]
            },
            "get_known_incidents": {
                "incidents": [
                    {
                        "incident_id": "INC-143",
                        "summary": "secret=incident-secret; historical failure",
                        "password": "incident-password",
                    }
                ]
            },
        }
    )
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "diagnosis"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "redacted-fields", "question": "What happened?", "service": "checkout-api"},
        )

    evidence_text = " ".join(item["summary"] for item in response.json()["evidence"])
    for sensitive_value in (
        "key-value",
        "pass-value",
        "token-value",
        "bearer-value",
        "secret-value",
        "incident-secret",
        "incident-password",
        "do-not-return",
    ):
        assert sensitive_value not in evidence_text
    assert "PaymentGatewayClient" not in evidence_text
    assert "[REDACTED]" in evidence_text


def test_allowed_operational_field_change_updates_only_its_evidence(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(
        result_overrides={"get_service_health": {"instances": [{"instance": "instance-9", "status": "healthy"}]}}
    )
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "diagnosis"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "allowed-field", "question": "What happened?", "service": "checkout-api"},
        )

    health_evidence = next(item for item in response.json()["evidence"] if item["source"] == "get_service_health")
    assert "instance-9" in health_evidence["summary"]


def test_model_summary_is_sanitized_before_returning_to_control_plane(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset()
    agent = create_investigation_agent(
        TestModel(
            custom_output_args={
                "summary": "api_key=super-secret password=hunter2 access_token=abc123 "
                "Authorization: Bearer bearer123 user-secret-echo"
            }
        ),
        toolset,
    )
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "summary-redaction",
                "question": "Repeat this user-controlled secret: password=hunter2",
                "service": "checkout-api",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["investigationId"] == "summary-redaction"
    assert body["actionProposal"] is None
    for secret in ("super-secret", "hunter2", "abc123", "bearer123"):
        assert secret not in body["summary"]
    assert "[REDACTED]" in body["summary"]


def test_allowlisted_mcp_strings_are_sanitized(monkeypatch: Any) -> None:
    toolset = RecordingReadToolset(
        result_overrides={
            "get_service_health": {
                "service": "api_key=health-secret",
                "instances": [{"instance": "Bearer health-token", "status": "password=health-password"}],
            },
            "get_deployment": {
                "service": "checkout-api",
                "version": "access_token=deployment-token",
                "deployed_at": "2026-08-18T10:03:00Z",
                "status": "authorization: Bearer deployment-bearer",
            },
            "get_logs": {
                "service": "checkout-api",
                "entries": [
                    {
                        "event_id": "secret=event-secret",
                        "timestamp": "2026-08-18T10:05:42Z",
                        "instance": "instance-3",
                        "severity": "api_key=severity-secret",
                        "message": "PaymentGatewayClient initialization failed.",
                    }
                ],
            },
            "get_known_incidents": {
                "service": "checkout-api",
                "incidents": [
                    {
                        "incident_id": "password=incident-password",
                        "service": "checkout-api",
                        "affected_instances": ["access_token=affected-token"],
                        "summary": "Historical incident INC-142.",
                    }
                ],
            },
        }
    )
    agent = create_investigation_agent(TestModel(custom_output_args={"summary": "diagnosis"}), toolset)
    monkeypatch.setattr(app_module, "create_runtime_agent", lambda: agent)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/internal/investigations",
            json={"investigationId": "allowlisted-redaction", "question": "What happened?", "service": "checkout-api"},
        )

    assert response.status_code == 200
    evidence_text = " ".join(item["summary"] for item in response.json()["evidence"])
    for secret in (
        "health-secret",
        "health-token",
        "health-password",
        "deployment-token",
        "deployment-bearer",
        "event-secret",
        "severity-secret",
        "incident-password",
        "affected-token",
    ):
        assert secret not in evidence_text
    assert "PaymentGatewayClient" in evidence_text
    assert "INC-142" in evidence_text
    assert "[REDACTED]" in evidence_text