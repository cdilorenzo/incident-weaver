# IncidentWeaver agent instructions

Read `.github/copilot-instructions.md` before making changes.

For every implementation task:

1. Read the relevant issue specification under `docs/issues/`.
2. Read the architecture documents and ADRs referenced by that issue.
3. Inspect the current repository before proposing changes.
4. Implement only the requested slice. Do not opportunistically add future features.
5. Preserve the trust boundary: the AI runtime must never gain state-changing capabilities or credentials.
6. Prefer explicit contracts, small interfaces, deterministic behavior, and testable seams.
7. Add or update tests for behavior introduced by the slice.
8. Run the smallest relevant validation commands available in the repository.
9. End with a concise summary of changed files, tests run, and any unresolved risks.

If an issue conflicts with an accepted ADR, stop and explain the conflict instead of silently changing the architecture.
