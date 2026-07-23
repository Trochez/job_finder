# Task 6 Evidence

## Scope

Add fakeable default-deny MCP boundary.

## Files

- `src/job_finder/adapters/mcp/port.py`
- `src/job_finder/adapters/mcp/fake.py`
- `src/job_finder/adapters/mcp/policy.py`
- `tests/contract/test_mcp_policy_gate.py`

## Red

- `python3 -m pytest tests/contract/test_mcp_policy_gate.py`
- Initial failure reason: unimplemented policy and fake adapter stubs

## Green

- `python3 -m pytest tests/contract/test_mcp_policy_gate.py`
- Result at task completion: `2 passed`

## Final verification snapshot

- `python3 -m pytest -q` → `19 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`
- `lsp_diagnostics /home/trocha/projects/job_finder/tests/contract/test_mcp_policy_gate.py` → clean

## Notes

- `server_name="fake"` is the only permitted MCP target in Wave 1.
- Every non-fake server request raises `LiveAccessDenied`.
