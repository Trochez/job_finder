# Automated Job Application Platform — Execution Specification

## Metadata

- Profile: standard
- Context: greenfield
- Final ambiguity: 19%; threshold: 20%
- Context snapshot: `.omo/context/automated-job-application-platform-20260728T083031Z.md`
- Interview: `.omo/interviews/automated-job-application-platform-20260728T083139Z.md`

## Goal

Build a dark-themed configurable platform that, daily or on demand, discovers LinkedIn jobs posted in the last 24 hours, ranks them against a user CV, automatically tailors and versions a CV, submits selected applications through browser automation, tracks unresolved questions, and reconciles application status from Gmail.

## Required integrations

- Job discovery: `borgius/jobspy-mcp-server`, constrained to LinkedIn, last 24 hours.
- CV source: Overleaf project, credentials under `.keys/`.
- Gmail status tracking: Composio Gmail OAuth, credentials/configuration under `.keys/`.
- Storage: SQLite.
- Submission: dedicated browser-automation adapter; JobSpy MCP and Composio do not submit applications.

## Functional requirements

### Settings

- Configurable job titles, locations, remote preference, employment types, daily top-job limit, and match threshold.
- Infer seniority from original CV.
- Provide button to run search/rank/apply cycle immediately.
- Provide control to enable or stop scheduled daily execution.

### Discovery, match, and selection

- Query LinkedIn jobs no older than 24 hours using JobSpy MCP.
- Deduplicate jobs and persist discovery data.
- Compute reproducible match percentage against CV/job requirements.
- Rank jobs and select configured top count meeting configurable threshold.

### CV generation

- Retrieve source from Overleaf; preserve original visual style/template.
- Generate a new incremented version per job application.
- Automatically tailor conservatively; never invent education or certifications.
- Preserve audit trail of source, tailored version, job, match score, and changes.

### Application execution

- Submit each selected job immediately after ranking without final approval.
- Cover LinkedIn Easy Apply and external application forms through browser automation.
- Reuse stored candidate answers only when applicable.
- Unknown, ambiguous, missing, CAPTCHA/MFA, consent, or blocked steps become `pending_user_action`; do not bypass safeguards.
- Store event logs, submission timestamp, form URL, state, errors, and evidence where available.

### User workflow and dashboard

- Dark UI displays applied roles, employer, match score, tailored CV version, current status, application date, and event timeline.
- Show pending questions/actions and allow user answers.
- Persist answers for future use; user can edit/delete prior answers.
- Track Gmail messages associated with each application through Composio and derive status with linked message evidence and timestamps.

## Data model minimum

Candidate profile; search configuration; jobs; job snapshots; CV source/versions; match evaluations; applications; question definitions; saved answers; pending actions; automation runs; browser events; Gmail messages; status events; audit logs; encrypted/indirect credential references.

## Security and policy requirements

- `.keys/` excluded from version control, least-privilege file permissions, never exposed by UI/logs.
- OAuth/token rotation and revocation supported.
- No CAPTCHA bypass or circumvention of authentication/consent controls.
- Browser executor must have explicit login/session handling, rate limits, idempotency, kill switch, and manual recovery queue.

## Acceptance criteria

1. Configured run discovers only recent LinkedIn listings, records deduplicated jobs, ranks scores, and selects only qualifying top limit.
2. Every selected application receives a distinct, incremented CV version preserving original template style.
3. Executor submits supported forms automatically; blocked or unknown-answer flows reliably enter pending state without submission.
4. Answering a pending question persists reusable answer and resumes/retries appropriate applications.
5. Dashboard accurately presents applications, dates, pending actions, and status timeline.
6. Gmail reconciliation links relevant messages and updates status with evidence.
7. Scheduler respects start/stop settings; manual cycle works independently.
8. SQLite persists all configured data and audit history; secrets remain confined to `.keys/`.

## Open implementation decisions

- Exact stack, hosting model, auth model, matching algorithm, Overleaf export/compile path, daily schedule/time zone, and per-site browser adapter scope remain implementation decisions.
- Candidate-supplied factual profile must define which experience claims besides education/certifications are permitted; absent facts always require confirmation.
