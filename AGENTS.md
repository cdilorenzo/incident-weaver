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

Do not weaken typing, linting, analyzers, tests, or architecture checks to make generated code pass. Fix the cause or explicitly report an unavoidable third-party limitation.

## Completion gate

- A task is not complete until every validation command required by the active issue and repository quality gate has executed successfully.
- Never report a change as complete, green, ready for review, or done when a required validation command fails.
- Never substitute a related validation command for a required command without reporting that exact difference.
- Never weaken, skip, exclude, suppress, or reconfigure a quality check merely to make generated code pass.
- If a required check cannot run because of the environment, report the task as incomplete and state the exact blocker.
- Validation reports must state the exact command and PASS/FAIL result.

## Acceptance evidence

- Before implementation, identify how each material acceptance criterion will be directly validated.
- Prefer direct validation over proxy evidence whenever the requirement itself can reasonably be tested.
- A passing downstream state does not prove that its setup, migration, bootstrap, or transition path works.
- If a material acceptance criterion has no direct validation, add one or explicitly mark the criterion unverified.
- An unverified mandatory criterion means the task is incomplete.
- Do not claim completion based only on code inspection when deterministic execution can prove the requirement.

Examples: bootstrap reproducibility requires a clean bootstrap; package installation requires actually installing the package; cross-platform behavior requires testing each platform branch.
