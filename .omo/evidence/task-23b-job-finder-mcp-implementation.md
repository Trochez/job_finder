# Task 23B Evidence — Checkpoint-resume and kill-switch dashboard controls

## Scope

Controls to surface checkpoints, accept exact answer/resume transition, set/clear kill switch. No challenge automation.

## Files

- `src/job_finder/web/routes/checkpoints.py`
- `src/job_finder/web/templates/checkpoints.html`
- `tests/integration/test_checkpoint_routes.py`

## Red

- `uv run pytest -q tests/integration/test_checkpoint_routes.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_checkpoint_routes.py`
- Result: 10 passed (exact answer resumes checkpoint; CAPTCHA shows pause-only; kill switch toggle works)

## Final verification snapshot

- `uv run pytest -q` → 249 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Exact known answer resumes fake checkpoint.
- Clear kill switch permits fake run.
- CAPTCHA/live-route checkpoint displays pause-only controls.
- Invalid answer displays pause-only controls.
