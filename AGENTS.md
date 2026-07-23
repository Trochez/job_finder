# job_finder — Agent Instructions

## Purpose

`job_finder` is a minimal managed project scaffold for a future job-finding
workflow.

## Status

**Managed** — this project is registered in the supreme-master workspace at
`/home/trocha/projects/master` and may receive delegated work.

## Public contract surface

- `index.md`
- `AGENTS.md`
- `docs/index.md`

## Current scope

- Managed-project bootstrap scaffold only
- No implementation yet

## Working rules

1. Start from `index.md`.
2. Keep project docs self-contained and up to date.
3. Do not modify implementation internals from the master workspace —
   always delegate through the project master agent.

## Edit permissions

Agents operating in this project may edit:

- `index.md` — with review
- `AGENTS.md` — with review
- `docs/*` — freely
- Source code — only through approved task delegation

Agents must NOT edit:

- Files outside this project directory
- Configuration files containing secrets (`.env`, `.keys/`, etc.)

## Verification expectations

1. `lsp_diagnostics` clean on changed files.
2. Documentation updated when interfaces or behaviors change.
3. OpenViking mirrors the canonical project docs after updates.

## Delegation constraints

- Project-specific implementation must use the project's master agent.
- Master workspace agents must NOT directly mutate project internals.

Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.
