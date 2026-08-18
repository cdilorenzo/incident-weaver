Perform an AI-security review of the current IncidentWeaver slice.

Read #file:../../docs/architecture/trust-boundaries.md and #file:../copilot-instructions.md before reviewing the change.

Do not edit files.

Explicitly test the design mentally against:

- direct and indirect prompt injection,
- model-generated unauthorized action requests,
- write-tool exposure to the AI runtime,
- approval bypass,
- double execution / replay,
- forged or stale action proposals,
- credential leakage,
- untrusted MCP metadata/results,
- unsafe audit or telemetry content.

Report exploit path, impact, violated boundary, and minimal fix for each material finding. Avoid generic security advice.
