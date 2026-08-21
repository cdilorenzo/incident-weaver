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

## Responsibility model

| Evidence | Developer | Reviewer | Security Reviewer |
| --- | --- | --- | --- |
| Repository quality gate | run | independently rerun | not duplicated |
| Slice functional criteria | run | independently verify | only if security-relevant |
| Security architecture | implement/test | inspect general correctness | independently inspect |
| Security executable tests | run | execute as part of gate | inspect proof/test design |

Independent verification means the assigned owner does not rely on the implementer's report; it does not require every role to duplicate every check. The Security Reviewer remains read/search-only and evaluates security scope directly. A role limitation is not an implementation defect unless a mandatory security invariant lacks proof.
