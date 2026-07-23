# Task 15 Evidence — Local CV rendering boundary for Overleaf artifacts

## Scope

Versioned renderer port over user-provided local synced/exported Overleaf working tree, fact-base-supported variants, immutable rendered-artifact IDs.

## Files

- `src/job_finder/adapters/cv_renderer/port.py`
- `src/job_finder/adapters/cv_renderer/local_renderer.py`
- `tests/integration/test_cv_renderer.py`

## Red

- `uv run pytest -q tests/integration/test_cv_renderer.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/integration/test_cv_renderer.py`
- Result: passed (generated metadata references only approved fact IDs, immutable artifact ID)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Template demanding unsupported claim returns EvidenceInsufficient without artifact output.
- No Overleaf credentials stored or scraped.
