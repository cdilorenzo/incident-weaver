using ControlPlane.Contracts;

namespace ControlPlane.Services;

public sealed record RuntimeInvestigationResult(
    string InvestigationId,
    string Summary,
    IReadOnlyList<RuntimeEvidenceItem> Evidence,
    ActionProposalDraft? ActionProposal);

public sealed class ActionLifecycle(
    IActionPolicy policy,
    IActionStateStore store,
    ControlPlaneEvidenceBinder evidenceBinder)
{
    public InvestigationResult BindAndEvaluate(
        InvestigationRequest request,
        RuntimeInvestigationResult runtimeResult)
    {
        var boundEvidence = evidenceBinder.Bind(runtimeResult.Evidence);
        var publicResult = new InvestigationResult(
            request.InvestigationId,
            runtimeResult.Summary,
            boundEvidence.Select(item => item.Evidence).ToArray(),
            null);

        if (runtimeResult.ActionProposal is not { } draft)
        {
            return publicResult;
        }

        var evidenceIds = boundEvidence
            .Where(item => item.Kind is not null)
            .Select(item => item.Evidence.EvidenceId)
            .ToArray();
        var proposal = new ActionProposal(
            Guid.NewGuid().ToString("N"),
            request.InvestigationId,
            draft.ActionType,
            request.Service,
            draft.Target,
            draft.Rationale,
            evidenceIds);
        var policyResult = policy.Evaluate(proposal, request.Service, boundEvidence);
        var state = new ActionState(
            proposal,
            policyResult,
            policyResult.IsAllowed
                ? ActionApprovalState.PendingApproval
                : ActionApprovalState.PolicyDenied,
            ActionExecutionState.NotStarted,
            DateTimeOffset.UtcNow);
        store.Add(state);
        return publicResult with { ActionProposal = proposal };
    }
}
