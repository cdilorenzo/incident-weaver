# Post-deployment HTTP 500 triage

For HTTP 500 reports after a release, first compare deployment time with log timestamps. Then compare instance health and request failures. A failure isolated to one instance suggests partial startup or readiness trouble rather than a uniformly bad release.

Confirm the pattern with current operational evidence and check historical incidents for recurrence before recommending a change.