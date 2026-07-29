# Assignment Context

Current project

- Status: greenfield docs scaffold
- Main product: automated job application platform
- Current planning artifact: `plan_to_do/automated-job-application-platform-20260728T083139Z.md`

Where look first

- Requirements: `.omo/specs/deep-interview-automated-job-application-platform.md`
- Interview: `.omo/interviews/automated-job-application-platform-20260728T083139Z.md`
- Execution plan: `plan_to_do/automated-job-application-platform-20260728T083139Z.md`

Assignment handoff checklist

- Confirm goal.
- Confirm latest plan.
- Confirm relevant ADRs.
- Confirm tests/runbook links.
- Then implement.

Implementation learnings

- JobSpy MCP is discovery-only. It feeds ranked candidates, not submissions.
- Composio Gmail is reconciliation-only. It attaches status evidence, not application submission.
- Browser automation is separate and must support Easy Apply plus external forms.
- Safety boundary: CAPTCHA, MFA, consent, auth walls, and rate limits queue manual action.
- Tailoring must stay conservative. Never invent education or certifications; missing facts become pending answers.
- Persistence centers on SQLite, append-only audit/status events, and secret references under `.keys/`.
- UI should expose configurable titles, locations, remote preference, employment types, match threshold, daily limit, and start/stop controls.
