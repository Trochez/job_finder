# Docs Structure Context Snapshot

## Task statement
Define project documentation structure under `./docs` so future agents can find best context for assignments.

## Desired outcome
A concise docs tree and indexing strategy, plus guidance on where agents should look first.

## Known facts
- Workspace is greenfield for product code.
- Existing durable artifacts live in `plan_to_do/` and `.omo/`.
- User wants docs material stored in `./docs`.

## Constraints
- Must help agents verify where/how to get best context for an assignment.
- Should function as project documentation, not product implementation.

## Unknowns / open questions
- Audience split: human maintainer vs autonomous agent vs both.
- Whether docs should include operational runbooks, ADRs, or only onboarding/architecture.
- Whether index should be machine-readable beyond Markdown.

## Likely touchpoints
- `docs/README.md`
- `docs/index.md` or `docs/map.md`
- `docs/agent-context.md`
- `docs/architecture/`, `docs/runbooks/`, `docs/adr/`, `docs/decisions/`, `docs/operations/`
