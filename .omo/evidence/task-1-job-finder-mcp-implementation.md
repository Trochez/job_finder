# Task 1 Evidence

## Scope

Bootstrap strict Python service skeleton.

## Files

- `pyproject.toml`
- `src/job_finder/__init__.py`
- `src/job_finder/domain/__init__.py`
- `tests/unit/test_bootstrap.py`

## Red

- `python3 -m pytest tests/unit/test_bootstrap.py tests/unit/test_domain_types.py`
- Initial failure reason: missing `job_finder` package

## Green

- `python3 -m pytest tests/unit/test_bootstrap.py tests/unit/test_domain_types.py`
- Result at task completion: `7 passed`

## Final verification snapshot

- `python3 -m pytest -q` → `19 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`
- `lsp_diagnostics /home/trocha/projects/job_finder/src/job_finder` → clean

## Notes

- Project uses `src/` layout with strict `basedpyright`, `ruff`, and `pytest` configuration declared in `pyproject.toml`.
