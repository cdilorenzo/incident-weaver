# ADR 0003: State-changing actions execute outside the AI runtime

- Status: Accepted
- Date: 2026-08-18

## Context

Prompt injection and excessive agency become materially more dangerous if the model can directly invoke privileged mutation tools.

## Decision

The AI runtime never receives state-changing credentials or write-tool access.

A model may return a structured `ActionProposal`. The ASP.NET control plane validates the proposal, evaluates deterministic policy, records explicit human approval, and only then invokes a privileged executor.

## Consequences

- prompt compromise does not directly grant mutation capability,
- approval is a real security boundary rather than prompt convention,
- action execution can be audited and made replay-safe,
- additional control-plane code is required for proposal lifecycle and execution.
