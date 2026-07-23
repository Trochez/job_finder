# Task 18A Evidence — Configurable daily-cap accounting and cap-reached decisions

## Scope

daily_application_cap default 25, positive-integer validation, ApplicationAttemptStarted event, per-run counting, run-level cap_reached event.

## Files

- `src/job_finder/application/daily_cap.py`
- `tests/integration/test_daily_cap.py`

## Red

- `uv run pytest -q tests/integration/test_daily_cap.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_daily_cap.py`
- Result: passed (default/custom cap behavior, atomic ApplicationAttemptStarted counting)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- 25th fake route-attempt event succeeds under default cap. 26th triggers cap_reached.
- After cap reached, all remaining processing halts. Zero is rejected.
- Positive cap over 100 remains accepted.
