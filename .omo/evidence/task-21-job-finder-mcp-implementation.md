# Task 21 Evidence — Dashboard design system and accessible shell

## Scope

DESIGN.md, design tokens, navigation, responsive local shell, focus/keyboard/error/empty/loading states, server-rendered templates.

## Files

- `DESIGN.md`
- `src/job_finder/web/static/css/style.css`
- `src/job_finder/web/templates/base.html`
- `src/job_finder/web/templates/dashboard.html`
- `src/job_finder/web/routes/dashboard.py`
- `tests/integration/test_dashboard_shell.py`

## Red

- `uv run pytest -q tests/integration/test_dashboard_shell.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_dashboard_shell.py`
- Result: 9 passed (keyboard navigation, landmarks, responsive shell, blocked-live state)

## Final verification snapshot

- `uv run pytest -q` → 249 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Semantic HTML with ARIA landmarks for navigation.
- Keyboard navigation reaches status and dashboard landmarks.
- Blocked-live-MCP state visibly announced (not dismissable through UI).
