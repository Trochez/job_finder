# job_finder Dashboard Frontend Plan

**Status:** ready for execution approval
**Created:** 2026-07-29T00:00:00Z
**Target:** frontend dashboard for job_finder application
**Artifact rule:** plan-only; no product code in this file

## Goal

Build dashboard that exposes every needed app param, every app action, and every app state needed run job_finder well. Dashboard must support manual iteration and preserve automatic daily loop.

## Scope

In scope:
- Dashboard UI for settings, run control, loop control, iteration control, status view, audit view.
- One source of truth for editable params and read-only state.
- Persistent run/loop/action model.
- Manual iteration without breaking automatic loop.
- Visibility into discovery, ranking, tailoring, application, pending questions, and Gmail reconciliation.

Out of scope:
- New product capabilities beyond dashboard control surface.
- Distributed architecture.
- Any bypass of CAPTCHA/MFA/auth walls.
- Any hidden automation state not exposed in dashboard.

## Team

**Team size:** 4

### Roles
1. **Planner/Owner** — scope, contracts, backlog, acceptance.
2. **Frontend engineer** — dashboard layout, forms, tables, controls, UX state.
3. **Backend/orchestration engineer** — dashboard API, state machine, persistence, loop control.
4. **QA/automation engineer** — scenario tests, replay tests, runbook, regression checks.

## Design Principles

1. Dashboard first, hidden state last.
2. Editable params must be explicit; read-only values must be labeled.
3. Manual iteration and automatic loop must share same state machine.
4. Every action must persist as audit event.
5. Reload must restore last known run/loop state.

## Required Dashboard Surfaces

- **Settings panel:** all user-editable params.
- **Run control panel:** start, pause, resume, stop, single iteration, auto-loop toggle.
- **Run status panel:** current loop state, current job batch, current step, error/warning state.
- **Workflow timeline:** discovery → rank → tailor → apply → reconcile → pending answers.
- **Applications table:** per-job status, version, submission result, next action.
- **Pending answers panel:** unresolved questions, saved answers, reuse history.
- **Audit log:** every action, state change, and external response.
- **Health panel:** last successful run, scheduler state, queue/manual intervention flags.

## Param Inventory Contract

Planner must freeze exact matrix before build:
- Editable: job titles, locations, remote preference, employment types, daily top-job limit, match threshold, auto-loop on/off, iteration trigger.
- Read-only with rationale: inferred seniority, job discovery results, match scores, selected jobs, submission outcomes, external status evidence, manual intervention flags.

## Atomic Backlog

### Wave 1 — Contracts
1. **Planner:** freeze param matrix and action matrix.
2. **Backend:** define dashboard state machine and run-state transitions.
3. **Backend:** define audit event schema and persistence fields.
4. **QA:** write acceptance scenarios for happy path, edge path, restart/recovery.

### Wave 2 — Data model
5. **Backend:** implement dashboard-facing read model for settings, runs, jobs, actions.
6. **Backend:** persist loop state, manual iteration requests, and action history.
7. **QA:** verify reload restores state from persistence.

### Wave 3 — UI core
8. **Frontend:** build settings editor for all editable params.
9. **Frontend:** build run control bar with start/pause/resume/stop/iterate/auto-loop.
10. **Frontend:** build workflow timeline and current-state summary.
11. **Frontend:** build applications table and pending answers panel.
12. **Frontend:** build audit log and health panel.

### Wave 4 — Orchestration wiring
13. **Backend:** wire UI actions into run-state transitions.
14. **Backend:** wire manual iteration so it uses same pipeline as auto-loop.
15. **Backend:** wire auto-loop scheduler and stop/resume semantics.
16. **Backend:** expose current action availability and guardrails to UI.

### Wave 5 — Verification
17. **QA:** verify every UI action emits audit event.
18. **QA:** verify manual iteration does not disable auto-loop.
19. **QA:** verify stop/pause/resume survive reload.
20. **QA:** run full regression and update runbook/user guide.

## Execution Plan

1. Lock param/action/state contracts first.
2. Build read model and persistence next.
3. Build dashboard UI against frozen contracts.
4. Wire controls to orchestration.
5. Verify state recovery, audit, and loop behavior.

## Acceptance Criteria

- Dashboard shows every editable param and clearly labels read-only data.
- Dashboard can start, pause, resume, stop, and trigger one iteration.
- Automatic loop stays available after manual iteration.
- Every app action appears in dashboard audit log.
- Reload restores last loop/run state.
- Pending answers and submission status remain visible in dashboard.
- No hidden control path required for normal operation.

## Risks

- Mixed manual/automatic control can cause state drift if state machine stays vague.
- Too many dashboard fields can become unusable unless grouped by workflow.
- Restart recovery can fail if audit events and loop state diverge.

## Follow-ups

- Create exact UI wireframe before implementation.
- Create exact state-transition table before code.
- Create test matrix before first UI wiring.

## ADR

**Decision:** single dashboard front end over contract-first orchestration surface.
**Why:** fastest path that keeps control, audit, and recovery in one place.
**Consequences:** tighter coupling upfront, simpler operator workflow.
**Follow-ups:** split later only if scale demands it.
