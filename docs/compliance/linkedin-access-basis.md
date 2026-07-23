# LinkedIn Access Basis — Compliance Record

## Purpose

Formal written-access-basis record for the `stickerdaniel/linkedin-mcp-server`
tool surface.  The compliance gate validates every MCP invocation against this
record before any data touches a downstream use case.

## Access basis record template

```yaml
access_basis_id: "linkedin-mcp-v1"
mcp_server: "stickerdaniel/linkedin-mcp-server"
pinned_commit: "abc123def456789abc123def456789abc123def456"
pinned_tag: "v0.1.2"
review_date: "2026-07-22"
reviewer: "operator-name"
written_permitted_access_basis: |
  The operator reviewed the linkedin-mcp-server source pinned at commit
  abc123def4 and confirmed that:
    - searchJobs searches LinkedIn job listings via public-search surface.
    - No write operations (apply, message, comment) are enabled.
    - No candidate PII is exfiltrated beyond job listing metadata.
permitted_operations: ["searchJobs"]
retention_days: 90
data_classification: "public_job_listing_metadata"
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `access_basis_id` | yes | Unique identifier for this access record |
| `mcp_server` | yes | GitHub repo path of the MCP server |
| `pinned_commit` | yes | Full SHA commit hash the review was based on |
| `pinned_tag` | yes | Semver tag matching the pinned commit |
| `review_date` | yes | ISO-8601 date of the last human review |
| `reviewer` | yes | Identity of the person who performed the review |
| `written_permitted_access_basis` | yes | Narrative justification of why access is permitted |
| `permitted_operations` | yes | List of MCP tool names allowed after review |
| `retention_days` | yes | Data retention window in days |
| `data_classification` | yes | Classification label for the data accessed |

## Validation rules

1. **pinned_commit** must be a 40-character hex SHA.
2. **pinned_tag** must match `v` + semver pattern.
3. **review_date** must not be in the future.
4. **reviewer** must not be blank.
5. **written_permitted_access_basis** must be at least 100 characters.
6. **permitted_operations** must have at least one entry.
7. Each entry in **permitted_operations** must be a known MCP tool name.
8. **retention_days** must be a positive integer.
9. **data_classification** must be one of the known classification labels.

See `src/job_finder/application/compliance_gate.py` for the programmatic
validation implementation.

## Known data classifications

- `public_job_listing_metadata` — title, company, location, apply URL,
  description excerpt
- `candidate_profile` — CV facts, skills, experience
- `audit_log` — workflow transition events
- `internal_configuration` — scoring weights, retention policies

## Access renewal

The access basis record must be reviewed and re-signed every 90 days.
When the MCP server is upgraded (new commit hash), a new record must be
created and the old one archived.  The compliance gate rejects any record
whose `review_date` is older than `retention_days`.

## No automatic enablement

This document is a **validation record only**.  The compliance gate inspects
records and reports validity; it **never auto-enables** live access.  Live
enablement is a separate operator action documented in
`docs/runbook.md#live-enable-preconditions`.
