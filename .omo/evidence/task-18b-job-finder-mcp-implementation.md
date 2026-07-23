# Task 18B Evidence — Submission-route classification and execution-access state

## Scope

Classify as easy_apply/external_ats/unsupported. Persist fake_only/live_access_blocked/eligible_for_manual_enablement/manual_handoff_required. Bind rendered-CV artifact.

## Files

- `src/job_finder/application/submission_routes.py`
- `tests/contract/test_submission_routes.py`

## Red

- `uv run pytest -q tests/contract/test_submission_routes.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/contract/test_submission_routes.py`
- Result: passed (route kind/access state independent, every fake attempt binds CV artifact, all routes non-live)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Missing artifact, unknown route, or live-enabled request denies safely with no outbound call.
- ADR-0005: live submission routes modeled/tested with fakes but blocked in production.
