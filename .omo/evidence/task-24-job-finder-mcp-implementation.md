# Task 24 Evidence — Run-once CLI, systemd-user timer, and single-instance lock

## Scope

Deterministic run-once command, systemd --user unit/timer, single-instance lock invoking one-catch-up service. No credentials embedded.

## Files

- `src/job_finder/worker/cli.py`
- `deploy/systemd/job-finder.service`
- `deploy/systemd/job-finder.timer`
- `tests/integration/test_run_once_cli.py`

## Red

- `uv run pytest -q tests/integration/test_run_once_cli.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_run_once_cli.py`
- Result: passed (fake clock executes one window, writes evidence)

## Final verification snapshot

- `uv run pytest -q` → 165 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Second concurrent invocation exits typed locked/no-op without adapter call.
- systemd-analyze verify deploy/systemd/job-finder.* passes in Linux.
