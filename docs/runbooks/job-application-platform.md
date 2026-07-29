# Job Application Platform Runbook

## Local setup

- Keep credentials in `.keys/`.
- Use SQLite for local persistence.
- Run dry-run mode first.

## Daily automation

- Start scheduled run only after confirming settings.
- Stop scheduled run before changing credentials or browser selectors.

## Manual recovery

- If browser flow hits CAPTCHA, MFA, consent, auth wall, or block, queue manual action.
- If application has unresolved factual question, move it to pending answers.

## Gmail reconciliation

- Treat Gmail as status evidence only.
- Record matching message IDs and confidence.

## Safety checks

- Never invent education or certifications.
- Never bypass anti-bot or auth controls.
