# Task 26 Evidence — MCP Supply Chain Documentation

## Scope

Write MCP supply chain documentation covering pinned dependency manifest,
checksum verification, allowed-tool-surface contract, and upgrade process.

## Files

- `docs/compliance/mcp-supply-chain.md` — supply chain docs (shared file with
  task 25)

## Red

- No supply chain documentation existed before.

## Green

- `docs/compliance/mcp-supply-chain.md` — covers all four required areas:

  1. **Pinned dependency manifest** — per-server YAML entry with name, repo,
     commit, tag, checksum, tools, classification, review date.
  2. **Checksum verification** — SHA-256 verification procedure with clone →
     checkout → archive → compare steps.
  3. **Allowed-tool-surface contract** — minimal-surface principle, audit
     trail, review requirement for additions.
  4. **Upgrade process** — 6-step operator procedure with contract test
     verification.
  5. **No-automatic-upgrade statement** — tests and gate are read-only.

## Final verification snapshot

- `uv run pytest -q tests/contract/test_mcp_supply_chain.py` → `35 passed`
- `uv run pytest -q tests/contract/test_compliance_enablement.py` → `35 passed`
- `basedpyright` → `0 errors, 0 warnings, 0 notes`

## Notes

- Supply chain manifest is defined in code at
  `tests/contract/test_mcp_supply_chain.py` as `_MANIFEST` constant.
- All pins validate against the compliance gate.
