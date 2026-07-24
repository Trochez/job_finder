# job_finder

Private single-user job-finding service with typed domain models, FastAPI dashboard, SQLite persistence, and policy-gated MCP integration.

## Entry points

- `AGENTS.md` — project operating contract
- `docs/index.md` — documentation landing page
- `docs/architecture.md` — architecture and ADR documentation
- `docs/runbook.md` — operator runbook
- `docs/user-guide.md` — end-user workflow guide (profile, review, audit, checkpoints)
- `docs/compliance/` — MCP compliance and access-basis records

## Current scope

### Implemented (Waves 1-5)

Domain layer — typed IDs, branded errors, scoring engine (30/30/25/10/5), eligibility/threshold/ranking, candidate facts with provenance, canonical job identity, immutable workflow states, checkpoint/kill switch, daily cap, submission route modeling.

Application layer — candidate import, job intake, scoring engine, eligibility evaluation, workflow state machine, screening answer/checkpoint service, daily-cap accounting, run-cycle orchestration (24h windows, catch-up), submission-route classification, retention (90-day purge), compliance gate (access-basis validation).

Adapters — SQLite repository layer (jobs, workflow, audit, migrations), private settings with secret-path guard, default-deny MCP policy gate, fake MCP adapter, LinkedIn MCP port/adapter, Telegram notification port/fake, CV renderer port/local renderer, Overleaf CV pull (CvSourcePort + OverleafGitSource/OverleafGitRenderer with Git token auth and typed error hierarchy), systemd timer/deploy units.

Web — FastAPI application factory, lifespan/dependency wiring, health endpoint, error mapping, Jinja2 templated dashboard (profile settings, CV source, job review, audit, checkpoint controls), static CSS, responsive shell.

Testing — 249+ unit/integration/contract tests, TDD evidence files, fake dependency injection, mock SQLite databases.

### Verification

- `uv run ruff check src/ tests/` — All checks passed
- `uv run basedpyright` — 0 errors
- `uv run pytest -q` — 405 passed
- Evidence: `.omo/evidence/` — 28+ evidence files for tasks 1-30B

## Execution policy

- Keep this project aligned with the master workspace contract.
- OpenViking scope: `viking://resources/job_finder`
- Compliance gate is read-only — enforcement lives in the MCP policy gate.

## Next steps

1. Complete E2E, Playwright, and security test suites.
2. Run F1-F4 final verification.
3. Add real MCP integration after separate written access-basis approval.
4. Overleaf CV pull wired into dashboard CV Source UI for live Git operations.
