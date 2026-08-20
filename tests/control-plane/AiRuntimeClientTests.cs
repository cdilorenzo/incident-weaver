using System.Net;
using System.Net.Http.Json;
using ControlPlane.Contracts;
using ControlPlane.Services;
using Xunit;

namespace ControlPlane.Tests;

public sealed class AiRuntimeClientTests
{
    private static readonly InvestigationRequest Request = new(
        "inv-002-001",
        "What happened?",
        "checkout-api",
        "1.8.4");

    [Fact]
    public async Task Valid_result_is_returned()
    {
        var expected = ValidResult();
        var client = CreateClient(JsonContent.Create(expected));

        var actual = await client.InvestigateAsync(Request, CancellationToken.None);

        Assert.Equal(expected.InvestigationId, actual.InvestigationId);
        Assert.Equal(expected.Summary, actual.Summary);
        Assert.Equal(expected.ActionProposal, actual.ActionProposal);
        var actualEvidence = Assert.Single(actual.Evidence);
        var expectedEvidence = Assert.Single(expected.Evidence);
        Assert.Equal(expectedEvidence.RuntimeEvidenceId, actualEvidence.RuntimeEvidenceId);
        Assert.Equal(expectedEvidence.Source, actualEvidence.Source);
        Assert.Equal(expectedEvidence.Summary, actualEvidence.Summary);
        var actualCitation = Assert.Single(actualEvidence.Citations);
        var expectedCitation = Assert.Single(expectedEvidence.Citations);
        Assert.Equal(expectedCitation.CitationId, actualCitation.CitationId);
        Assert.Equal(expectedCitation.Reference, actualCitation.Reference);
    }

    [Fact]
    public async Task Mismatched_investigation_id_is_rejected()
    {
        var client = CreateClient(JsonContent.Create(ValidResult() with { InvestigationId = "other" }));

        var exception = await Assert.ThrowsAsync<AiRuntimeContractException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));

        Assert.Contains("different investigation", exception.Message);
    }

    [Fact]
    public async Task Incomplete_result_is_rejected()
    {
        var client = CreateClient(JsonContent.Create(new
        {
            investigationId = Request.InvestigationId,
            summary = "summary",
            evidence = new[]
            {
                new
                {
                    evidenceId = "evidence-1",
                    source = "logs",
                    summary = "failure",
                    citations = new[] { new { citationId = "", reference = "log-1" } }
                }
            },
            actionProposal = (object?)null
        }));

        await Assert.ThrowsAsync<AiRuntimeContractException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));
    }

    [Fact]
    public async Task Malformed_json_result_is_rejected()
    {
        var client = CreateClient(new StringContent("{"));

        await Assert.ThrowsAsync<AiRuntimeContractException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));
    }

    [Theory]
    [InlineData(65, 10, 10)]
    [InlineData(10, 129, 10)]
    [InlineData(10, 10, 501)]
    public async Task Oversized_proposal_draft_is_rejected(int actionTypeLength, int targetLength, int rationaleLength)
    {
        var result = ValidResult() with
        {
            ActionProposal = new ActionProposalDraft(
                new string('a', actionTypeLength),
                new string('b', targetLength),
                new string('c', rationaleLength))
        };
        var client = CreateClient(JsonContent.Create(result));

        await Assert.ThrowsAsync<AiRuntimeContractException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));
    }

    [Fact]
    public async Task Non_success_response_is_distinguished_from_transport_failure()
    {
        var client = CreateClient(new StringContent("rejected"), HttpStatusCode.UnprocessableEntity);

        var exception = await Assert.ThrowsAsync<AiRuntimeHttpException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, exception.StatusCode);
    }

    [Fact]
    public async Task Transport_failure_is_propagated()
    {
        using var httpClient = new HttpClient(new ThrowingHandler())
        {
            BaseAddress = new Uri("http://ai-runtime")
        };
        var client = new AiRuntimeClient(httpClient);

        await Assert.ThrowsAsync<HttpRequestException>(
            () => client.InvestigateAsync(Request, CancellationToken.None));
    }

    private static AiRuntimeClient CreateClient(HttpContent content, HttpStatusCode statusCode = HttpStatusCode.OK)
    {
        var handler = new ResponseHandler(new HttpResponseMessage(statusCode) { Content = content });
        return new AiRuntimeClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://ai-runtime")
        });
    }

    private static RuntimeInvestigationResult ValidResult() => new(
        Request.InvestigationId,
        "summary",
        [new RuntimeEvidenceItem(
            "evidence-1",
            "logs",
            "failure",
            [new Citation("citation-1", "log-1")])],
        null);

    private sealed class ResponseHandler(HttpResponseMessage response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) => Task.FromResult(response);
    }

    private sealed class ThrowingHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) =>
            throw new HttpRequestException("connection failed");
    }
}
