# Task 23A Evidence — Read-only job-review and audit-evidence dashboard views

## Scope

Views for scored jobs, factor/source evidence, audit history, cap status, route classification, local audit references. No secrets in views.

## Files

- `src/job_finder/web/routes/jobs.py`
- `src/job_finder/web/routes/audit.py`
- `src/job_finder/web/templates/job_review.html`
- `src/job_finder/web/templates/audit.html`
- `tests/integration/test_job_audit_routes.py`

## Red

- `uv run pytest -q tests/integration/test_job_audit_routes.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_job_audit_routes.py`
- Result: 10 passed (allowlisted response fields, safe error view for malformed data)

## Final verification snapshot

- `uv run pytest -q` → 249 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Job detail exposes score evidence, cap state, route type, local audit ref.
- Malformed audit record produces safe error view with no secret/CV/form data.
