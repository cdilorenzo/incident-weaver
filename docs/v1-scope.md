# V1 Scope

## Product goal

Demonstrate one complete, production-oriented incident investigation and guarded remediation path without building a general operations platform.

## Canonical incident

User input:

> Checkout API returns HTTP 500 since deployment 1.8.4. What happened?

The V1 data set is intentionally constructed so that the system can discover a defensible diagnosis from multiple evidence sources.

## Required V1 capabilities

- one investigation agent,
- structured investigation output,
- evidence and citations,
- read-only operational tools through MCP,
- a small RAG knowledge base,
- model-provider abstraction,
- action proposal as data,
- deterministic policy evaluation,
- explicit human approval,
- privileged execution outside the AI runtime,
- audit trail,
- prompt-injection evaluation,
- OpenTelemetry-based observability,
- automated tests and CI.

## Explicit non-goals

- multi-agent orchestration,
- agent swarms,
- Kubernetes,
- Kafka,
- event sourcing,
- production SSO/OAuth,
- large-scale data ingestion,
- model fine-tuning,
- custom model training,
- autonomous background remediation,
- a complex web UI,
- many real vendor integrations.

## Success criterion

A reviewer should be able to trace the complete path from user question to evidence, proposed action, deterministic approval gate, privileged execution, and audit record and understand why prompt injection cannot directly cross the write boundary.
