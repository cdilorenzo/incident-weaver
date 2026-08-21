using System.Net;
using ControlPlane.Contracts;
using ControlPlane.Services;
using Xunit;

namespace ControlPlane.Tests;

public sealed class PrivilegedExecutionTests
{
    [Fact]
    public void PendingApproval_cannot_begin_execution()
    {
        var store = new InMemoryActionStateStore(TimeProvider.System);
        var proposal = CreateProposal();
        store.Add(new ActionState(
            proposal,
            new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance"),
            ActionApprovalState.PendingApproval,
            ActionExecutionState.NotStarted,
            DateTimeOffset.UtcNow));

        Assert.False(store.TryBeginExecution(proposal.ActionId, out _));
    }

    [Fact]
    public void Approved_action_can_execute_once_and_then_becomes_executing()
    {
        var store = new InMemoryActionStateStore(TimeProvider.System);
        var proposal = CreateProposal();
        store.Add(new ActionState(
            proposal,
            new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance"),
            ActionApprovalState.Approved,
            ActionExecutionState.NotStarted,
            DateTimeOffset.UtcNow));

        Assert.True(store.TryBeginExecution(proposal.ActionId, out var executing));
        Assert.Equal(ActionExecutionState.Executing, executing!.ExecutionState);
        Assert.Equal(ActionApprovalState.Approved, executing.ApprovalState);

        Assert.False(store.TryBeginExecution(proposal.ActionId, out _));
    }

    [Fact]
    public async Task Stale_approved_action_is_expired_without_invoking_executor()
    {
        var fakeClock = new FakeTimeProvider(new DateTimeOffset(2026, 8, 20, 12, 0, 0, TimeSpan.Zero));
        var store = new InMemoryActionStateStore(fakeClock);
        var proposal = CreateProposal();
        store.Add(new ActionState(
            proposal,
            new PolicyResult(PolicyDecision.Allowed, "allowed_restart_instance"),
            ActionApprovalState.Approved,
            ActionExecutionState.NotStarted,
            fakeClock.GetUtcNow().AddHours(-2),
            fakeClock.GetUtcNow().AddHours(-2)));

        var executor = new FakePrivilegedActionExecutor();
        var auditStore = new InMemoryAuditStore();
        var service = new ActionExecutionService(store, executor, auditStore, fakeClock);

        var result = await service.ExecuteAsync(proposal.ActionId, CancellationToken.None);

        Assert.Equal(ActionExecutionStatus.Expired, result.Status);
        Assert.Equal(0, executor.CallCount);
        Assert.Contains(auditStore.Records, record => record.ActionId == proposal.ActionId && record.EventType == AuditEventType.Expired);
    }

    private static ActionProposal CreateProposal() => new(
        "action-001",
        "investigation-001",
        "restart_instance",
        "checkout-api",
        "instance-3",
        "Dependency initialization failed on instance-3.",
        ["evidence-1", "evidence-2", "evidence-3", "evidence-4"]);

    private sealed class FakePrivilegedActionExecutor : IPrivilegedActionExecutor
    {
        public int CallCount { get; private set; }

        public Task<ExecutionResult> ExecuteAsync(ActionProposal proposal, CancellationToken cancellationToken)
        {
            CallCount++;
            return Task.FromResult(new ExecutionResult(
                proposal.ActionId,
                ActionExecutionStatus.Executed,
                proposal.ActionType,
                proposal.Service,
                proposal.Target,
                DateTimeOffset.UtcNow,
                "completed"));
        }
    }

    private sealed class FakeTimeProvider(DateTimeOffset utcNow) : TimeProvider
    {
        private readonly DateTimeOffset _utcNow = utcNow;

        public override DateTimeOffset GetUtcNow() => _utcNow;
    }
}
