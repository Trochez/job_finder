# job_finder Docs Index

This is the documentation landing page for `job_finder`.

## Available docs

- `index.md` — root project entrypoint
- `AGENTS.md` — project operating contract
- `linkedin-mcp.md` — LinkedIn MCP setup and auth status
- `architecture.md` — architecture documentation with ADRs
- `runbook.md` — operator runbook for fake-mode deployment
- `user-guide.md` — end-user workflow guide (profile, review, audit, checkpoints)
- `compliance/linkedin-access-basis.md` — written access-basis compliance record
- `compliance/mcp-supply-chain.md` — MCP supply chain verification docs
- `../.omx/specs/deep-interview-job_finder.md` — non-sensitive requirements overview for the future workflow

## Status

Docs cover managed bootstrap scaffold, architecture, compliance, operations, and end-user guide.
LinkedIn MCP is configured and authenticated via secure interactive browser login.
Compliance gate validates access-basis records but never enables live access.

## Execution policy

- Keep the scaffold aligned with the master workspace contract.
- Maintain runbook, architecture, compliance, and user docs as the project grows.
- Compliance gate is read-only — enforcement lives in the policy gate.
