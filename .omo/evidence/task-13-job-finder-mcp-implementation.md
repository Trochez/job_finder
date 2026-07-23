# Task 13 Evidence — Requested MCP client adapter against typed port

## Scope

Adapter translating reviewed MCP tool contract into typed results/checkpoint errors, wired through policy gate and fake test transport.

## Files

- `src/job_finder/adapters/mcp/port.py`
- `src/job_finder/adapters/mcp/fake.py`
- `src/job_finder/adapters/mcp/linkedin_client.py`
- `src/job_finder/adapters/mcp/policy.py`
- `tests/contract/test_linkedin_mcp_adapter.py`

## Red

- `uv run pytest -q tests/contract/test_linkedin_mcp_adapter.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/contract/test_linkedin_mcp_adapter.py`
- Result: passed (every supported fake response maps to typed domain result)

## Final verification snapshot

- `uv run pytest -q` → 158 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- Challenge, malformed response, or prohibited live config yields pause/deny state with no retry bypass.
- No live MCP executable invoked by tests.
