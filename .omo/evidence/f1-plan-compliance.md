# F1 — Plan and Spec Compliance Audit

## Auditor

M5 + Momus — trace every must-have and must-not-have to code, tests, and evidence.

## Verification commands

```bash
uv run pytest -q && uv run pytest -m e2e -q
```

## Results

- `uv run pytest -q` → 286 passed (all unit/integration/contract/security)
- `uv run pytest -m e2e -q` → 23 passed (8 E2E + 15 Playwright)

## Compliance trace (must-haves)

| Must-have | Evidence | Status |
|-----------|----------|--------|
| Private single-user Python/FastAPI/SQLite service | `pyproject.toml`, `src/job_finder/web/app.py` | ✅ |
| Typed domain contracts (branded IDs, states, errors) | `src/job_finder/domain/{ids,states,errors}.py` | ✅ |
| Structured CV fact-base with source provenance | `src/job_finder/domain/candidate.py`, tests | ✅ |
| 30/30/25/10/5 weighted scoring with version | `src/job_finder/domain/{scoring,scoring_policy}.py` | ✅ |
| Hard-filter gating, threshold, deterministic ranking | `src/job_finder/domain/eligibility.py` | ✅ |
| Requested MCP typed port with fake test double | `src/job_finder/adapters/mcp/{port,fake,policy}.py` | ✅ |
| Default-deny policy gate | `src/job_finder/adapters/mcp/policy.py` | ✅ |
| Durable run model (24h windows, catch-up) | `src/job_finder/application/run_cycle.py` | ✅ |
| Workflow transitions, kill switch, checkpoint pauses | `src/job_finder/application/{workflow,checkpoints}.py` | ✅ |
| Daily-cap enforcement (default 25) | `src/job_finder/application/daily_cap.py` | ✅ |
| Canonical job identity and idempotent dedupe | `src/job_finder/domain/job_identity.py` | ✅ |
| Append-only audit + 90-day purge with tombstones | `src/job_finder/{domain,adapters,application}/...` | ✅ |
| Telegram allowlist (status+score only) | `src/job_finder/adapters/notifications/telegram.py` | ✅ |
| Compliance gate (validates but never enables) | `src/job_finder/application/compliance_gate.py` | ✅ |
| MCP supply-chain pin verification | `docs/compliance/mcp-supply-chain.md` | ✅ |
| FastAPI dashboard with Jinja2 templates | `src/job_finder/web/{app,routes,templates}/` | ✅ |
| systemd-user timer | `deploy/systemd/` | ✅ |
| TDD evidence files | `.omo/evidence/` (28 files) | ✅ |

## Compliance trace (must-not-haves)

| Must-not-have | Verification | Status |
|---------------|-------------|--------|
| No live MCP/LinkedIn calls | `test_live_mcp_adapter_denied` in security suite | ✅ |
| No scraping/browser automation | All tests use fakes; Playwright only for dashboard QA | ✅ |
| No CAPTCHA/bypass | Checkpoint tests enforce pause-only | ✅ |
| No credentials in source/code | No `.keys`, `sk-`, `ghp_` in source files | ✅ |
| No multi-user/RBAC | Single-user FastAPI app | ✅ |
| No @latest / unpinned MCP | Pin verification in supply-chain docs | ✅ |
| No unsupported score inference | All scores use deterministic engine | ✅ |
| No hidden hard-filter/checkpoint failure | Audit trail records every decision | ✅ |

## Verdict

**APPROVED** — All must-haves implemented and verified. All must-not-haves confirmed absent.
