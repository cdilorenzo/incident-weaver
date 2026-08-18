---
applyTo: "src/control-plane/**/*.cs,tests/control-plane/**/*.cs"
---

# .NET control-plane instructions

- Target .NET 10 unless an explicit ADR changes the target.
- Keep control-plane decisions deterministic and independent of model-provider SDKs.
- Do not reference Pydantic AI or Python implementation concepts from control-plane domain/application code.
- Model approval and execution state explicitly; do not encode authorization decisions in prompt text.
- Prefer small records/value objects for contracts and focused services for policy/execution behavior.
- Keep HTTP, persistence, MCP client, and authentication concerns at infrastructure edges.
- Use async APIs for I/O paths and propagate cancellation tokens.
- Add unit tests for policy/state transitions and integration tests only where boundary behavior is the subject under test.
