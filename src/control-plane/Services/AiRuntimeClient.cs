using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using ControlPlane.Contracts;

namespace ControlPlane.Services;

public interface IAiRuntimeClient
{
    Task<RuntimeInvestigationResult> InvestigateAsync(
        InvestigationRequest request,
        CancellationToken cancellationToken);
}

public sealed record RuntimeEvidenceItem(
    [property: JsonPropertyName("evidenceId")]
    string RuntimeEvidenceId,
    string Source,
    string Summary,
    IReadOnlyList<Citation> Citations);

public sealed record ActionProposalDraft(
    string ActionType,
    string Target,
    string Rationale);

public sealed class AiRuntimeHttpException(HttpStatusCode statusCode)
    : Exception($"AI runtime returned HTTP {(int)statusCode}.")
{
    public HttpStatusCode StatusCode { get; } = statusCode;
}

public sealed class AiRuntimeContractException(string message, Exception? innerException = null)
    : Exception(message, innerException);

public sealed class AiRuntimeClient(HttpClient httpClient) : IAiRuntimeClient
{
    private static readonly JsonSerializerOptions RuntimeJsonOptions = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow
    };

    public async Task<RuntimeInvestigationResult> InvestigateAsync(
        InvestigationRequest request,
        CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "/internal/investigations",
            request,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new AiRuntimeHttpException(response.StatusCode);
        }

        RuntimeInvestigationResult? result;
        try
        {
            result = await response.Content.ReadFromJsonAsync<RuntimeInvestigationResult>(
                RuntimeJsonOptions,
                cancellationToken);
        }
        catch (JsonException exception)
        {
            throw new AiRuntimeContractException(
                "AI runtime returned malformed investigation JSON.",
                exception);
        }

        return ValidateResult(request, result);
    }

    private static RuntimeInvestigationResult ValidateResult(
        InvestigationRequest request,
        RuntimeInvestigationResult? result)
    {
        if (result is null || string.IsNullOrWhiteSpace(result.InvestigationId))
        {
            throw new AiRuntimeContractException(
                "AI runtime returned an investigation result without an ID.");
        }

        if (!string.Equals(result.InvestigationId, request.InvestigationId, StringComparison.Ordinal))
        {
            throw new AiRuntimeContractException(
                "AI runtime returned an investigation result for a different investigation.");
        }

        if (string.IsNullOrWhiteSpace(result.Summary) || result.Evidence is null)
        {
            throw new AiRuntimeContractException(
                "AI runtime returned an incomplete investigation result.");
        }

        foreach (var evidence in result.Evidence)
        {
            if (evidence is null ||
                string.IsNullOrWhiteSpace(evidence.RuntimeEvidenceId) ||
                string.IsNullOrWhiteSpace(evidence.Source) ||
                string.IsNullOrWhiteSpace(evidence.Summary) ||
                evidence.Citations is null)
            {
                throw new AiRuntimeContractException(
                    "AI runtime returned an incomplete evidence item.");
            }

            foreach (var citation in evidence.Citations)
            {
                if (citation is null ||
                    string.IsNullOrWhiteSpace(citation.CitationId) ||
                    string.IsNullOrWhiteSpace(citation.Reference))
                {
                    throw new AiRuntimeContractException(
                        "AI runtime returned an incomplete citation.");
                }
            }
        }

        if (result.ActionProposal is { } proposal &&
            (string.IsNullOrWhiteSpace(proposal.ActionType) ||
             string.IsNullOrWhiteSpace(proposal.Target) ||
             string.IsNullOrWhiteSpace(proposal.Rationale) ||
             proposal.ActionType.Length > 64 ||
             proposal.Target.Length > 128 ||
             proposal.Rationale.Length > 500))
        {
            throw new AiRuntimeContractException(
                "AI runtime returned an incomplete action proposal.");
        }

        return result;
    }
}
