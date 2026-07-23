# Task 11A Evidence — SQLite migrations and repos for job/application state

## Scope

Migrations and repositories for candidate profiles, canonical jobs, application-route state, run watermark, immutable workflow-transition records.

## Files

- `src/job_finder/adapters/repositories/jobs.py`
- `src/job_finder/adapters/repositories/workflow.py`
- `src/job_finder/adapters/repositories/_query_helpers.py`
- `src/job_finder/adapters/migrations.py`
- `alembic/versions/20260722_0001_canonical_state.sql`
- `tests/integration/test_workflow_repository.py`

## Red

- `uv run pytest -q tests/integration/test_workflow_repository.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_workflow_repository.py`
- Result: passed (migration, unique identity, immutable transition persistence)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Query helpers extracted to `_query_helpers.py` for fetchone/fetchall/execute/read patterns.
- Duplicate identity or illegal transition fails atomically without extra row.
