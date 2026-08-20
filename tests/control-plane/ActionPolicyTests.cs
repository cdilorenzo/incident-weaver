using ControlPlane.Contracts;
using ControlPlane.Services;
using Xunit;

namespace ControlPlane.Tests;

public sealed class ActionPolicyTests
{
    private static readonly InvestigationRequest Request = new(
        "request-owned-investigation",
        "What happened?",
        "checkout-api",
        "1.8.4");

    [Fact]
    public void Canonical_proposal_is_allowed_deterministically()
    {
        var evidence = BoundEvidence();
        var proposal = Proposal("restart_instance", "instance-3", evidence);
        var policy = new DeterministicActionPolicy();

        var first = policy.Evaluate(proposal, Request.Service, evidence);
        var second = policy.Evaluate(proposal, Request.Service, evidence);

        Assert.Equal(new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance"), first);
        Assert.Equal(first, second);
    }

    [Theory]
    [InlineData("execute_command", "*")]
    [InlineData("restart_service", "checkout-api")]
    [InlineData("restart_instance", "*")]
    public void Unsafe_or_unsupported_proposal_is_denied(string actionType, string target)
    {
        var evidence = BoundEvidence();
        var result = new DeterministicActionPolicy().Evaluate(
            Proposal(actionType, target, evidence), Request.Service, evidence);

        Assert.Equal(PolicyDecision.Denied, result.Decision);
    }

    [Fact]
    public void Missing_operational_evidence_is_denied()
    {
        var evidence = BoundEvidence().Where(item => item.Kind != OperationalEvidenceKind.Logs).ToArray();
        var result = new DeterministicActionPolicy().Evaluate(
            Proposal("restart_instance", "instance-3", evidence), Request.Service, evidence);

        Assert.Equal("missing_required_operational_evidence", result.ReasonCode);
    }

    [Fact]
    public void Knowledge_evidence_does_not_satisfy_operational_requirements()
    {
        var evidence = BoundEvidence()
            .Select(item => item.Kind == OperationalEvidenceKind.Logs
                ? new BoundEvidenceItem(item.Evidence with { Source = "knowledge" }, null)
                : item)
            .ToArray();

        var result = new DeterministicActionPolicy().Evaluate(
            Proposal("restart_instance", "instance-3", evidence), Request.Service, evidence);

        Assert.Equal("missing_required_operational_evidence", result.ReasonCode);
    }

    [Fact]
    public void Duplicate_operational_kind_is_denied()
    {
        var evidence = BoundEvidence()
            .Append(new BoundEvidenceItem(
                new EvidenceItem("server-logs-duplicate", "get_logs", "duplicate", []),
                OperationalEvidenceKind.Logs))
            .ToArray();

        var result = new DeterministicActionPolicy().Evaluate(
            Proposal("restart_instance", "instance-3", evidence), Request.Service, evidence);

        Assert.Equal("missing_required_operational_evidence", result.ReasonCode);
    }

    [Fact]
    public void State_machine_allows_one_explicit_terminal_transition()
    {
        var evidence = BoundEvidence();
        var proposal = Proposal("restart_instance", "instance-3", evidence);
        var store = new InMemoryActionStateStore();
        store.Add(new ActionState(
            proposal,
            new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance"),
            ActionApprovalState.PendingApproval,
            ActionExecutionState.NotStarted,
            DateTimeOffset.UtcNow));

        Assert.True(store.TryTransition(proposal.ActionId, ActionApprovalState.Approved, out var approved));
        Assert.Equal(ActionApprovalState.Approved, approved!.ApprovalState);
        Assert.False(store.TryTransition(proposal.ActionId, ActionApprovalState.Rejected, out _));
        Assert.Equal("instance-3", approved.Proposal.Target);
    }

    [Fact]
    public void Lifecycle_generates_identity_and_binds_request_and_evidence()
    {
        var runtimeEvidence = RuntimeEvidence();
        var lifecycle = new ActionLifecycle(
            new DeterministicActionPolicy(),
            new InMemoryActionStateStore(),
            new ControlPlaneEvidenceBinder());
        var runtime = new RuntimeInvestigationResult(
            "model-controlled-id",
            "diagnosis",
            runtimeEvidence,
            new ActionProposalDraft("restart_instance", "instance-3", "Dependency failed."));

        var result = lifecycle.BindAndEvaluate(Request, runtime);
        Assert.NotNull(result.ActionProposal);
        var proposal = result.ActionProposal!;

        Assert.NotEqual("model-controlled-id", proposal.ActionId);
        Assert.Equal(Request.InvestigationId, proposal.InvestigationId);
        Assert.Equal(Request.Service, proposal.Service);
        Assert.DoesNotContain("attacker-evidence-1", proposal.EvidenceIds);
        Assert.DoesNotContain("attacker-evidence-2", proposal.EvidenceIds);
        Assert.All(proposal.EvidenceIds, id => Assert.StartsWith("evidence-", id));
        Assert.Equal(4, proposal.EvidenceIds.Count);
    }

    private static ActionProposal Proposal(string actionType, string target, IReadOnlyList<BoundEvidenceItem> evidence) =>
        new("server-action-id", Request.InvestigationId, actionType, Request.Service, target, "Observed failure.",
            evidence.Select(item => item.Evidence.EvidenceId).ToArray());

    private static BoundEvidenceItem[] BoundEvidence() =>
    [
        new(new("server-health", "get_service_health", "health", []), OperationalEvidenceKind.ServiceHealth),
        new(new("server-logs", "get_logs", "logs", []), OperationalEvidenceKind.Logs),
        new(new("server-deployment", "get_deployment", "deployment", []), OperationalEvidenceKind.Deployment),
        new(new("server-incidents", "get_known_incidents", "incidents", []), OperationalEvidenceKind.KnownIncidents)
    ];

    private static RuntimeEvidenceItem[] RuntimeEvidence() =>
    [
        new("attacker-evidence-1", "get_service_health", "health", []),
        new("attacker-evidence-2", "get_logs", "logs", []),
        new("attacker-evidence-3", "get_deployment", "deployment", []),
        new("attacker-evidence-4", "get_known_incidents", "incidents", [])
    ];
}
