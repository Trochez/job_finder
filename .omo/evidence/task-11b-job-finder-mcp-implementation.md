# Task 11B Evidence — Append-only evaluation audit and score-evidence repo

## Scope

Append-only audit for evaluated-job decisions, threshold, score version, factor breakdown, source fields, evidence references, ranking metadata, route result, CV artifact reference.

## Files

- `src/job_finder/adapters/repositories/audit.py`
- `tests/integration/test_audit_repository.py`

## Red

- `uv run pytest -q tests/integration/test_audit_repository.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_audit_repository.py`
- Result: passed (one evaluation atomically appends decision, evidence, CV-artifact reference)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Evaluation writes complete evidence/threshold/artifact trail in single transaction.
- Injected audit write error rolls back decision with no partial record exposed.
