using ControlPlane.Contracts;
using ControlPlane.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient<IAiRuntimeClient, AiRuntimeClient>(client =>
{
    var runtimeUrl = builder.Configuration["AiRuntime:Url"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(runtimeUrl);
});

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.MapPost("/investigations", async (
    InvestigationRequest? request,
    IAiRuntimeClient aiRuntimeClient,
    CancellationToken cancellationToken) =>
{
    if (request is null || !IsValid(request))
    {
        return Results.BadRequest(new { error = "InvestigationId, Question, and Service are required." });
    }

    try
    {
        var result = await aiRuntimeClient.InvestigateAsync(request, cancellationToken);
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

app.Run();

static bool IsValid(InvestigationRequest request) =>
    !string.IsNullOrWhiteSpace(request.InvestigationId) &&
    !string.IsNullOrWhiteSpace(request.Question) &&
    !string.IsNullOrWhiteSpace(request.Service);

public partial class Program;
