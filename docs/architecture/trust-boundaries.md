# Trust Boundaries

## Boundary 1: Untrusted input to AI runtime

User text, retrieved documents, model output, MCP metadata, and MCP results are data, not authority.

A retrieved document can influence diagnosis but cannot change system policy or grant capabilities.

## Boundary 2: AI runtime to control plane

The AI runtime returns structured data. In particular, a remediation is represented as an `ActionProposal`, not an executable command.

The control plane validates proposal type, target, lifecycle state, caller authorization, policy, approval state, freshness, and replay status before execution.

## Boundary 3: Read capability vs write capability

The AI runtime has access only to read-only operational capabilities.

State-changing credentials and MCP capabilities are available only to the privileged execution path controlled by the ASP.NET control plane.

This boundary must hold even if the model is fully compromised by prompt injection.

## Boundary 4: Human approval

Human approval is a control-plane state transition, not a model instruction.

Approval must be tied to a specific immutable proposal and must not be reusable for a different target or action.

## Boundary 5: Audit and telemetry

Audit records are deterministic system records. Model-generated text may be included as evidence/rationale but must not be confused with trusted execution facts.

Secrets, raw credentials, and unnecessary sensitive content must not be recorded.
