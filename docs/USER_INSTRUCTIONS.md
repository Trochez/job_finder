# job_finder Dashboard Quickstart

## 1. Start
```bash
cd /home/trocha/projects/job_finder
uv run python -m job_finder.web.app
```
Dashboard: http://127.0.0.1:8000

## 2. Profile Settings First
Visit `/profile-settings`:
- Set timezone (e.g., America/Bogota)
- Set hard filters (remote, contract, etc.)
- Set score threshold (default 50)
- Set daily cap (default 10)
- Click **Save Settings**

## 3. CV Source Second
Visit `/cv-source`:
- Select renderer type: `local` or `overleaf`
- For Overleaf: enter 24‑hex project ID and ensure token file is configured (see docs/overleaf.md)
- Click **Save CV Source**

## 4. Daily Cycle Behavior
- The dashboard triggers a discovery cycle on load (or via systemd timer).
- Jobs are scored, filtered by threshold/hard filters, and ranked.
- Eligible jobs appear in `/jobs` with route classification.
- Daily cap limits automated applications; excess jobs stay pending.

## 5. Fake‑Mode Default & Live MCP
- Default: fake mode (no network, in‑memory MCP).
- Live MCP (e.g., LinkedIn) requires explicit operator override after compliance:
  1. Pass compliance tests: `uv run pytest tests/contract/test_compliance_enablement.py -v`
  2. Verify supply chain: `uv run pytest tests/contract/test_mcp_supply_chain.py -v`
  3. Ensure access‑basis record in `docs/compliance/linkedin-access-basis.md` is within retention.
  4. Edit `policy.py` or `linkedin_client.py` to enable live server.
- No automatic live enable.

## 6. Checkpoint Handling
When automation blocks (CAPTCHA, 2FA, unknown question):
- Visit `/checkpoints` to see paused workflows.
- **Resume**: provide exact matching answer.
- **Cancel**: abort that job path.
- **Kill Switch** (top toggle) stops all active workflows; must be cleared manually.

## 7. Evidence & Session Learnings
- Task evidence: `.omo/evidence/` (files `task-*.md`).
- Session learnings: `SESSION_LEARNINGS.md` (project root).
- Refer to these for implementation details and verification.

---