# Task 28 Evidence — Playwright dashboard and accessibility scenarios

## Scope

Launch local app with fake deps, verify desktop/mobile workflows, keyboard/focus semantics, error states, policy-blocked status, redacted notification preview.

## Files

- `tests/e2e/test_dashboard_playwright.py`

## Red

- `uv run pytest -m e2e -q tests/e2e/test_dashboard_playwright.py` — initial failure

## Green

- `uv run pytest -m e2e -q tests/e2e/test_dashboard_playwright.py`
- Result: 15 passed

## Scenarios verified

- Desktop (1280px) dashboard loads with correct title
- All navigation links visible at desktop viewport
- Mobile (375px) dashboard loads with correct title
- Mobile dashboard has accessible menu label
- Mobile nav links visible after viewport change
- Keyboard nav: skip-link focuses main content
- Keyboard nav: profile settings link focusable via Tab
- Error page renders for nonexistent routes (404)
- Health endpoint returns live_mcp: false (policy-blocked status visible)
- Notification preview: redacted payload (no secrets leaked)
- Dashboard shows correct page counts for jobs, eligible, audit, checkpoints
- CSS custom properties define design tokens (--color-primary, --color-bg)
- Dashboard has proper HTML heading hierarchy

## Final verification snapshot

- `uv run pytest -q` → 286 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Uses thread-based local server with `uvicorn.run()` instead of CLI command
- `scope="session"` fixture reuses server across all tests in the module
- Tests run at 1280px and 375px viewports without navigating to LinkedIn/ATS
