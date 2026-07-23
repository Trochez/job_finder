# Task 25 Evidence — LinkedIn Access Basis Compliance

## Scope

Create compliance record template and validation docs for LinkedIn MCP access
basis.

## Files

- `docs/compliance/linkedin-access-basis.md` — compliance record template and
  validation rules
- `docs/compliance/mcp-supply-chain.md` — MCP pin/upgrade verification docs

## Red

- `docs/compliance/` directory did not exist before implementation.
- No formal compliance record template existed.

## Green

- `docs/compliance/linkedin-access-basis.md` — written; includes access-basis
  record template (YAML), field descriptions, validation rules, known data
  classifications, access renewal policy, and no-automatic-enablement statement.
- `docs/compliance/mcp-supply-chain.md` — written; includes pinned dependency
  manifest, checksum verification procedure, allowed-tool-surface contract,
  upgrade process, and no-automatic-upgrade statement.

## Final verification snapshot

- `uv run pytest -q tests/contract/test_compliance_enablement.py` → `35 passed`
- `uv run pytest -q tests/contract/test_mcp_supply_chain.py` → `35 passed`
- `basedpyright` on compliance gate → `0 errors, 0 warnings, 0 notes`
- `ruff` on all new files → `All checks passed`

## Notes

- Compliance docs reference the programmatic validator in
  `src/job_finder/application/compliance_gate.py`.
- No credentials, no `@latest` references, no live MCP calls documented.
