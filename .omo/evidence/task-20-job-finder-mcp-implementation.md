# Task 20 Evidence — FastAPI composition, lifespan, and typed dependency boundary

## Scope

Application factory, lifespan resource setup, typed repositories/ports dependencies, health endpoint, error mapping. No live MCP at startup.

## Files

- `src/job_finder/web/app.py`
- `src/job_finder/web/deps.py`
- `src/job_finder/web/errors.py`
- `tests/integration/test_app_lifespan.py`
- `tests/integration/test_health.py`

## Red

- `uv run pytest -q tests/integration/test_app_lifespan.py tests/integration/test_health.py` — initial failure

## Green

- `uv run pytest -q tests/integration/test_app_lifespan.py tests/integration/test_health.py`
- Result: passed (startup/shutdown and dependency overrides verified)

## Final verification snapshot

- `uv run pytest -q` → 165 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Default live MCP config returns blocked state with no external process/network call.
- TestClient context exposes health with fake dependencies.
