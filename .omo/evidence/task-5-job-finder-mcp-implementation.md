# Task 5 Evidence

## Scope

Define provenance-backed candidate fact model.

## Files

- `src/job_finder/domain/candidate.py`
- `tests/unit/test_candidate_facts.py`

## Red

- `python3 -m pytest tests/unit/test_candidate_facts.py`
- Initial failure reason: missing candidate module

## Green

- `python3 -m pytest tests/unit/test_candidate_facts.py`
- Result at task completion: `3 passed`

## Final verification snapshot

- `python3 -m pytest -q` → `19 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`
- `lsp_diagnostics /home/trocha/projects/job_finder/tests/unit/test_candidate_facts.py` → clean

## Notes

- Candidate facts are frozen and provenance-backed.
- Derived claims cannot be stronger than their source claim type.
- Profiles form a single immutable version chain.
