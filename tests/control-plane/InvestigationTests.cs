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
        Assert.StartsWith("evidence-", actualEvidence.EvidenceId);
        Assert.NotEqual(expectedEvidence.EvidenceId, actualEvidence.EvidenceId);
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

    [Fact]
    public async Task Unsupported_service_is_rejected_without_calling_runtime()
    {
        var runtime = new RecordingAiRuntimeClient();
        using var client = CreateClient(runtime);

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("unsupported-service", "What happened?", "payments-api", null));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
        Assert.False(runtime.Called);
    }

    [Fact]
    public async Task Allowed_proposal_can_be_inspected_approved_and_not_rejected_again()
    {
        using var client = CreateClient(ProposalResult("restart_instance", "instance-3"));
        var actionId = await CreateAction(client);

        using var inspection = await client.GetAsync($"/actions/{actionId}");
        Assert.Equal(HttpStatusCode.OK, inspection.StatusCode);
        var inspectionState = await inspection.Content.ReadFromJsonAsync<ActionStateResponse>();
        Assert.Equal(ActionApprovalState.PendingApproval, inspectionState!.ApprovalState);

        using var approval = await client.PostAsync($"/actions/{actionId}/approve", null);
        Assert.Equal(HttpStatusCode.OK, approval.StatusCode);
        var approvedState = await approval.Content.ReadFromJsonAsync<ActionStateResponse>();
        Assert.Equal(ActionApprovalState.Approved, approvedState!.ApprovalState);

        using var rejected = await client.PostAsync($"/actions/{actionId}/reject", null);
        Assert.Equal(HttpStatusCode.Conflict, rejected.StatusCode);
    }

    [Fact]
    public async Task Allowed_proposal_can_be_rejected_and_not_approved_again()
    {
        using var client = CreateClient(ProposalResult("restart_instance", "instance-3"));
        var actionId = await CreateAction(client);

        using var rejection = await client.PostAsync($"/actions/{actionId}/reject", null);
        Assert.Equal(HttpStatusCode.OK, rejection.StatusCode);
        var rejectedState = await rejection.Content.ReadFromJsonAsync<ActionStateResponse>();
        Assert.Equal(ActionApprovalState.Rejected, rejectedState!.ApprovalState);

        using var approval = await client.PostAsync($"/actions/{actionId}/approve", null);
        Assert.Equal(HttpStatusCode.Conflict, approval.StatusCode);
    }

    [Fact]
    public async Task Unsupported_action_is_policy_denied_and_not_transitionable()
    {
        using var client = CreateClient(ProposalResult("execute_command", "*"));
        var actionId = await CreateAction(client);

        using var inspection = await client.GetAsync($"/actions/{actionId}");
        var deniedState = await inspection.Content.ReadFromJsonAsync<ActionStateResponse>();
        Assert.Equal(ActionApprovalState.PolicyDenied, deniedState!.ApprovalState);
        Assert.Equal(HttpStatusCode.Conflict,
            (await client.PostAsync($"/actions/{actionId}/approve", null)).StatusCode);
        Assert.Equal(HttpStatusCode.Conflict,
            (await client.PostAsync($"/actions/{actionId}/reject", null)).StatusCode);
    }

    [Fact]
    public async Task Unknown_action_endpoints_return_not_found()
    {
        using var client = CreateClient(new InvestigationResult("unused", "unused", [], null));
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync("/actions/unknown")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.PostAsync("/actions/unknown/approve", null)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.PostAsync("/actions/unknown/reject", null)).StatusCode);
    }

    [Fact]
    public async Task Investigation_returns_bad_gateway_when_runtime_rejects_request()
    {
        using var client = CreateClient(new AiRuntimeHttpException(HttpStatusCode.UnprocessableEntity));

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("inv-002-001", "What happened?", "checkout-api", null));

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Contains("rejected", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task Investigation_returns_bad_gateway_when_runtime_result_is_invalid()
    {
        using var client = CreateClient(new AiRuntimeContractException("invalid result"));

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("inv-002-001", "What happened?", "checkout-api", null));

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Contains("invalid investigation result", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task Investigation_returns_bad_gateway_when_runtime_is_unreachable()
    {
        using var client = CreateClient(new HttpRequestException("connection failed"));

        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("inv-002-001", "What happened?", "checkout-api", null));

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Contains("could not be reached", await response.Content.ReadAsStringAsync());
    }

    private HttpClient CreateClient(Exception exception)
    {
        return factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddSingleton<IAiRuntimeClient>(new ThrowingAiRuntimeClient(exception));
            });
        }).CreateClient();
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

    private HttpClient CreateClient(RecordingAiRuntimeClient runtime)
    {
        return factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services => services.AddSingleton<IAiRuntimeClient>(runtime));
        }).CreateClient();
    }

    private static async Task<string> CreateAction(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync(
            "/investigations",
            new InvestigationRequest("action-investigation", "What happened?", "checkout-api", "1.8.4"));
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var result = await response.Content.ReadFromJsonAsync<InvestigationResult>();
        return result!.ActionProposal!.ActionId;
    }

    private static InvestigationResult ProposalResult(string actionType, string target) => new(
        "action-investigation",
        "diagnosis",
        [
            new EvidenceItem("runtime-health", "get_service_health", "health", []),
            new EvidenceItem("runtime-logs", "get_logs", "logs", []),
            new EvidenceItem("runtime-deployment", "get_deployment", "deployment", []),
            new EvidenceItem("runtime-incidents", "get_known_incidents", "incidents", [])
        ],
        new ActionProposal("runtime-action-id", "runtime-investigation-id", actionType, "runtime-service", target, "Observed failure.", []));

    private sealed class FakeAiRuntimeClient(InvestigationResult result) : IAiRuntimeClient
    {
        public Task<RuntimeInvestigationResult> InvestigateAsync(
            InvestigationRequest request,
            CancellationToken cancellationToken) => Task.FromResult(new RuntimeInvestigationResult(
                result.InvestigationId,
                result.Summary,
                result.Evidence.Select(item => new RuntimeEvidenceItem(
                    item.EvidenceId,
                    item.Source,
                    item.Summary,
                    item.Citations)).ToArray(),
                result.ActionProposal is null
                    ? null
                    : new ActionProposalDraft(
                        result.ActionProposal.ActionType,
                        result.ActionProposal.Target,
                        result.ActionProposal.Rationale)));
    }

    private sealed class ThrowingAiRuntimeClient(Exception exception) : IAiRuntimeClient
    {
        public Task<RuntimeInvestigationResult> InvestigateAsync(
            InvestigationRequest request,
            CancellationToken cancellationToken) => Task.FromException<RuntimeInvestigationResult>(exception);
    }

    private sealed class RecordingAiRuntimeClient : IAiRuntimeClient
    {
        public bool Called { get; private set; }

        public Task<RuntimeInvestigationResult> InvestigateAsync(
            InvestigationRequest request,
            CancellationToken cancellationToken)
        {
            Called = true;
            return Task.FromResult(new RuntimeInvestigationResult(request.InvestigationId, "unused", [], null));
        }
    }
}
