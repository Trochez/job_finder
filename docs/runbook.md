# job_finder Operator Runbook

## Fake-mode startup

The default configuration runs in **fake mode** — all MCP calls use the
in-memory `FakeMCPJobSource` adapter.  No network access, no LinkedIn auth.

```bash
# From project root
uv run python -m job_finder.main
```

Expected output:

```
Job finder started (fake mode)
Run watermark at 2026-01-02T03:04:05+00:00
0 jobs discovered, 0 eligible
```

To run a single discovery cycle:

```bash
uv run python -m job_finder.main --run-once
```

## systemd-user timer

For periodic execution, install the user timer:

```bash
mkdir -p ~/.config/systemd/user/
cp deploy/job-finder.service ~/.config/systemd/user/
cp deploy/job-finder.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now job-finder.timer
```

The timer runs job_finder every 4 hours.  Logs:

```bash
journalctl --user -u job-finder.service -n 50 --follow
```

## Watermark recovery

If a run cycle fails mid-way (e.g. process killed), the watermark may be
stale.  To reset:

```bash
# Check current watermark
sqlite3 ~/.local/share/job_finder/jobs.db \
  "SELECT * FROM run_watermarks ORDER BY updated_at DESC LIMIT 1;"

# Delete the stuck watermark to allow a new run
sqlite3 ~/.local/share/job_finder/jobs.db \
  "DELETE FROM run_watermarks WHERE candidate_profile_id = '<id>';"
```

The `ConcurrentRunError` guard in `run_cycle.py` prevents overlapping runs.
After watermark deletion the next cycle proceeds normally.

## Rollback

To roll back to a previous build:

```bash
# Identify the git tag or commit to roll back to
git log --oneline -10

# Hard reset (discards uncommitted changes — backup first)
git reset --hard <target-commit>

# Reinstall dependencies
uv sync

# Verify
uv run pytest -q
```

## Evidence location

Task-completion evidence is stored in `.omo/evidence/` at the project root.
Each evidence file follows this naming convention:

```
task-<task-number>-<brief-description>.md
```

The format is:

```markdown
# Task N Evidence

## Scope

Brief description.

## Files

- List of files created or modified.

## Red

- Command and expected failure before implementation.

## Green

- Command and pass result after implementation.

## Final verification snapshot

- Test count and status.
```

Current evidence files:

- `task-1-job-finder-mcp-implementation.md` — bootstrap scaffold.
- `task-25-linkedin-access-basis-compliance.md` — written access basis docs.
- `task-26-mcp-supply-chain-docs.md` — MCP supply chain documentation.
- `task-30A-compliance-gate-implementation.md` — compliance gate code + tests.
- `task-30B-architecture-runbook-docs.md` — architecture and runbook docs.

## Manual live-enable preconditions

Live MCP access is **never** enabled automatically.  The following
preconditions must be met before enabling:

1. **Compliance record valid.**  Run `uv run pytest tests/contract/test_compliance_enablement.py -v`
   and verify all tests pass.
2. **Supply chain verified.**  Run `uv run pytest tests/contract/test_mcp_supply_chain.py -v`
   and verify all tests pass.
3. **Access basis signed.**  The access-basis record in
   `docs/compliance/linkedin-access-basis.md` must have a `review_date` within
   the `retention_days` window.
4. **Operator override.**  The operator must edit `policy.py` to change the
   `create_job_source()` server-name check or update `linkedin_client.py` to
   accept a non-fake server name.

**No test or code path automatically enables live access.**  The override is
always an explicit operator action.

## Configuration

All configuration is in `pyproject.toml` under `[tool.job_finder]` (future) or
passed as CLI arguments.  Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_FINDER_DB_PATH` | `~/.local/share/job_finder/jobs.db` | SQLite database path |
| `JOB_FINDER_LOG_LEVEL` | `INFO` | Python logging level |
| `JOB_FINDER_FAKE_MODE` | `true` | Force fake MCP adapter |

## Health check

```bash
uv run python -m job_finder.health
```

Returns exit code 0 if the database is reachable and schema is current.
