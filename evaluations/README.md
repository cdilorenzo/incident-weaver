# Evaluations

Slice 009 splits verification of IncidentWeaver's prompt-injection and grounding
claims into two deliberately separate kinds of evidence. Do not confuse them.

## 1. Deterministic security tests vs. probabilistic AI evaluations

**Deterministic security/architecture tests** (`tests/ai-runtime/test_prompt_injection_security.py`,
`tests/control-plane/PromptInjectionSecurityTests.cs`) directly assert structural invariants of the
system: tool-surface enforcement, schema rejection of unmapped fields, evidence-ID authority,
deterministic policy outcomes, and the approval/execution state machine. They do not depend on a
model choosing to behave safely — the assertion fails if the underlying code no longer enforces the
invariant, regardless of what any model would do.

**AI evaluations** (this directory) run curated scenarios through the real investigation pipeline
(`agent.py` + `app.py`) driven by `pydantic_ai.models.test.TestModel`, a scripted/fake model. They
check expected *properties* of the resulting `InvestigationResult` (evidence kinds present, no
fabricated evidence, action-proposal shape, absence of a proposal when evidence is
insufficient/conflicting) rather than exact prose.

Do not treat AI evaluation cases as security proof: because the model is scripted, these cases do
not prove a live LLM will actually resist a given attack. They prove that *given* a hypothetical
model output (benign or adversarial), the surrounding harness still enforces bounded schemas,
sanitization, and grounding.

## 2. What Slice 009 proves

- A compromised or malicious read MCP endpoint cannot smuggle a write tool into the agent's
  toolset; the grounding toolset fails closed on any unexpected tool name.
- The investigation agent's construction API has no write-capability seam.
- Malicious content in the user question, retrieved knowledge, operational logs, or known-incident
  history cannot expand the tool surface, change required grounding, or create authoritative
  evidence/approval state — it can only ever appear as bounded, sanitized evidence text.
- A model cannot self-approve or self-identify: any `action_id`/`approval_state`/`policy` field
  attached to a proposal draft is schema-invalid (`extra="forbid"` in Python,
  `JsonUnmappedMemberHandling.Disallow` in .NET) and fails closed rather than being silently ignored
  and accepted.
- Deterministic control-plane policy denies unsupported action types and wildcard/service-wide
  targets regardless of what the rationale text says; the policy never parses rationale for
  embedded instructions.
- Attacker-controlled evidence IDs from the AI runtime are never trusted; the control plane
  generates and binds its own evidence identity.
- Execution requires an `Approved`, fresh proposal; a `PendingApproval` action cannot execute no
  matter what its rationale claims.
- A compromised write MCP endpoint advertising more than the singleton `restart_instance` tool is
  refused rather than partially trusted.
- The canonical checkout-api investigation still succeeds end-to-end with all four required
  read-only evidence sources present.
- None of the above requires Azure/OpenAI credentials, a paid model call, or network access.

## 3. What Slice 009 deliberately does NOT prove

- That a real LLM (e.g. an Azure OpenAI deployment) will actually ignore any specific injected
  instruction. Passing these evaluations does **not** mean a model is "prompt-injection proof."
- Any statement about model output quality, factual accuracy, or reasoning ability.
- That every conceivable injection phrasing is covered — the threat cases here are representative,
  not exhaustive.
- Anything about production authentication, network security, or infrastructure hardening.

The project's actual security claim rests on capability isolation (no write MCP access from the AI
runtime), a bounded tool surface, server-owned evidence/action identity, deterministic policy,
explicit human approval, and privileged execution outside the AI runtime — not on trusting model
behavior. See [docs/architecture/trust-boundaries.md](../docs/architecture/trust-boundaries.md).

## 4. Running deterministic evaluations

Both the deterministic security tests and the AI evaluation cases run as part of the normal test
suite, with no live model credentials required:

```powershell
python -m pytest tests/ai-runtime/test_prompt_injection_security.py
dotnet test tests/control-plane/ControlPlane.Tests.csproj --filter PromptInjectionSecurityTests
python -m pytest evaluations
```

Or standalone, for a small human-readable report:

```powershell
python evaluations/runner.py
```

All of the above are also exercised by the repository baseline gate:

```powershell
python scripts/validate.py
```

## 5. Optional live-model evaluation

No live-model evaluation runner exists in this slice. If one is added later, it must:

- be explicitly opt-in (for example, gated behind an environment variable and a separate script),
- never run as part of `python scripts/validate.py` or the normal CI quality gate,
- require real provider credentials only when explicitly invoked,
- reuse the same `EvaluationCase`/`Expectation` shapes in `runner.py` so cases are not duplicated.
