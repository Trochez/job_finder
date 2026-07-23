# Task 12 Evidence — 90-day purge and minimal submission tombstones

## Scope

Scheduled purge use case deleting detailed data at 90 days, preserving only non-content hashed submission tombstones for dedupe.

## Files

- `src/job_finder/application/retention.py`
- `tests/integration/test_retention.py`

## Red

- `uv run pytest -q tests/integration/test_retention.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_retention.py`
- Result: passed (exactly-expired detailed records purged, safe tombstone remains)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Record at day 90 minus one survives. Record at day 90 plus one loses prohibited fields.
- Duplicate still cannot resubmit after purge (tombstone preserves job_identity_hash).
