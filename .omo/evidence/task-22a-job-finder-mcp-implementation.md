# Task 22A Evidence — Profile settings: timezone, hard filters, threshold, cap

## Scope

Typed profile forms for IANA timezone, hard filters, integer threshold, daily application cap. Parse-on-boundary, profile persistence.

## Files

- `src/job_finder/web/routes/profile_settings.py`
- `src/job_finder/web/templates/profile_settings.html`
- `tests/integration/test_profile_settings_routes.py`

## Red

- `uv run pytest -q tests/integration/test_profile_settings_routes.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_profile_settings_routes.py`
- Result: 10 passed (valid threshold/cap/timezone saves; blank/out-of-range rejected)

## Final verification snapshot

- `uv run pytest -q` → 249 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Valid threshold/cap/timezone saves and displays on GET.
- Blank/out-of-range threshold or invalid cap yields field error.
- Eligibility unavailable until valid settings saved.
