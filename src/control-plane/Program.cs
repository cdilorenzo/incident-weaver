using ControlPlane.Contracts;
using ControlPlane.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient<IAiRuntimeClient, AiRuntimeClient>(client =>
{
    var runtimeUrl = builder.Configuration["AiRuntime:Url"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(runtimeUrl);
});
builder.Services.AddSingleton<IActionPolicy, DeterministicActionPolicy>();
builder.Services.AddSingleton<IActionStateStore, InMemoryActionStateStore>();
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

app.MapPost("/actions/{actionId}/approve", (string actionId, IActionStateStore store) =>
    TransitionAction(actionId, ActionApprovalState.Approved, store));

app.MapPost("/actions/{actionId}/reject", (string actionId, IActionStateStore store) =>
    TransitionAction(actionId, ActionApprovalState.Rejected, store));

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
    state.ApprovalState);

public partial class Program;
