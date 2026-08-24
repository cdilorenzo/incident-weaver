"""Small evaluation harness that runs curated cases through the real AI-runtime
investigation pipeline (agent.py + app.py) against a deterministic/fake model.

This intentionally does not measure live-model reasoning quality. See
evaluations/README.md for what this suite does and does not prove.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

_SRC_AI_RUNTIME = Path(__file__).resolve().parents[1] / "src" / "ai-runtime"
if str(_SRC_AI_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_SRC_AI_RUNTIME))

from fastapi.testclient import TestClient  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool  # noqa: E402
from pydantic_ai.tools import ToolDefinition  # noqa: E402

import app as app_module  # noqa: E402
from agent import REQUIRED_READ_TOOLS, create_investigation_agent  # noqa: E402
from retrieval import RetrievedChunk  # noqa: E402


class _ToolArgsValidator:
    def __init__(self, adapter: TypeAdapter[dict[str, Any]]) -> None:
        self.adapter = adapter

    def validate_python(self, input: Any, **kwargs: Any) -> Any:
        return self.adapter.validate_python(input)

    def validate_json(self, input: str | bytes | bytearray, **kwargs: Any) -> Any:
        return self.adapter.validate_json(input)


_CANONICAL_TOOL_RESULTS: dict[str, dict[str, Any]] = {
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
        "status": "deployed",
    },
    "get_logs": {
        "service": "checkout-api",
        "entries": [
            {
                "event_id": "checkout-api-1",
                "timestamp": "2026-08-18T10:03:15Z",
                "instance": "instance-3",
                "severity": "ERROR",
                "message": "PaymentGatewayClient initialization failed during dependency startup.",
            }
        ],
    },
    "get_known_incidents": {
        "service": "checkout-api",
        "incidents": [
            {
                "incident_id": "INC-142",
                "service": "checkout-api",
                "affected_instances": ["instance-3"],
                "summary": "checkout-api deployment 1.7.9 triggered HTTP 500s from a PaymentGatewayClient issue.",
            }
        ],
    },
}


class ScriptedReadToolset(AbstractToolset[None]):
    """A read MCP toolset whose available tools and results are fixed per case."""

    def __init__(self, enabled_tools: frozenset[str], result_overrides: dict[str, dict[str, Any]]) -> None:
        self.calls: list[str] = []
        self.enabled_tools = enabled_tools
        self.result_overrides = result_overrides

    @property
    def id(self) -> str:
        return "evaluation-ops-read"

    async def get_tools(self, ctx: Any) -> dict[str, ToolsetTool[None]]:
        return {
            name: ToolsetTool(
                self,
                ToolDefinition(name=name, parameters_json_schema={"type": "object", "properties": {}}),
                max_retries=1,
                args_validator=_ToolArgsValidator(TypeAdapter(dict[str, Any])),
            )
            for name in self.enabled_tools
        }

    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx: Any, tool: ToolsetTool[None]) -> dict[str, Any]:
        self.calls.append(name)
        return {**_CANONICAL_TOOL_RESULTS[name], **self.result_overrides.get(name, {})}


class FixedRetriever:
    """A retrieval substitute that returns a fixed, case-scripted set of chunks."""

    def __init__(self, chunks: tuple[RetrievedChunk, ...]) -> None:
        self.chunks = chunks

    async def retrieve(self, question: str, service: str, deployment: str | None) -> list[RetrievedChunk]:
        return list(self.chunks)


@dataclass(frozen=True)
class CaseOutcome:
    status_code: int
    result: Any
    tool_calls: tuple[str, ...]


@dataclass(frozen=True)
class Expectation:
    name: str
    check: Callable[[CaseOutcome], bool]


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    description: str
    question: str
    enabled_tools: frozenset[str]
    expectations: tuple[Expectation, ...]
    service: str = "checkout-api"
    deployment: str | None = "1.8.4"
    tool_result_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_chunks: tuple[RetrievedChunk, ...] = ()
    scripted_output: dict[str, Any] = field(default_factory=lambda: {"summary": "diagnosis"})


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    passed: bool
    failed_expectations: tuple[str, ...]


def run_case(case: EvaluationCase) -> EvaluationResult:
    toolset = ScriptedReadToolset(case.enabled_tools, case.tool_result_overrides)
    agent = create_investigation_agent(
        TestModel(custom_output_args=case.scripted_output),
        toolset,
        FixedRetriever(case.knowledge_chunks),  # type: ignore[arg-type]
    )

    original_factory = app_module.create_runtime_agent
    app_module.create_runtime_agent = lambda: agent  # type: ignore[assignment]
    try:
        with TestClient(app_module.app) as client:
            response = client.post(
                "/internal/investigations",
                json={
                    "investigationId": case.case_id,
                    "question": case.question,
                    "service": case.service,
                    "deployment": case.deployment,
                },
            )
    finally:
        app_module.create_runtime_agent = original_factory

    result = (
        app_module.InvestigationResult.model_validate(response.json())
        if response.status_code == 200
        else None
    )
    outcome = CaseOutcome(response.status_code, result, tuple(toolset.calls))

    failed = tuple(expectation.name for expectation in case.expectations if not expectation.check(outcome))
    return EvaluationResult(case.case_id, passed=not failed, failed_expectations=failed)


def run_all(cases: Sequence[EvaluationCase]) -> list[EvaluationResult]:
    return [run_case(case) for case in cases]


def format_report(results: Sequence[EvaluationResult]) -> str:
    lines: list[str] = []
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.case_id}")
        for name in result.failed_expectations:
            lines.append(f"    failed expectation: {name}")
    return "\n".join(lines)


def main() -> int:
    from cases import EVALUATION_CASES

    results = run_all(EVALUATION_CASES)
    print(format_report(results))
    failures = sum(1 for result in results if not result.passed)
    print(f"\n{len(results)} case(s), {failures} failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
