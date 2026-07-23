# Task 4 Evidence

## Scope

Add private typed settings and SQLite bootstrap.

## Files

- `src/job_finder/adapters/settings.py`
- `src/job_finder/adapters/db.py`
- `tests/integration/test_private_storage_bootstrap.py`

## Red

- `python3 -m pytest tests/integration/test_private_storage_bootstrap.py -q`
- Initial failure reason: missing adapter modules

## Green

- `python3 -m pytest tests/integration/test_private_storage_bootstrap.py -q`
- Result at task completion: `3 passed`

## Final verification snapshot

- `python3 -m pytest -q` → `19 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`
- `lsp_diagnostics /home/trocha/projects/job_finder/tests/integration/test_private_storage_bootstrap.py` → clean

## Notes

- Validation fails closed on `.keys` path references.
- SQLite bootstrap is limited to local file creation and `PRAGMA user_version = 1`.
