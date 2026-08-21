# Contributing to IncidentWeaver

IncidentWeaver is a reference architecture for safe AI incident investigation and guarded remediation. The design goal is architecture depth over feature breadth: small, explicit trust boundaries and deterministic controls matter more than broad product surface.

## Project intent

This repository demonstrates a narrow but well-structured incident-investigation path:

- deterministic control plane
- probabilistic AI runtime
- read-only operational access
- grounded investigation output
- structured action proposals
- explicit approval before state-changing execution
- auditable privileged execution

It is not a general-purpose AIOps product or a large autonomous remediation framework.

## Before contributing

Read these first:

- [README.md](README.md)
- [AGENTS.md](AGENTS.md)
- the relevant issue under [docs/issues](docs/issues)
- the relevant ADRs under [docs/architecture/adr](docs/architecture/adr)

Keep the active slice small and within the accepted architecture.

## Development setup

Use the canonical local setup:

```bash
python scripts/bootstrap-dev.py
python scripts/validate.py
```

This repository expects:

- Python 3.13
- .NET toolchain for the control-plane code
- Docker and Docker Compose for the local topology

## Contribution discipline

- work in small, bounded slices
- preserve accepted ADRs and trust boundaries
- do not opportunistically broaden scope
- prefer direct acceptance evidence over proxy checks
- ensure repository quality gates pass before reporting completion
- do not make normal tests or default CI call real paid AI services
- keep model/provider/framework concerns at the edges
- never give the AI runtime write credentials or write capabilities

## Good contribution areas

Current work that fits the project is focused and architecture-driven, such as:

- prompt-injection and evaluation coverage
- observability
- architecture validation
- documentation
- deterministic tests
- developer experience

Avoid broad product expansion or generic platform features that are outside the active V1 scope.

## Pull requests

Keep pull requests focused and evidence-based:

- one bounded change or slice
- relevant tests
- validation result
- architectural or security impact noted where relevant

A reviewable PR explains why the change is in scope, how it preserves the trust boundary, and what evidence supports it. Pull requests must also pass the same quality gate in CI.
