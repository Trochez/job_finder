# Task 14 Evidence — Normalize minimal job intake and data-provenance records

## Scope

Transform typed MCP job results into canonical job model, retain minimum allowed fields/evidence references, reject incomplete identities.

## Files

- `src/job_finder/application/job_intake.py`
- `tests/integration/test_job_intake.py`

## Red

- `uv run pytest -q tests/integration/test_job_intake.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_job_intake.py`
- Result: passed (normalized records preserve source fields, reject unsupported payloads)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Minimal fake posting normalized and audited. Posting without external ID or source provenance cannot reach scoring.
