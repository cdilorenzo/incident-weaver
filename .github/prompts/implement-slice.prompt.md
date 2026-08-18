Implement exactly one IncidentWeaver issue.

First read:

- #file:../../AGENTS.md
- #file:../copilot-instructions.md
- the issue file supplied by the user under `docs/issues/`
- every ADR referenced by that issue

Then inspect the current repository before editing.

Requirements:

1. Restate the issue goal in one sentence.
2. Identify the files/components you expect to change.
3. Implement only the issue scope and acceptance criteria.
4. Preserve all documented trust boundaries and dependency rules.
5. Add focused tests for introduced behavior.
6. Run relevant format/lint/build/test commands.
7. Review your own diff for unnecessary complexity and remove it.
8. Finish with changed files, validation results, and unresolved risks.

Do not implement future backlog items while you are in the area.
