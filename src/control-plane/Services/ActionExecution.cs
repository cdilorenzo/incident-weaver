using System.Collections.Concurrent;
using System.Net.Http.Json;
using System.Text.Json;
using ControlPlane.Contracts;

namespace ControlPlane.Services;

public enum ActionExecutionState
{
    NotStarted,
    Executing,
    Executed,
    ExecutionFailed,
    Expired
}

public enum ActionExecutionStatus
{
    Executed,
    ExecutionFailed,
    Expired
}

public enum AuditEventType
{
    ExecutionRequested,
    ExecutionStarted,
    ExecutionSucceeded,
    ExecutionFailed,
    Expired
}

public sealed record ExecutionResult(
    string ActionId,
    ActionExecutionStatus Status,
    string OperationType,
    string Service,
    string Target,
    DateTimeOffset CompletedAt,
    string ReasonCode);

public sealed record AuditRecord(
    string AuditId,
    string ActionId,
    string InvestigationId,
    AuditEventType EventType,
    string ActionType,
    string Service,
    string Target,
    DateTimeOffset Timestamp,
    string StatusCode,
    string ReasonCode);

public interface IAuditStore
{
    void Add(AuditRecord record);
    IReadOnlyList<AuditRecord> GetForAction(string actionId);
}

public sealed class InMemoryAuditStore : IAuditStore
{
    private readonly ConcurrentDictionary<string, List<AuditRecord>> recordsByAction = new(StringComparer.Ordinal);

    public IReadOnlyList<AuditRecord> Records => recordsByAction
        .Values
        .SelectMany(list => list)
        .OrderBy(record => record.Timestamp)
        .ToArray();

    public void Add(AuditRecord record)
    {
        var list = recordsByAction.GetOrAdd(record.ActionId, _ => []);
        lock (list)
        {
            list.Add(record);
        }
    }

    public IReadOnlyList<AuditRecord> GetForAction(string actionId)
    {
        if (!recordsByAction.TryGetValue(actionId, out var records))
        {
            return Array.Empty<AuditRecord>();
        }

        lock (records)
        {
            return records
                .OrderBy(item => item.Timestamp)
                .ToArray();
        }
    }
}

public interface IPrivilegedActionExecutor
{
    Task<ExecutionResult> ExecuteAsync(ActionProposal proposal, CancellationToken cancellationToken);
}

public sealed class McpPrivilegedActionExecutor(HttpClient httpClient) : IPrivilegedActionExecutor
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<ExecutionResult> ExecuteAsync(ActionProposal proposal, CancellationToken cancellationToken)
    {
        using var discovery = await httpClient.PostAsJsonAsync(
            "/mcp",
            new { jsonrpc = "2.0", id = 1, method = "tools/list", @params = new { } },
            cancellationToken);

        if (!discovery.IsSuccessStatusCode)
        {
            throw new InvalidOperationException("Write MCP discovery failed.");
        }

        var discoveryJson = await discovery.Content.ReadFromJsonAsync<JsonElement>(JsonOptions, cancellationToken);
        var toolNames = discoveryJson.TryGetProperty("result", out var result)
            ? result.TryGetProperty("tools", out var tools)
                ? tools.EnumerateArray().Select(tool => tool.GetProperty("name").GetString()).ToArray()
                : []
            : [];

        if (toolNames is not ["restart_instance"]) // exact one tool only
        {
            throw new InvalidOperationException("Write MCP tool surface is invalid.");
        }

        using var call = await httpClient.PostAsJsonAsync(
            "/mcp",
            new
            {
                jsonrpc = "2.0",
                id = 2,
                method = "tools/call",
                @params = new
                {
                    name = "restart_instance",
                    arguments = new
                    {
                        action_id = proposal.ActionId,
                        service = proposal.Service,
                        instance = proposal.Target
                    }
                }
            },
            cancellationToken);

        if (!call.IsSuccessStatusCode)
        {
            throw new InvalidOperationException("Write MCP execution failed.");
        }

        var body = await call.Content.ReadFromJsonAsync<JsonElement>(JsonOptions, cancellationToken);
        var payload = body.TryGetProperty("result", out var resultNode)
            ? resultNode
            : body;

        var actionId = payload.TryGetProperty("action_id", out var actionIdNode)
            ? actionIdNode.GetString() ?? proposal.ActionId
            : proposal.ActionId;
        var service = payload.TryGetProperty("service", out var serviceNode)
            ? serviceNode.GetString() ?? proposal.Service
            : proposal.Service;
        var target = payload.TryGetProperty("instance", out var instanceNode)
            ? instanceNode.GetString() ?? proposal.Target
            : proposal.Target;
        var statusText = payload.TryGetProperty("status", out var statusNode)
            ? statusNode.GetString() ?? "restarted"
            : "restarted";
        var reason = payload.TryGetProperty("result", out var resultCodeNode)
            ? resultCodeNode.GetString() ?? "completed"
            : "completed";

        var status = string.Equals(statusText, "restarted", StringComparison.OrdinalIgnoreCase)
            ? ActionExecutionStatus.Executed
            : ActionExecutionStatus.ExecutionFailed;

        return new ExecutionResult(
            actionId,
            status,
            proposal.ActionType,
            service,
            target,
            DateTimeOffset.UtcNow,
            reason);
    }
}

public sealed class ActionExecutionService(
    IActionStateStore store,
    IPrivilegedActionExecutor executor,
    IAuditStore auditStore,
    TimeProvider? timeProvider = null)
{
    private const string MaxAgeReasonCode = "execution_stale";
    private static readonly TimeSpan MaxExecutionAge = TimeSpan.FromHours(1);
    private readonly TimeProvider timeProvider = timeProvider ?? TimeProvider.System;

    public async Task<ExecutionResult> ExecuteAsync(string actionId, CancellationToken cancellationToken)
    {
        if (!store.TryGet(actionId, out var current) || current is null)
        {
            throw new InvalidOperationException("Action not found.");
        }

        if (current.ApprovalState != ActionApprovalState.Approved)
        {
            throw new InvalidOperationException("Action is not approved for execution.");
        }

        if (current.ExecutionState != ActionExecutionState.NotStarted)
        {
            throw new InvalidOperationException("Action execution is not available in the current state.");
        }

        if (IsExpired(current))
        {
            store.TrySetExpired(actionId, out var expiredState);
            var expired = expiredState ?? current;
            auditStore.Add(new AuditRecord(
                Guid.NewGuid().ToString("N"),
                expired.Proposal.ActionId,
                expired.Proposal.InvestigationId,
                AuditEventType.Expired,
                expired.Proposal.ActionType,
                expired.Proposal.Service,
                expired.Proposal.Target,
                timeProvider.GetUtcNow(),
                expired.ExecutionState.ToString(),
                MaxAgeReasonCode));
            return new ExecutionResult(
                expired.Proposal.ActionId,
                ActionExecutionStatus.Expired,
                expired.Proposal.ActionType,
                expired.Proposal.Service,
                expired.Proposal.Target,
                timeProvider.GetUtcNow(),
                MaxAgeReasonCode);
        }

        if (!store.TryBeginExecution(actionId, out var executing) || executing is null)
        {
            throw new InvalidOperationException("Action execution could not begin atomically.");
        }

        auditStore.Add(new AuditRecord(
            Guid.NewGuid().ToString("N"),
            executing.Proposal.ActionId,
            executing.Proposal.InvestigationId,
            AuditEventType.ExecutionStarted,
            executing.Proposal.ActionType,
            executing.Proposal.Service,
            executing.Proposal.Target,
            timeProvider.GetUtcNow(),
            executing.ExecutionState.ToString(),
            "execution_started"));

        try
        {
            var result = await executor.ExecuteAsync(executing.Proposal, cancellationToken);
            var finalState = result.Status == ActionExecutionStatus.Executed
                ? ActionExecutionState.Executed
                : ActionExecutionState.ExecutionFailed;
            store.TryUpdateExecution(actionId, finalState, result.ReasonCode, out _);
            auditStore.Add(new AuditRecord(
                Guid.NewGuid().ToString("N"),
                executing.Proposal.ActionId,
                executing.Proposal.InvestigationId,
                result.Status == ActionExecutionStatus.Executed
                    ? AuditEventType.ExecutionSucceeded
                    : AuditEventType.ExecutionFailed,
                executing.Proposal.ActionType,
                executing.Proposal.Service,
                executing.Proposal.Target,
                timeProvider.GetUtcNow(),
                finalState.ToString(),
                result.ReasonCode));
            return result;
        }
        catch (Exception exception)
        {
            store.TryUpdateExecution(actionId, ActionExecutionState.ExecutionFailed, "mcp_execution_failed", out _);
            auditStore.Add(new AuditRecord(
                Guid.NewGuid().ToString("N"),
                executing.Proposal.ActionId,
                executing.Proposal.InvestigationId,
                AuditEventType.ExecutionFailed,
                executing.Proposal.ActionType,
                executing.Proposal.Service,
                executing.Proposal.Target,
                timeProvider.GetUtcNow(),
                ActionExecutionState.ExecutionFailed.ToString(),
                "mcp_execution_failed"));
            throw new InvalidOperationException("Privileged execution failed.", exception);
        }
    }

    public bool IsExpired(ActionState state)
    {
        var approvedAt = state.ApprovedAt ?? state.CreatedAt;
        return approvedAt + MaxExecutionAge < timeProvider.GetUtcNow();
    }
}
