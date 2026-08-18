from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/internal/investigations", response_model=InvestigationResult)
async def investigate(request: InvestigationRequest) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=request.investigation_id,
        summary=f"Deterministic investigation stub for {request.service}.",
        evidence=[
            EvidenceItem(
                evidence_id="evidence-stub-001",
                source="deterministic-stub",
                summary="No AI provider or operational tools are used in this slice.",
                citations=[Citation(citation_id="citation-stub-001", reference="slice-002")],
            )
        ],
        action_proposal=None,
    )