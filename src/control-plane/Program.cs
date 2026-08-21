using ControlPlane.Contracts;
using ControlPlane.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient<IAiRuntimeClient, AiRuntimeClient>(client =>
{
    var runtimeUrl = builder.Configuration["AiRuntime:Url"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(runtimeUrl);
});
builder.Services.AddHttpClient<IPrivilegedActionExecutor, McpPrivilegedActionExecutor>(client =>
{
    var writeUrl = builder.Configuration["WriteMcp:Url"] ?? "http://localhost:8002";
    client.BaseAddress = new Uri(writeUrl);
});
builder.Services.AddSingleton<IActionPolicy, DeterministicActionPolicy>();
builder.Services.AddSingleton<IActionStateStore, InMemoryActionStateStore>();
builder.Services.AddSingleton<IAuditStore, InMemoryAuditStore>();
builder.Services.AddSingleton<ControlPlaneEvidenceBinder>();
builder.Services.AddSingleton<ActionLifecycle>();

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.MapPost("/investigations", async (
    InvestigationRequest? request,
    IAiRuntimeClient aiRuntimeClient,
    ActionLifecycle actionLifecycle,
    CancellationToken cancellationToken) =>
{
    if (request is null || !IsValid(request))
    {
        return Results.BadRequest(new { error = "InvestigationId, Question, and Service are required." });
    }

    if (!SupportedServices.IsSupported(request.Service))
    {
        return Results.UnprocessableEntity(new { error = "Unsupported service." });
    }

    try
    {
        var runtimeResult = await aiRuntimeClient.InvestigateAsync(request, cancellationToken);
        var result = actionLifecycle.BindAndEvaluate(request, runtimeResult);
        return Results.Ok(result);
    }
    catch (HttpRequestException)
    {
        return Results.Problem("The AI runtime could not be reached.", statusCode: StatusCodes.Status502BadGateway);
    }
    catch (AiRuntimeHttpException)
    {
        return Results.Problem("The AI runtime rejected the investigation request.", statusCode: StatusCodes.Status502BadGateway);
    }
    catch (AiRuntimeContractException)
    {
        return Results.Problem("The AI runtime returned an invalid investigation result.", statusCode: StatusCodes.Status502BadGateway);
    }
    catch (System.Text.Json.JsonException)
    {
        return Results.Problem("The AI runtime returned an invalid investigation result.", statusCode: StatusCodes.Status502BadGateway);
    }
});

app.MapGet("/actions/{actionId}", (string actionId, IActionStateStore store) =>
{
    return store.TryGet(actionId, out var state)
        ? Results.Ok(ToResponse(state!))
        : Results.NotFound();
});

app.MapGet("/actions/{actionId}/audit", (string actionId, IAuditStore auditStore) =>
{
    var records = auditStore.GetForAction(actionId);
    return records.Count == 0 ? Results.NotFound() : Results.Ok(records);
});

app.MapPost("/actions/{actionId}/approve", (string actionId, IActionStateStore store) =>
    TransitionAction(actionId, ActionApprovalState.Approved, store));

app.MapPost("/actions/{actionId}/reject", (string actionId, IActionStateStore store) =>
    TransitionAction(actionId, ActionApprovalState.Rejected, store));

app.MapPost("/actions/{actionId}/execute", async (
    string actionId,
    IActionStateStore store,
    IPrivilegedActionExecutor executor,
    IAuditStore auditStore,
    CancellationToken cancellationToken) =>
{
    if (!store.TryGet(actionId, out var current) || current is null)
    {
        return Results.NotFound();
    }

    try
    {
        var execution = new ActionExecutionService(store, executor, auditStore);
        var result = await execution.ExecuteAsync(actionId, cancellationToken);
        return Results.Ok(new ActionExecutionResponse(
            actionId,
            result.Status,
            result.OperationType,
            result.Service,
            result.Target,
            result.CompletedAt,
            result.ReasonCode));
    }
    catch (InvalidOperationException exception)
    {
        return Results.Conflict(new { error = exception.Message });
    }
    catch (Exception)
    {
        return Results.Problem("Privileged execution failed.", statusCode: StatusCodes.Status500InternalServerError);
    }
});

app.Run();

static bool IsValid(InvestigationRequest request) =>
    !string.IsNullOrWhiteSpace(request.InvestigationId) &&
    !string.IsNullOrWhiteSpace(request.Question) &&
    !string.IsNullOrWhiteSpace(request.Service);

static IResult TransitionAction(
    string actionId,
    ActionApprovalState nextState,
    IActionStateStore store)
{
    if (!store.TryGet(actionId, out var current))
    {
        return Results.NotFound();
    }

    if (!store.TryTransition(actionId, nextState, out var updated))
    {
        return Results.Conflict(new { error = "Action is not in a transitionable state." });
    }

    return Results.Ok(ToResponse(updated!));
}

static ActionStateResponse ToResponse(ActionState state) => new(
    state.Proposal,
    state.Policy.Decision,
    state.Policy.ReasonCode,
    state.ApprovalState,
    state.ExecutionState);

public sealed record ActionExecutionResponse(
    string ActionId,
    ActionExecutionStatus Status,
    string OperationType,
    string Service,
    string Target,
    DateTimeOffset CompletedAt,
    string ReasonCode);

public partial class Program;
