using ControlPlane.Contracts;

namespace ControlPlane.Services;

public sealed record RuntimeInvestigationResult(
    string InvestigationId,
    string Summary,
    IReadOnlyList<EvidenceItem> Evidence,
    ActionProposalDraft? ActionProposal);

public sealed class ActionLifecycle(
    IActionPolicy policy,
    IActionStateStore store)
{
    public InvestigationResult BindAndEvaluate(
        InvestigationRequest request,
        RuntimeInvestigationResult runtimeResult)
    {
        var publicResult = new InvestigationResult(
            request.InvestigationId,
            runtimeResult.Summary,
            runtimeResult.Evidence,
            null);

        if (runtimeResult.ActionProposal is not { } draft)
        {
            return publicResult;
        }

        var evidenceIds = runtimeResult.Evidence
            .Where(item => item.Source is
                "get_service_health" or "get_logs" or "get_deployment" or "get_known_incidents")
            .Select(item => item.EvidenceId)
            .Distinct(StringComparer.Ordinal)
            .ToArray();
        var proposal = new ActionProposal(
            Guid.NewGuid().ToString("N"),
            request.InvestigationId,
            draft.ActionType,
            request.Service,
            draft.Target,
            draft.Rationale,
            evidenceIds);
        var policyResult = policy.Evaluate(proposal, request.Service, publicResult.Evidence);
        var state = new ActionState(
            proposal,
            policyResult,
            policyResult.IsAllowed
                ? ActionApprovalState.PendingApproval
                : ActionApprovalState.PolicyDenied);
        store.Add(state);
        return publicResult with { ActionProposal = proposal };
    }
}
