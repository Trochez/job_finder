# Task 18 Evidence — Screening answers and challenge checkpoint pauses

## Scope

Exact normalized question key matching, typed checkpoint states for unknown questions/CAPTCHA/2FA/login challenges, user-cleared resume token.

## Files

- `src/job_finder/application/checkpoints.py`
- `tests/unit/test_screening_answers.py`
- `tests/integration/test_checkpoints.py`

## Red

- `uv run pytest -q tests/unit/test_screening_answers.py tests/integration/test_checkpoints.py` — initial failure

## Green

- `uv run pytest -q tests/unit/test_screening_answers.py tests/integration/test_checkpoints.py`
- Result: passed (exact-match and pause-only behavior)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Identical question reuses saved answer. Punctuation variant yields pause with no retry.
- CAPTCHA/2FA yields pause with no adapter retry.
