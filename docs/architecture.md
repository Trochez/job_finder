# job_finder Architecture

## Overview

job_finder is a private single-user job-finding service.  It discovers job
listings via MCP sources, evaluates them against a candidate profile, scores
fit, and routes eligible applications.

## Package layout

```
src/job_finder/
  domain/           # Pure domain logic — no I/O, no side effects
    candidate.py
    eligibility.py
    errors.py
    ids.py
    job_identity.py
    scoring.py
    scoring_policy.py
    states.py
  application/      # Use cases — orchestrate domain + adapters
    candidate_import.py
    checkpoints.py
    compliance_gate.py   # Wave 5 — written-access-basis validation
    daily_cap.py
    job_intake.py
    retention.py
    run_cycle.py
    submission_routes.py
    workflow.py
  adapters/
    cv_renderer/    # CV rendering port + LaTeX adapter
    mcp/            # MCP job-source port + fake + LinkedIn mock
    repositories/   # SQLite persistence
    telegram/       # Telegram notification adapter
```

## Layer rules

- **domain/** imports nothing from `application/` or `adapters/`.
- **application/** imports from `domain/` and ports defined in `adapters//*/port.py`.
- **adapters/** implement ports but never import `application/` use-case modules.

## Scoring governance

Scoring is governed by `src/job_finder/domain/scoring_policy.py`.  The current
policy (`2026-07-fixed-30-30-25-10-5`) assigns fixed percentage weights to
five factors:

| Factor | Weight |
|--------|--------|
| role_alignment | 30 |
| skills_tools | 30 |
| experience_seniority | 25 |
| domain_relevance | 10 |
| preferred_qualifications | 5 |

The policy is immutable at runtime.  A new policy version requires:

1. A new `ScoringPolicyVersion` constant.
2. A new set of `_CURRENT_FACTOR_WEIGHTS`.
3. An update to `CURRENT_SCORING_POLICY`.
4. Passing contract tests.

The validator in `ScoringPolicy.__post_init__` rejects any change to the
current version's weights — a new version string is required before new
weights take effect (protecting against silent semantic drift).

## Compliance boundaries

Wave 5 introduces a compliance gate (`application/compliance_gate.py`) that
validates:

- **Written access basis:** MCP commit hash, review date, permitted ops,
  retention constraints, approver identity.
- **MCP supply chain:** pinned dependency manifest, checksum surface,
  allowed-tool-surface contract.

The gate is a **validator, not an enforcer**.  It answers "is this record
valid?" but does not block or permit any execution path.  Enforcement happens
at the `policy.py` gate in `adapters/mcp/`.

## ADRs

### ADR-001: src/ layout

**Context:** Python projects commonly use flat or `src/` layout.
**Decision:** `src/` layout to prevent accidental import of test or config
code from distribution packages.
**Consequences:** `pyproject.toml` uses `src/` as the package root.
`tests/conftest.py` appends `src/` to `sys.path`.

### ADR-002: No ORM, raw sqlite3

**Context:** The data model is small and tightly controlled.
**Decision:** Use stdlib `sqlite3` with hand-written SQL.  No ORM.
**Consequences:** Repository layer uses raw SQL strings with parameterised
queries.  Simpler deployment, no migration tooling.

### ADR-003: Domain errors as frozen dataclasses

**Context:** Domain errors need structured fields for test assertions and
operator diagnostics.
**Decision:** All domain errors are frozen dataclasses inheriting from
`DomainError`.
**Consequences:** Callers can match on error type and inspect fields without
parsing exception strings.

### ADR-004: Workflow state machine with legal transition map

**Context:** Job applications have a defined lifecycle that must not permit
illegal transitions.
**Decision:** A declarative `LEGAL_TRANSITIONS` dict maps `(from, to)` pairs
to human-readable reasons.  A kill switch halts all non-terminal transitions.
**Consequences:** Adding a new state requires updating the map.  The kill
switch bypasses the map for `CANCELLED` and `FAILED` transitions.

### ADR-005: MCP policy gate blocks live access by default

**Context:** MCP servers are external dependencies with network access.
**Decision:** `create_job_source()` in `policy.py` returns only the `"fake"`
server.  Any other server name raises `LiveAccessDeniedError`.
**Consequences:** Live MCP requires an explicit operator override.  Tests and
CI use the fake adapter exclusively.

### ADR-006: Compliance gate is read-only

**Context:** There is a temptation to make the compliance gate an execution
guard that blocks operations on invalid records.
**Decision:** The compliance gate validates and reports.  It never blocks or
enables.  Enforcement remains in the policy gate.
**Consequences:** Compliance validation can be run offline without affecting
system behavior.  The validation result is a data point for operator decision.

### ADR-007: Scoring policy version must change before weights change

**Context:** If weights change without a version change, audits can't tell
which policy was in effect when a score was computed.
**Decision:** `ScoringPolicy.__post_init__` checks that the current version's
weights are unchanged.  A new version string is required for new weights.
**Consequences:** Weight changes are always version-tracked.  Policy version
is part of the `ScoreResult` struct.

## Key architectural decisions

1. **Deterministic clock and UUIDs in tests** — `DeterministicClock` and
   `DeterministicUuidFactory` in `conftest.py` make tests reproducible.
2. **Fake adapters** — Every external port has a fake implementation in
   `tests/fakes/` for contract tests.
3. **Evidence files** — Task completion is recorded in `.omo/evidence/` with
   Red/Green/Verification-snapshot format.
