# Task 8 Evidence — Fixed weighted scoring engine

## Scope

30/30/25/10/5 factor model with applicable-criterion denominator, zero for missing evidence, half-up rounding, immutable ScoringPolicyVersion.

## Files

- `src/job_finder/domain/scoring.py`
- `src/job_finder/domain/scoring_policy.py`
- `tests/unit/test_scoring.py`

## Red

- `uv run pytest -q tests/unit/test_scoring.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/unit/test_scoring.py`
- Result: passed (known fixtures produce expected 0-100 integers, evidence breakdowns, policy version)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- ScoringPolicyVersion is an immutable named value; any factor/weight change requires new version.
- Half-up whole-percent rounding applied.
