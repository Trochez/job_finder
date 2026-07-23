# Task 17 Evidence — Workflow transitions, kill switch, and resume rules

## Scope

Exhaustive state transitions (evaluated, eligible, blocked, ready, submitted, cancelled, failed), kill switch cancel/block, no auto-resume of blocked live action.

## Files

- `src/job_finder/application/workflow.py`
- `tests/unit/test_workflow_transitions.py`
- `tests/integration/test_kill_switch.py`

## Red

- `uv run pytest -q tests/unit/test_workflow_transitions.py tests/integration/test_kill_switch.py` — initial failure

## Green

- `uv run pytest -q tests/unit/test_workflow_transitions.py tests/integration/test_kill_switch.py`
- Result: passed (all transitions verified, kill switch cancels/blocks correctly)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Cleared kill switch allows fake run. Trigger during active work yields cancelled status.
- No new adapter call after kill switch engaged.
