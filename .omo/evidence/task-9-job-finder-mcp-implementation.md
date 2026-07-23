# Task 9 Evidence — Hard filters, threshold, deterministic ranking

## Scope

Hard-filter precedence, integer threshold, unset-threshold block, score >= threshold, publication-time then canonical-ID tie-break, typed eligibility decisions.

## Files

- `src/job_finder/domain/eligibility.py`
- `tests/unit/test_eligibility.py`

## Red

- `uv run pytest -q tests/unit/test_eligibility.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/unit/test_eligibility.py`
- Result: passed (all threshold/hard-filter/rank truth tables)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Equal score/threshold is eligible. Ties sort deterministically by publication time then canonical ID.
- Unset threshold and failed work-authorization filter remain ineligible despite high score.
