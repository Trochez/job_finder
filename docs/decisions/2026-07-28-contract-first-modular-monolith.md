# 2026-07-28 Contract-first modular monolith

Decision

Build platform as one repo, one SQLite-backed app, with typed domain contracts before provider adapters.

Drivers

- Greenfield scope.
- Immediate auto-apply requirement.
- Local auditability and deterministic state.

Consequences

- Easier run-state, audit, and retry logic.
- Browser automation stays isolated behind a port.
- No distributed orchestration until real scaling need appears.

Follow-ups

- Finalize concrete source stack once implementation repo exists.
- Keep provider contracts and state machines documented alongside code.
