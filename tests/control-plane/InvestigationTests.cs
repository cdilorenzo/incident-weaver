using System.Net;
using System.Net.Http.Json;
using ControlPlane.Contracts;
using ControlPlane.Services;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ControlPlane.Tests;

public sealed class InvestigationTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> factory;

    public InvestigationTests(WebApplicationFactory<Program> factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task Investigation_forwards_request_and_returns_typed_result()
    {
        var expected = new InvestigationResult(
            "inv-002-001",
            "Deterministic investigation stub for checkout-api.",
            [
                new EvidenceItem(
                    "evidence-stub-001",
                    "deterministic-stub",
                    "No AI provider or operational tools are used in this slice.",
                    [new Citation("citation-stub-001", "slice-002")])
            ],
            null);
        using var client = CreateClient(expected);

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest(
                "inv-002-001",
                "Checkout API returns HTTP 500 since deployment 1.8.4. What happened?",
                "checkout-api",
                "1.8.4"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var actual = await response.Content.ReadFromJsonAsync<InvestigationResult>();

        Assert.NotNull(actual);
        Assert.Equal(expected.InvestigationId, actual.InvestigationId);
        Assert.Equal(expected.Summary, actual.Summary);
        Assert.Equal(expected.ActionProposal, actual.ActionProposal);
        var actualEvidence = Assert.Single(actual.Evidence);
        var expectedEvidence = Assert.Single(expected.Evidence);
        Assert.Equal(expectedEvidence.EvidenceId, actualEvidence.EvidenceId);
        Assert.Equal(expectedEvidence.Source, actualEvidence.Source);
        Assert.Equal(expectedEvidence.Summary, actualEvidence.Summary);
        var actualCitation = Assert.Single(actualEvidence.Citations);
        var expectedCitation = Assert.Single(expectedEvidence.Citations);
        Assert.Equal(expectedCitation.CitationId, actualCitation.CitationId);
        Assert.Equal(expectedCitation.Reference, actualCitation.Reference);
    }

    [Fact]
    public async Task Investigation_rejects_invalid_request()
    {
        using var client = CreateClient(new InvestigationResult("unused", "unused", [], null));

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("", "What happened?", "checkout-api", null));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    private HttpClient CreateClient(InvestigationResult result)
    {
        return factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddSingleton<IAiRuntimeClient>(new FakeAiRuntimeClient(result));
            });
        }).CreateClient();
    }

    private sealed class FakeAiRuntimeClient(InvestigationResult result) : IAiRuntimeClient
    {
        public Task<InvestigationResult> InvestigateAsync(
            InvestigationRequest request,
            CancellationToken cancellationToken) => Task.FromResult(result);
    }
}
