# Acceptance Evidence

IncidentWeaver separates proving a requirement from proving that the repository baseline is healthy:

```text
Requirement -> Direct Evidence -> Repository Quality Gate -> Independent Review -> CI later
```

## Direct evidence

Direct evidence tests the requirement itself. A material criterion should have a deterministic test, smoke test, or execution trace before completion.

## Proxy evidence

Proxy evidence tests something related but does not prove the requirement. It can supplement direct evidence, but it cannot replace it when direct validation is feasible.

Bad:

```text
An existing .venv passes validation, therefore bootstrap is portable.
```

Good:

```text
Windows/POSIX bootstrap paths are tested, a clean bootstrap is executed,
and the resulting environment passes the repository quality gate.
```

## Completion semantics

Done means all mandatory direct acceptance validations pass, the repository quality gate passes, and no mandatory criterion is unverified. It does not mean an agent believes the implementation is correct or that one large command happened to pass.

The baseline command is `python scripts/validate.py`. Slice-specific direct validations remain separate when they would make the baseline slow, destructive, or difficult to maintain.
