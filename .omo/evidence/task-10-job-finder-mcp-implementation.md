# Task 10 Evidence — Canonical job identity and idempotent dedup

## Scope

Canonical identity from source, immutable external job ID, canonical company key, uniqueness constraints, identity-unverified handling.

## Files

- `src/job_finder/domain/job_identity.py`
- `src/job_finder/adapters/repositories/jobs.py`
- `tests/integration/test_job_dedupe.py`

## Red

- `uv run pytest -q tests/integration/test_job_dedupe.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_job_dedupe.py`
- Result: passed (duplicate inserts idempotent, submissions cannot repeat)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Job identity hash uses source + external_job_id + canonical_company_key.
- Missing external ID is audited `identity_unverified` and never eligible.
