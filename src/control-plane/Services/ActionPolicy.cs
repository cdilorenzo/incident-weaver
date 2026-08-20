using ControlPlane.Contracts;

namespace ControlPlane.Services;

public enum PolicyDecision
{
    Allowed,
    Denied
}

public sealed record PolicyResult(PolicyDecision Decision, string ReasonCode)
{
    public bool IsAllowed => Decision == PolicyDecision.Allowed;
}

public interface IActionPolicy
{
    PolicyResult Evaluate(ActionProposal proposal, string validatedService, IReadOnlyList<EvidenceItem> evidence);
}

public sealed class DeterministicActionPolicy : IActionPolicy
{
    private static readonly string[] RequiredSources =
    [
        "get_service_health",
        "get_logs",
        "get_deployment",
        "get_known_incidents"
    ];

    public PolicyResult Evaluate(
        ActionProposal proposal,
        string validatedService,
        IReadOnlyList<EvidenceItem> evidence)
    {
        if (proposal.ActionType != "restart_instance")
        {
            return Denied("unsupported_action_type");
        }

        if (proposal.Service != validatedService)
        {
            return Denied("service_mismatch");
        }

        if (!System.Text.RegularExpressions.Regex.IsMatch(
                proposal.Target,
                "^instance-[A-Za-z0-9]+$",
                System.Text.RegularExpressions.RegexOptions.CultureInvariant))
        {
            return Denied("invalid_instance_target");
        }

        if (string.IsNullOrWhiteSpace(proposal.Rationale) || proposal.Rationale.Length > 500)
        {
            return Denied("invalid_rationale");
        }

        if (evidence.Count != evidence.Select(item => item.EvidenceId).Distinct(StringComparer.Ordinal).Count())
        {
            return Denied("invalid_evidence_binding");
        }

        var evidenceById = evidence.ToDictionary(item => item.EvidenceId);
        if (proposal.EvidenceIds.Count == 0 || proposal.EvidenceIds.Any(id => !evidenceById.ContainsKey(id)))
        {
            return Denied("invalid_evidence_binding");
        }

        var sources = proposal.EvidenceIds
            .Select(id => evidenceById[id].Source)
            .ToHashSet(StringComparer.Ordinal);
        if (!RequiredSources.All(sources.Contains))
        {
            return Denied("missing_required_operational_evidence");
        }

        return new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance");
    }

    private static PolicyResult Denied(string reasonCode) =>
        new(PolicyDecision.Denied, reasonCode);
}
