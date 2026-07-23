# Task 7 Evidence — Candidate fact-base import

## Scope

Parse user-provided structured CV facts, persist profile version/provenance, reject unsupported claims.

## Files

- `src/job_finder/application/candidate_import.py`
- `src/job_finder/domain/candidate.py`
- `tests/integration/test_candidate_import.py`

## Red

- `uv run pytest -q tests/integration/test_candidate_import.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_candidate_import.py`
- Result: passed (imports facts with source references, rejects unsupported claims)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors
- `lsp_diagnostics /home/trocha/projects/job_finder/src/job_finder` → clean

## Notes

- Fact import validates source references, provenance, and rejects claims without evidence.
- CandidateProfile uses versioned immutable records.
