using System.Collections.Concurrent;
using ControlPlane.Contracts;

namespace ControlPlane.Services;

public enum ActionApprovalState
{
    PolicyDenied,
    PendingApproval,
    Approved,
    Rejected,
    Expired
}

public sealed record ActionState(
    ActionProposal Proposal,
    PolicyResult Policy,
    ActionApprovalState ApprovalState,
    ActionExecutionState ExecutionState,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ApprovedAt = null,
    string? ExecutionFailureReasonCode = null);

public sealed record ActionStateResponse(
    ActionProposal Proposal,
    PolicyDecision PolicyDecision,
    string PolicyReasonCode,
    ActionApprovalState ApprovalState,
    ActionExecutionState ExecutionState);

public interface IActionStateStore
{
    ActionState Add(ActionState state);
    bool TryGet(string actionId, out ActionState? state);
    bool TryTransition(string actionId, ActionApprovalState nextState, out ActionState? state);
    bool TryBeginExecution(string actionId, out ActionState? state);
    bool TrySetExpired(string actionId, out ActionState? state);
    bool TryUpdateExecution(string actionId, ActionExecutionState nextState, string reasonCode, out ActionState? state);
}

public sealed class InMemoryActionStateStore(TimeProvider? timeProvider = null) : IActionStateStore
{
    private readonly ConcurrentDictionary<string, ActionState> states = new(StringComparer.Ordinal);
    private readonly TimeProvider clock = timeProvider ?? TimeProvider.System;

    public ActionState Add(ActionState state)
    {
        if (!states.TryAdd(state.Proposal.ActionId, state))
        {
            throw new InvalidOperationException("ActionId already exists.");
        }

        return state;
    }

    public bool TryGet(string actionId, out ActionState? state) => states.TryGetValue(actionId, out state);

    public bool TryTransition(string actionId, ActionApprovalState nextState, out ActionState? state)
    {
        while (states.TryGetValue(actionId, out var current))
        {
            if (!IsValidTransition(current.ApprovalState, nextState))
            {
                state = current;
                return false;
            }

            var updated = current with
            {
                ApprovalState = nextState,
                ApprovedAt = nextState == ActionApprovalState.Approved ? clock.GetUtcNow() : current.ApprovedAt
            };
            if (states.TryUpdate(actionId, updated, current))
            {
                state = updated;
                return true;
            }
        }

        state = null;
        return false;
    }

    public bool TryBeginExecution(string actionId, out ActionState? state)
    {
        while (states.TryGetValue(actionId, out var current))
        {
            if (current.ApprovalState != ActionApprovalState.Approved ||
                current.ExecutionState != ActionExecutionState.NotStarted)
            {
                state = current;
                return false;
            }

            var updated = current with
            {
                ExecutionState = ActionExecutionState.Executing,
                ApprovedAt = current.ApprovedAt ?? clock.GetUtcNow()
            };
            if (states.TryUpdate(actionId, updated, current))
            {
                state = updated;
                return true;
            }
        }

        state = null;
        return false;
    }

    public bool TrySetExpired(string actionId, out ActionState? state)
    {
        while (states.TryGetValue(actionId, out var current))
        {
            if (current.ApprovalState != ActionApprovalState.Approved || current.ExecutionState != ActionExecutionState.NotStarted)
            {
                state = current;
                return false;
            }

            var updated = current with
            {
                ApprovalState = ActionApprovalState.Expired,
                ExecutionState = ActionExecutionState.Expired,
                ExecutionFailureReasonCode = "execution_stale"
            };
            if (states.TryUpdate(actionId, updated, current))
            {
                state = updated;
                return true;
            }
        }

        state = null;
        return false;
    }

    public bool TryUpdateExecution(string actionId, ActionExecutionState nextState, string reasonCode, out ActionState? state)
    {
        while (states.TryGetValue(actionId, out var current))
        {
            if (current.ExecutionState == ActionExecutionState.Executed ||
                current.ExecutionState == ActionExecutionState.ExecutionFailed ||
                current.ExecutionState == ActionExecutionState.Expired)
            {
                state = current;
                return false;
            }

            var updated = current with
            {
                ExecutionState = nextState,
                ExecutionFailureReasonCode = reasonCode
            };
            if (states.TryUpdate(actionId, updated, current))
            {
                state = updated;
                return true;
            }
        }

        state = null;
        return false;
    }

    private static bool IsValidTransition(ActionApprovalState current, ActionApprovalState next) =>
        current == ActionApprovalState.PendingApproval &&
        next is ActionApprovalState.Approved or ActionApprovalState.Rejected;
}
