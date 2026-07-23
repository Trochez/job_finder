# MCP Supply Chain — Dependency Verification

## Purpose

Document the pinned-dependency manifest, checksum verification, and
allowed-tool-surface contract for all MCP servers used by job_finder.
This ensures reproducible builds and auditability of the MCP supply chain.

## Principle

**No `@latest` references.**  Every MCP server dependency is pinned to a
specific commit SHA and semver tag.  Upgrades are an explicit operator action
with a review step.

## Pinned dependency manifest

Each MCP server used by the project must have an entry in the supply-chain
manifest.  The manifest is validated by
`tests/contract/test_mcp_supply_chain.py`.

```yaml
# .omo/mcp-supply-chain.yaml
servers:
  - name: linkedin-mcp
    repository: stickerdaniel/linkedin-mcp-server
    pinned_commit: abc123def456789abc123def456789abc123def456
    pinned_tag: v0.1.2
    checksum_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    allowed_tools:
      - searchJobs
    allowed_operations:
      - search
    data_classification: public_job_listing_metadata
    review_date: 2026-07-22
    review_expiry_days: 90
```

## Checksum verification

The `checksum_sha256` field is a SHA-256 hash of the server's source at the
pinned commit.  Verification steps:

1. `git clone --depth 1 <repo>`
2. `git checkout <pinned_commit>`
3. `git archive HEAD | sha256sum`
4. Compare result against manifest entry.

The contract test `test_pinned_server_checksum_matches` performs this
verification when run in an environment with network access.  In air-gapped
mode it verifies only that the manifest entry is well-formed.

## Allowed-tool-surface contract

The `allowed_tools` list defines the exact MCP tool surface the project is
permitted to call.  Any tool not on this list is blocked by the compliance
gate.  Rationale:

- **Minimal surface:** reduces blast radius if a server is compromised.
- **Audit trail:** every tool addition is a version-controlled change.
- **Review requirement:** tool-surface changes require a new access-basis record.

## Upgrade process

1. Operator reviews the new server version's changelog and diff.
2. New `pinned_commit`, `pinned_tag`, and `checksum_sha256` are computed.
3. Access-basis record is reviewed and signed (see `linkedin-access-basis.md`).
4. Supply-chain manifest is updated.
5. Contract tests run to verify the new pin.
6. Compliance gate validates the new record before any data flows.

## No automatic upgrade

Supply-chain verification is a **read-only check**.  The tests and compliance
gate validate integrity but never modify the manifest, never pull new
versions, and never enable live access.
