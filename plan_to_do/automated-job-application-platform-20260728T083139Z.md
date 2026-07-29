# Automated Job Application Platform — Consensus Implementation Plan

**Status:** Ready for explicit execution approval  
**Created:** 2026-07-28T08:31:39Z  
**Source spec:** `.omo/specs/deep-interview-automated-job-application-platform.md`  
**Interview:** `.omo/interviews/automated-job-application-platform-20260728T083139Z.md`  
**Context:** Greenfield workspace; current files are OpenCode tooling only.  
**Plan mode:** No product code changed.

## RALPLAN-DR summary

### Principles

1. **Safe automation:** never bypass CAPTCHA, MFA, consent, authentication, rate limits, or blocked flows; queue manual action.
2. **Contract-first:** domain state machines and provider interfaces precede external integrations, preventing vendor coupling.
3. **Auditability:** every discovery, score, CV version, answer, submission, status update, and failure is persisted with evidence.
4. **Determinism:** match scoring, deduplication, idempotency, retries, and version numbering produce reproducible outcomes.
5. **Recoverability:** kill switch, resumable runs, pending actions, append-only events, and dry-run mode protect user control.

### Decision drivers

- Submission mistakes are high-impact and irreversible.
- JobSpy MCP and Composio provide discovery/status inputs, not application submission.
- User requires immediate auto-submit, but unknown factual answers must pause.

### Viable options

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Contract-first modular monolith + SQLite + browser adapter | Small deployment, clear boundaries, fast MVP, easy local audit | Browser worker remains operationally complex | **Choose** |
| Distributed services + queue/database cluster | Independent scaling, stronger isolation | Excessive deployment/ops cost for single-user greenfield MVP | Reject |
| Manual application assistant | Lowest automation risk | Fails explicit immediate auto-submit requirement | Reject |

## Target architecture

One repository with strict modules:

```text
frontend dashboard/settings
        ↓ typed HTTP API
application service + state machines
        ↓ repositories / event log
SQLite migrations
        ↓ provider ports
JobSpy MCP | Overleaf | browser executor | Composio Gmail
        ↑ scheduler + manual run controller
```

Use typed contracts at module boundaries. Keep provider-specific payloads out of domain tables. Store secret references, never secret values, in SQLite. `.keys/` remains local-only and excluded from version control.

### Required state machines

- `automation_run`: `idle → running → stopping → stopped|completed|failed`.
- `application`: `selected → preparing → ready_to_submit → submitted|pending_user_action|blocked|failed`; pending may resume after answer/manual intervention.
- `status`: append-only source events; derive current status with confidence and evidence links.

## Team staffing

**Team size: 8 implementation agents plus 1 lead coordinator (9 total seats).** Lead owns integration sequencing and release gate; agents own assigned atomic tasks and tests.

| Role | Count | Primary ownership | Lane |
|---|---:|---|---|
| Lead architect/coordinator | 1 | ADR, contracts, dependency graph, integration, release gate | `ultrabrain` / `oracle` |
| Backend/data engineer | 1 | API, SQLite, migrations, state transitions, audit | `deep` |
| Integrations engineer | 1 | JobSpy MCP, Overleaf, Composio ports/adapters | `deep` |
| CV/matching engineer | 1 | source parsing, conservative tailoring, versions, score | `deep` |
| Browser automation engineer | 1 | Easy Apply/external executor, safety gates, idempotency | `deep` |
| Frontend engineer | 1 | dark dashboard, settings, pending workflow | `visual-engineering` |
| Security/reliability engineer | 1 | secrets, threat model, kill switch, observability, failure injection | `ultrabrain` |
| QA/e2e engineer | 1 | contract/integration/browser fixture/e2e/accessibility tests | `deep` |

If `$ralph` runs sequentially, retain same roles as backlog lanes. If `$team` runs parallel, lead creates shared contracts first, then releases dependent batches in listed order.

## Atomic backlog

Each item has one owner, one deliverable, and completion evidence. No item starts before listed dependencies pass.

### Batch 0 — topology, safety, contracts

- **A01 — Lead — `docs/adr/001-stack-and-boundaries.md`**: choose typed backend/frontend stack, monolith boundary, test tools, and local deployment; expect approved ADR with rejected alternatives.
- **A02 — Security — `docs/security/threat-model.md`**: model `.keys/`, OAuth, browser sessions, PII, CV data, Gmail data, logs, and irreversible submission; expect threats, mitigations, residual risks.
- **A03 — Lead — `src/domain/contracts`**: define typed Job, Candidate, SearchConfig, MatchResult, CVVersion, Application, Question, Answer, StatusEvent, Run, and AuditEvent schemas; expect compile-time contract tests.
- **A04 — Lead — `src/domain/state-machines`**: define legal run/application/status transitions and idempotency keys; expect transition tests rejecting illegal moves.
- **A05 — QA — `tests/fixtures/providers`**: create deterministic JobSpy, Overleaf, browser, and Gmail fixtures including duplicate, stale, malformed, blocked, and pending cases; expect reusable offline fixtures.

### Batch 1 — skeleton, secrets, persistence

- **B01 — Backend — `src/config`**: load validated non-secret settings and secret references from `.keys/`; expect startup failure for missing/unsafe config and no secret logging.
- **B02 — Backend — `db/migrations/001_initial`**: create SQLite tables for settings, jobs, snapshots, CV artifacts, matches, applications, questions, answers, runs, provider messages, status events, audit events; expect clean migration and rollback/checksum tests.
- **B03 — Backend — `src/repositories`**: implement typed repositories and transaction boundaries; expect CRUD/constraint tests and idempotent upserts.
- **B04 — Backend — `src/services/audit`**: append immutable audit events with correlation IDs and redaction; expect event ordering and redaction tests.
- **B05 — QA — `tests/migrations`**: test fresh install, restart, duplicate migration, and representative schema upgrade; expect repeatable database verification.

### Batch 2 — discovery and ranking

- **C01 — Integrations — `src/providers/jobspy`**: implement MCP client port and LinkedIn query mapping; expect normalized fixture output and provider error mapping.
- **C02 — Integrations — `src/services/discovery`**: enforce `hours_old=24`, local timestamp normalization, source retention, and deduplication key; expect stale/duplicate tests.
- **C03 — Backend — `src/services/search-config`**: persist configurable titles, locations, residence, remote preference, employment types, daily limit, threshold; expect validation/API tests.
- **C04 — CV/matching — `src/matching/score`**: implement documented deterministic match percentage from verified CV/job facts; expect explanation components and boundary tests.
- **C05 — CV/matching — `src/matching/rank`**: sort stable by score, recency, deterministic tie-break; enforce threshold/top-N; expect reproducible ranking tests.

### Batch 3 — Overleaf and CV versions

- **D01 — Integrations — `src/providers/overleaf`**: retrieve configured project using `.keys/` credentials and cache source metadata; expect mocked auth/error tests.
- **D02 — CV/matching — `src/cv/parser`**: parse source into verified facts while preserving template/style metadata; expect fixture parse tests.
- **D03 — CV/matching — `src/cv/tailor`**: rewrite/reorder only verified facts, forbid invented education/certifications, emit change set; expect negative claim tests.
- **D04 — CV/matching — `src/cv/versioning`**: create incremented per-application versions, compile/export PDF with source linkage; expect unique version and artifact tests.
- **D05 — QA — `tests/cv/golden`**: compare generated artifact layout/style against golden CV fixtures; expect visual/style regression report.

### Batch 4 — application executor and pending answers

- **E01 — Browser — `src/providers/browser`**: define browser executor port, session lifecycle, bounded retries, evidence capture, and kill switch; expect fake-browser contract tests.
- **E02 — Browser — `src/application/form-classifier`**: classify Easy Apply, external form, unknown, blocked, CAPTCHA, MFA, and consent states; expect fixture classification tests.
- **E03 — Browser — `src/application/submit`**: submit selected jobs immediately, enforce idempotency and application state transitions; expect duplicate-run and retry tests.
- **E04 — Backend — `src/answers/vault`**: store versioned user-approved answers with sensitivity, scope, edit/delete, and reuse matching; expect no-answer and stale-answer tests.
- **E05 — Browser — `src/application/pending`**: pause unknown factual questions and blocked flows without unsafe submission; expect resume/manual queue tests.
- **E06 — Frontend — `src/features/pending-actions`**: show question, job, context, and answer form; expect answer persistence and resume API tests.

### Batch 5 — orchestration and scheduler

- **F01 — Backend — `src/services/application-cycle`**: orchestrate discover → rank → tailor → submit, transactionally record each step; expect end-to-end service test with fixtures.
- **F02 — Backend — `src/scheduler`**: schedule daily runs with timezone/config persistence; expect due/not-due and restart recovery tests.
- **F03 — Backend — `src/run-control`**: implement manual run button endpoint, stop endpoint, kill switch, and resumable stopping; expect concurrency/stop tests.
- **F04 — QA — `tests/failure-injection/cycle`**: inject provider timeout, malformed job, compile failure, browser block, DB restart; expect safe terminal/pending states and audit events.

### Batch 6 — Gmail reconciliation

- **G01 — Integrations — `src/providers/composio-gmail`**: implement OAuth/tool port and message retrieval with redaction; expect mocked token/error tests.
- **G02 — Integrations — `src/status/correlation`**: correlate messages to applications using stable identifiers, employer/title/date evidence; expect false-positive rejection tests.
- **G03 — Backend — `src/status/reconcile`**: parse supported status signals, append evidence events, derive current status/confidence; expect ordering/conflict tests.
- **G04 — QA — `tests/gmail/reconciliation`**: test matching inbox, unrelated inbox, duplicate message, ambiguous status, and revoked OAuth; expect integration report.

### Batch 7 — frontend and API surface

- **H01 — Frontend — `src/features/applications`**: display role, employer, score, CV version, status, date, and timeline; expect loading/error/empty states.
- **H02 — Frontend — `src/features/settings`**: edit search fields, daily top-N, threshold, schedule, residence, and remote policy; expect validation and save feedback.
- **H03 — Frontend — `src/features/run-control`**: add search-rank-apply and stop controls with run progress; expect disabled/in-progress/failed states.
- **H04 — Frontend — `src/theme`**: implement dark theme, keyboard navigation, focus states, contrast, responsive layout; expect accessibility checks.
- **H05 — Backend — `src/api`**: expose typed endpoints for settings, runs, applications, pending actions, answers, status timeline, and artifacts; expect API contract tests.

### Batch 8 — verification and release

- **I01 — QA — `tests/e2e/search-to-status`**: run fixture flow discovery → ranking → CV → submission/pending → Gmail status → dashboard; expect reproducible full-path pass.
- **I02 — QA — `tests/browser`**: run Easy Apply/external form fixture scenarios, blocked/CAPTCHA/MFA, duplicate retry, stop, and resume; expect no bypass and no duplicate submission.
- **I03 — Security — `tests/security`**: verify secret redaction, `.keys/` permissions/ignore, OAuth handling, CSRF/auth boundaries, PII access, and audit integrity; expect zero critical findings.
- **I04 — Security — `src/observability`**: add structured redacted logs, metrics, run/application counters, provider latency/error metrics, and alerts; expect observability assertions.
- **I05 — Lead — `docs/runbook`**: document local setup, credential provisioning, dry-run, scheduled stop, pending recovery, backup, migration, revoke-token, and incident response; expect operator walkthrough.
- **I06 — Lead + QA — `release`**: execute dry-run gate, migration backup/restore, accessibility scan, test suite, and manual production-readiness checklist; expect signed release decision.

## Dependency and assignment map

| Batch | Can parallelize after | Owners |
|---|---|---|
| 0 | none | Lead, Security, QA |
| 1 | A01–A05 | Backend, QA, Security |
| 2 | B01–B05 | Integrations, Backend, CV, QA |
| 3 | A03, B01–B04 | Integrations, CV, QA |
| 4 | A04, B01–B04, C02 | Browser, Backend, Frontend |
| 5 | C01–C05, D01–D04, E01–E05 | Backend, QA |
| 6 | B03, A03, C02 | Integrations, Backend, QA |
| 7 | B03, A03, F01, E06, G03 | Frontend, Backend |
| 8 | all feature batches | QA, Security, Lead |

Lead merges only passing contract tests. Team members may work concurrently within batch; cross-batch work waits for dependency evidence.

## Test and verification matrix

### Unit

- Schema validation; state transitions; stale filter; deduplication; score explanation; stable rank; CV claim prohibition; version increment; answer reuse; idempotency; status parsing.

### Integration

- JobSpy MCP fixture → SQLite; Overleaf fixture → source/artifact; Composio fixture → correlated status; browser fake → application state machine; scheduler → run control.

### End-to-end

- Manual run and scheduled run full path.
- Top-N/threshold enforcement.
- Easy Apply and external form successful fixtures.
- Pending factual question answer → resume.
- CAPTCHA/MFA/block → manual queue.
- Gmail email → evidence-backed status timeline.
- Stop during each orchestration stage → safe recovery.

### Observability

- Every run/application has correlation ID.
- Audit contains state transition, actor, provider, timestamp, redacted reason.
- Metrics cover discovery count, selected count, submitted count, pending count, blocked count, Gmail correlation count, latency, and errors.
- Alerts fire on repeated provider failures, duplicate-attempt prevention, token failure, and kill-switch activation.

## Pre-mortem

1. **Duplicate or unintended applications:** retries lose idempotency. Mitigation: unique `(job_id, candidate_id)` key, persisted submission intent, browser evidence, duplicate fixture tests, kill switch.
2. **False CV claims or wrong answers:** model fills unsupported facts. Mitigation: verified-fact whitelist, education/certification hard blocks, pending queue, answer provenance, negative tests.
3. **Provider/site drift:** MCP fields, Gmail formats, or browser selectors change. Mitigation: ports/adapters, contract fixtures, versioned provider mappings, health checks, blocked/manual queue, no bypass.

## ADR

**Decision:** Use contract-first modular monolith with SQLite and separate provider adapters; execute browser automation only behind safety state machine.  
**Drivers:** single-user greenfield speed, auditability, vendor isolation, immediate auto-submit requirement.  
**Alternatives:** distributed services (rejected operational overhead); manual assistant (rejected requirement mismatch); direct vendor coupling (rejected testability and migration cost).  
**Consequences:** simpler deployment and strong local audit; browser automation remains fragile and needs ongoing selector/fixture maintenance.  
**Follow-ups:** select concrete stack in A01; confirm browser provider/session deployment; define supported status vocabulary; define backup/retention policy.

## Available agents and launch guidance

- `oracle`: architecture/security consultation; use for ADR, threat model, hard state-machine disputes.
- `explore`: codebase/path discovery; use before touching unfamiliar existing files.
- `librarian`: external integration documentation and provider contract verification.
- `momus`: final plan/diff review.
- `deep`: multi-file feature implementation with tests.
- `visual-engineering`: dashboard/theme/accessibility implementation.
- `quick`: isolated mechanical tasks only.

### `$team` launch

Launch 8 workers after lead completes Batch 0. Assign lanes exactly by staffing table. Keep Browser and Security isolated from credential sharing. Merge by batch; QA owns gate evidence. Suggested parallel first wave: Backend B01–B05, Integrations C01, CV C04, Security threat tests, QA fixtures. Do not launch submission automation before E01–E05 safety tests pass.

### `$ralph` launch

Run backlog A01→I06 sequentially, preserving batch dependencies. Stop on failed contract, migration, security, or idempotency gate. Use QA I01–I04 as mandatory final loop; no production auto-submit until I06 release decision.

## Definition of done

- All A01–I06 deliverables complete.
- Unit, integration, browser fixture, e2e, accessibility, security, migration, and observability checks pass.
- Dry-run demonstrates ranking, versioning, pending handling, stop/resume, Gmail evidence, and no duplicate submission.
- Secrets remain outside source/database/logs.
- Runbook and rollback/revocation steps tested.
- Lead and QA sign release gate.
