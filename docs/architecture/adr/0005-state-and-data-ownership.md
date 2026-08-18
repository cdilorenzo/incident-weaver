# ADR 0005: Keep control-plane and AI-runtime state ownership separate

- Status: Accepted
- Date: 2026-08-18

## Context

The control plane owns security-relevant lifecycle data while the AI runtime will later own retrieval-oriented data.

## Decision

The control plane owns investigations, action proposals, approvals, executions, and audit records.

The AI runtime owns retrieval indexes and AI-specific evaluation artifacts.

A local V1 may use one PostgreSQL server for convenience, but schemas/credentials and repository code must not create cross-component data ownership.

## Consequences

- security-relevant records remain deterministic control-plane state,
- the AI runtime can evolve retrieval storage independently,
- local infrastructure stays small while logical boundaries remain clear.
