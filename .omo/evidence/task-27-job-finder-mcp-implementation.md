# Task 27 Evidence — End-to-end fake-MCP integration scenarios

## Scope

Compose temporary SQLite, fake MCP, fake renderer, fake notifier, FastAPI deps into full job-cycle tests.

## Files

- `tests/e2e/test_fake_mcp_job_cycle.py`
- `tests/fakes/sentinels.py`
- `tests/conftest.py`

## Red

- `uv run pytest -q tests/e2e/test_fake_mcp_job_cycle.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/e2e/test_fake_mcp_job_cycle.py`
- Result: 8 passed

## Flows verified

- Eligible fake job flows to ready_for_user with audit and bound CV artifact
- Duplicate submission is idempotent (returns same record)
- Unset threshold blocks eligibility (no ready_for_user)
- Hard-filter failure blocks (workflow stays at INELIGIBLE)
- Kill switch engaged stops processing at ELIGIBLE (never reaches READY_FOR_USER)
- Checkpoint blocks and pause pauses processing with typed checkpoint state
- Post-cap jobs are not processed (daily cap reached)
- FakeMCPJobSource discovers jobs and returns typed JobListing fixtures

## Final verification snapshot

- `uv run pytest -q` → 286 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Uses real bootstrapped SQLite database with migrations applied
- All adapters use fakes — no network access in any test
- `from __future__ import annotations` pattern maintains clean import structure
