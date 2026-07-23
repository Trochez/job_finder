# Task 22B Evidence — CV fact-base and local renderer-source selection flow

## Scope

Select validated candidate fact-base version and private local renderer source reference. No remote credentials.

## Files

- `src/job_finder/web/routes/cv_source.py`
- `src/job_finder/web/templates/cv_source.html`
- `tests/integration/test_cv_source_routes.py`

## Red

- `uv run pytest -q tests/integration/test_cv_source_routes.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_cv_source_routes.py`
- Result: 10 passed (valid profile version/local path saves; invalid/remote/.keys rejected)

## Final verification snapshot

- `uv run pytest -q` → 249 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Approved fact-base version and local renderer reference save correctly.
- Unknown profile version, remote URL, or `.keys` path rejected before persistence.
