namespace ControlPlane.Contracts;

public sealed record InvestigationRequest(
    string InvestigationId,
    string Question,
    string Service,
    string? Deployment);

public sealed record InvestigationResult(
    string InvestigationId,
    string Summary,
    IReadOnlyList<EvidenceItem> Evidence,
    ActionProposal? ActionProposal);

public sealed record ActionProposalDraft(
    string ActionType,
    string Target,
    string Rationale);

public sealed record EvidenceItem(
    string EvidenceId,
    string Source,
    string Summary,
    IReadOnlyList<Citation> Citations);

public sealed record Citation(
    string CitationId,
    string Reference);

public sealed record ActionProposal(
    string ActionId,
    string InvestigationId,
    string ActionType,
    string Service,
    string Target,
    string Rationale,
    IReadOnlyList<string> EvidenceIds);
