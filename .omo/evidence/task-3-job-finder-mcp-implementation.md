# Task 3 Evidence

## Scope

Model typed domain identities, states, and typed failures.

## Files

- `src/job_finder/domain/errors.py`
- `src/job_finder/domain/ids.py`
- `src/job_finder/domain/states.py`
- `tests/unit/test_domain_types.py`

## Red

- `python3 -m pytest tests/unit/test_bootstrap.py tests/unit/test_domain_types.py`
- Initial failure reason: missing `job_finder` package and domain modules

## Green

- `python3 -m pytest tests/unit/test_bootstrap.py tests/unit/test_domain_types.py`
- Result at task completion: `7 passed`

## Final verification snapshot

- `python3 -m pytest -q` → `19 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`
- `lsp_diagnostics /home/trocha/projects/job_finder/tests/unit/test_domain_types.py` → clean

## Notes

- Exposes branded IDs, validated IANA timezone parsing, explicit workflow/checkpoint/eligibility state tags, and typed domain errors.
