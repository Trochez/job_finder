# Task 16 Evidence — Run window, watermark, and one-catch-up orchestration

## Scope

Single-run application service deriving profile-local 24-hour windows, persisting successful UTC watermarks, one deduplicated catch-up, serializing active runs.

## Files

- `src/job_finder/application/run_cycle.py`
- `tests/integration/test_run_windows.py`

## Red

- `uv run pytest -q tests/integration/test_run_windows.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_run_windows.py`
- Result: passed (deterministic timezone/watermark/catch-up fixtures)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- One missed interval yields one deduped catch-up. Adapter failure leaves watermark unchanged.
- Concurrent start returns RunAlreadyActive.
