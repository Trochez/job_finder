# Task 30B Evidence — Architecture and Runbook Documentation

## Scope

Write architecture documentation with ADRs and operator runbook for fake-mode
deployment.

## Files

- `docs/architecture.md` — architecture documentation covering:
  - Package layout with layer rules (domain → application → adapters)
  - Scoring governance (version-locked policy weights)
  - Compliance boundaries (gate is validator, policy gate is enforcer)
  - 7 ADRs (ADR-001 through ADR-007)
  - Key architectural decisions
- `docs/runbook.md` — operator runbook covering:
  - Fake-mode startup command
  - systemd-user timer installation
  - Watermark recovery (SQLite commands)
  - Rollback procedure
  - Evidence file naming convention and locations
  - Manual live-enable preconditions (4 checks)
  - Configuration reference (env vars, defaults)
  - Health check command

## Red

- No architecture docs existed.
- No runbook existed.

## Green

- `docs/architecture.md` — 7 ADRs documented, layer rules, scoring governance,
  compliance boundaries.
- `docs/runbook.md` — all operational procedures documented, live-enable
  preconditions explicitly require operator action.
- `docs/index.md` — amended to reference new docs.

## Final verification snapshot

- All markdown files render cleanly.
- `ruff` → `All checks passed`
- All 35 compliance and supply chain tests pass.

## Notes

- Runbook clearly states live MCP access is never enabled automatically.
- ADR-006 explicitly documents the read-only compliance gate principle.
- No credentials, no live execution steps in docs.
