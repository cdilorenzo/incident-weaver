from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent import REQUIRED_READ_TOOLS, create_investigation_agent, evidence_summary
from model_provider import ModelSettings, create_model
from pydantic_ai.mcp import MCPServerStreamableHTTP


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class WireModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class InvestigationRequest(WireModel):
    investigation_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    service: str = Field(min_length=1)
    deployment: str | None = None


class Citation(WireModel):
    citation_id: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class EvidenceItem(WireModel):
    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    citations: list[Citation]


class ActionProposal(WireModel):
    action_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    target: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class InvestigationResult(WireModel):
    investigation_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence: list[EvidenceItem]
    action_proposal: ActionProposal | None = None

app = FastAPI(title="IncidentWeaver AI Runtime")

OPS_MCP_URL = "http://ops-mcp:8001/mcp"


def create_runtime_agent() -> object:
    settings = ModelSettings.from_env()
    read_mcp = MCPServerStreamableHTTP(os.getenv("INCIDENTWEAVER_OPS_MCP_URL", OPS_MCP_URL))
    return create_investigation_agent(create_model(settings), read_mcp)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/internal/investigations", response_model=InvestigationResult)
async def investigate(request: InvestigationRequest) -> InvestigationResult:
    if request.service.strip() != "checkout-api":
        raise HTTPException(status_code=422, detail="Unknown service. Supported service: checkout-api.")

    try:
        investigation = create_runtime_agent()
        async with investigation:
            result = await investigation.run(
                f"Service: {request.service}\n"
                f"Deployment hint: {request.deployment or 'none'}\n"
                f"Question: {request.question}"
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Investigation service unavailable.") from exc

    evidence_calls = [call for call in investigation.trace.calls if call.name in REQUIRED_READ_TOOLS]
    return InvestigationResult(
        investigation_id=request.investigation_id,
        summary=result.output.summary,
        evidence=[
            EvidenceItem(
                evidence_id=f"evidence-{index:03d}",
                source=call.name,
                summary=evidence_summary(call.result),
                citations=[],
            )
            for index, call in enumerate(evidence_calls, start=1)
        ],
        action_proposal=None,
    )