# job_finder User Guide

End-user workflow for job seekers. Dashboard at `http://127.0.0.1:8000`.

## Quick Start

```bash
cd /home/trocha/projects/job_finder
uv run python -m job_finder.web.app
# Open browser → http://127.0.0.1:8000
```

## Step 1: Profile Settings — `/profile-settings`

Configure candidate profile and job search preferences.

**Timezone**: IANA timezone dropdown (e.g. `America/Bogota`). Used for daily cap tracking window.

**Hard Filters**: Checkboxes — jobs matching ANY filter marked ineligible:
- No Remote Work
- Contract/Freelance Only
- Startup Only (< 50 employees)
- Requires Relocation
- Below Minimum Salary Band
- Visa Sponsorship Required

**Score Threshold** (0-100): Minimum weighted score for eligibility. Default 50. Job must score >= threshold.

**Daily Cap** (0-100): Max automated applications per day. Default 10. 0 = unlimited.

Click **Save Settings**.

## Step 2: CV Source — `/cv-source`

Select candidate fact-base version and renderer configuration.

**Active Profile Version**: Dropdown of imported CV fact-base versions. Determines which provenanced claims used for scoring.

**Renderer Type**: Select `local` (filesystem renderer) or `overleaf` (Git-based Overleaf fetch).

- **Local Renderer Path**: Filesystem path to CV renderer executable/script (used when type is `local`). Generates tailored CV variants per job application.
- **Overleaf Project ID**: 24-character hex string found in the Overleaf project URL: `https://www.overleaf.com/project/<24-char-hex-id>`.
- **Overleaf Git Token**: Generate at Overleaf Account Settings → Git Tokens. Token is stored in a `0o600` file on the filesystem — never in the database or environment variables. Refer to `PrivateSettings` for path configuration.
- **Renderer type** must match the configured source in `PrivateSettings` — `local` uses `LocalOverleafRenderer`, `overleaf` uses `OverleafGitRenderer`.

Click **Save CV Source**.

## Step 3: Dashboard — `/dashboard`

Main overview with stat cards:

| Card | Meaning |
|------|---------|
| Total Jobs Scored | All jobs processed in current run window |
| Eligible | Jobs passing threshold + hard filters |
| Submitted | Application attempts made |
| Pending Review | Jobs needing human decision |
| Active Checkpoints | Paused workflows (CAPTCHA, screening questions) |
| Today's Applications/N | Daily count vs configured cap |

Quick actions: Review Jobs, Manage Checkpoints, Profile Settings.

Empty state shown when no data — links to Profile Settings and CV Source.

## Step 4: Job Review — `/jobs`

Table of scored jobs. Each row shows:

| Column | Value |
|--------|-------|
| Company | Job poster name |
| Title | Job title |
| Score | 0-100 weighted (green ≥70, yellow ≥40, red <40) |
| Eligibility | Eligible / Hard Filter / Ineligible / Threshold Unset |
| Factors | Badge tags (skills, experience, culture, location, growth) |
| Route | Automated / Review / External ATS / Unsupported |
| Cap Status | Open (can apply) / Capped (daily limit hit) |

Score factor weights: 30% skills, 30% experience, 25% culture fit, 10% location, 5% growth.

## Step 5: Audit Trail — `/audit`

Full evaluation history. Per job record:
- Applied score threshold
- Scoring policy version
- Factor breakdown with evidence references
- CV artifact reference
- Decision timestamp
- Route classification + execution access state

Data auto-purges at 90 days. Only non-content tombstone hash remains for deduplication.

## Step 6: Checkpoints & Resume — `/checkpoints`

When automated workflow blocks on:
- Unknown screening question
- CAPTCHA challenge
- 2FA / login challenge
- Anti-automation trigger

Each checkpoint shows block reason and pause state.

Controls:
- **Resume**: Provide exact matching answer to continue
- **Cancel**: Abort that job path

**Kill Switch** toggle at top:
- ON: Cancels all active workflow, blocks new runs
- Must manually clear to resume

## Daily Automation (optional systemd timer)

```bash
cp deploy/systemd/job-finder.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now job-finder.timer
```

Each timer run:
1. Opens 24h window since last successful watermark
2. Catches up one missed cycle if timer was off
3. Fetches jobs via MCP adapter (fake-only by default)
4. Scores, filters, ranks
5. Checks daily cap
6. Pauses at blocking challenges
7. Sends Telegram notification (status + score only — all other fields redacted)

## Current Limitations

- Dashboard routes return placeholder/sampled data — not yet wired to `SqliteWorkflowRepository`
- Settings stored in memory only (`InMemorySettingsProvider`), lost on restart
- LinkedIn MCP behind default-deny policy gate — no live calls
- Telegram notifier is `_NullNotifier` placeholder
- Port 8000, host 127.0.0.1 hardcoded in `app.py`
