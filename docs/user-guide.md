# job_finder User Guide

This guide is for final users running job_finder.

## What app does

job_finder helps automate job discovery, ranking, tailoring, application submission, and status tracking.

## Before you start

- Keep secrets in `.keys/`.
- Keep local data in SQLite.
- Use Overleaf as source CV.
- Use Gmail only for reconciliation/status evidence.
- Use browser automation for submission.

## Start app

Current repo has no explicit app launcher file or package script in docs-only workspace.
When app implementation exists, start it with project’s documented start command and verify it loads before enabling automation.

## Safe setup steps

1. Set job titles.
2. Set locations.
3. Set remote preference.
4. Set employment types.
5. Set daily top-job limit.
6. Set match threshold.
7. Confirm Overleaf and Gmail credentials.
8. Confirm browser automation profile and selectors.

## First run

1. Run dry-run mode first.
2. Review discovered jobs.
3. Check match scores.
4. Check tailored CV output.
5. Check unresolved questions.
6. Check status reconciliation.

## Daily use

1. Start scheduled run only after settings look right.
2. Stop scheduled run before changing credentials or browser selectors.
3. Review pending questions before submit.
4. Review submitted jobs and Gmail status evidence.

## How workflow works

1. Discover LinkedIn jobs from last 24 hours.
2. Deduplicate results.
3. Rank jobs against CV and settings.
4. Tailor CV conservatively.
5. Submit selected applications through browser automation.
6. Track status through Gmail.

## Manual intervention rules

- CAPTCHA → stop automation, queue manual action.
- MFA → stop automation, queue manual action.
- Consent wall → stop automation, queue manual action.
- Auth wall → stop automation, queue manual action.
- Rate limit or block → stop automation, queue manual action.
- Unknown factual question → mark pending, answer later.

## Safety rules

- Do not invent education or certifications.
- Do not bypass anti-bot or auth controls.
- Treat Gmail as evidence only.
- Keep secret values out of version control.

## Recovery

1. Inspect SQLite state.
2. Check latest run events.
3. Fix settings or credentials.
4. Rerun dry-run.
5. Resume scheduled automation only after stable run.

## Where to read next

- `docs/README.md`
- `docs/agent-index.md`
- `docs/assignment-context.md`
- `docs/architecture/overview.md`
- `docs/runbooks/job-application-platform.md`
- `docs/decisions/2026-07-28-contract-first-modular-monolith.md`
