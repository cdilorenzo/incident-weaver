using System.Net.Http.Json;
using System.Text.Json;
using ControlPlane.Contracts;

namespace ControlPlane.Services;

public interface IAiRuntimeClient
{
    Task<InvestigationResult> InvestigateAsync(
        InvestigationRequest request,
        CancellationToken cancellationToken);
}

public sealed class AiRuntimeClient(HttpClient httpClient) : IAiRuntimeClient
{
    public async Task<InvestigationResult> InvestigateAsync(
        InvestigationRequest request,
        CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "/internal/investigations",
            request,
            cancellationToken);
        response.EnsureSuccessStatusCode();

        var result = await response.Content.ReadFromJsonAsync<InvestigationResult>(
            cancellationToken);
        return result ?? throw new JsonException("AI runtime returned an empty result.");
    }
}
