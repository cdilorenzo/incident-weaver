using ControlPlane.Contracts;

namespace ControlPlane.Services;

public enum OperationalEvidenceKind
{
    ServiceHealth,
    Logs,
    Deployment,
    KnownIncidents
}

public sealed record BoundEvidenceItem(
    EvidenceItem Evidence,
    OperationalEvidenceKind? Kind);

public sealed class ControlPlaneEvidenceBinder
{
    public IReadOnlyList<BoundEvidenceItem> Bind(IReadOnlyList<RuntimeEvidenceItem> runtimeEvidence) =>
        runtimeEvidence
            .Select(item => new BoundEvidenceItem(
                new EvidenceItem(
                    $"evidence-{Guid.NewGuid():N}",
                    item.Source,
                    item.Summary,
                    item.Citations),
                Classify(item.Source)))
            .ToArray();

    private static OperationalEvidenceKind? Classify(string source) => source switch
    {
        "get_service_health" => OperationalEvidenceKind.ServiceHealth,
        "get_logs" => OperationalEvidenceKind.Logs,
        "get_deployment" => OperationalEvidenceKind.Deployment,
        "get_known_incidents" => OperationalEvidenceKind.KnownIncidents,
        _ => null
    };
}
