using System.Collections.Concurrent;
using ControlPlane.Contracts;

namespace ControlPlane.Services;

public enum ActionApprovalState
{
    PolicyDenied,
    PendingApproval,
    Approved,
    Rejected
}

public sealed record ActionState(
    ActionProposal Proposal,
    PolicyResult Policy,
    ActionApprovalState ApprovalState);

public sealed record ActionStateResponse(
    ActionProposal Proposal,
    PolicyDecision PolicyDecision,
    string PolicyReasonCode,
    ActionApprovalState ApprovalState);

public interface IActionStateStore
{
    ActionState Add(ActionState state);
    bool TryGet(string actionId, out ActionState? state);
    bool TryTransition(string actionId, ActionApprovalState nextState, out ActionState? state);
}

public sealed class InMemoryActionStateStore : IActionStateStore
{
    private readonly ConcurrentDictionary<string, ActionState> states = new(StringComparer.Ordinal);

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

            var updated = current with { ApprovalState = nextState };
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
