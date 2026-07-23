# F4 — Security, Privacy, and Scope-Fidelity Audit

## Auditor

M2 + M5 + Oracle — run security and contract test suites.

## Verification commands

```bash
uv run pytest -q tests/security tests/contract
```

## Results

- `tests/security` → **14 passed**
- `tests/contract` → **42 passed** (35 compliance/MCP supply chain + 7 MCP policy gate/linkedin adapter/submission routes)

## Default-deny MCP behavior

| Test | Assertion | Status |
|------|-----------|--------|
| Live MCP adapter raises LiveAccessDeniedError | Default-deny enforced at adapter boundary | ✅ |
| Fake MCP adapter returns typed fixtures | Fake path works without denial | ✅ |
| Submission routes are all non-live | easy_apply, external_ats, unsupported all blocked | ✅ |

## Pin/hash enforcement

| Test | Assertion | Status |
|------|-----------|--------|
| Valid compliance record produces EligibleForManualEnablement | Gate accepts complete records | ✅ |
| Missing MCP server field rejected | Gate rejects incomplete records | ✅ |
| Missing pin hash rejected | Supply chain verification catches missing hash | ✅ |
| Unreviewed tool surface rejected | Allowed-tools contract enforced | ✅ |

## No secret/CV leakage

| Test | Assertion | Status |
|------|-----------|--------|
| Sentinels not in health endpoint | No API key, CV, token in HTTP responses | ✅ |
| Sentinels not in audit routes | No secret data in audit views | ✅ |
| Sentinels not in fake notifier | Redaction patterns catch CV, URLs, emoji, evidence | ✅ |
| Telegram redaction rejects URLs | URL sentinel caught by pattern | ✅ |
| Telegram redaction rejects emoji | Emoji content blocked | ✅ |
| Telegram redaction rejects CV mentions | CV text blocked | ✅ |

## 90-day purge

| Test | Assertion | Status |
|------|-----------|--------|
| Expired retention removes audit entries | Old records deleted | ✅ |
| Recent retention preserves data | Records within window survive | ✅ |
| Purge preserves submission tombstones | Dedupe hash retained after purge | ✅ |

## Scope creep verification

| Scope boundary | Check | Status |
|----------------|-------|--------|
| No multi-user accounts | Single-user FastAPI, no auth/RBAC | ✅ |
| No live enablement without approval | Compliance gate validates but never enables | ✅ |
| No @latest references | Supply chain docs require pin+hash | ✅ |
| No bulk LinkedIn content storage | Minimal field model per plan | ✅ |
| No unsupported score inference | Deterministic 30/30/25/10/5 engine | ✅ |
| No CAPTCHA/bypass automation | Checkpoint pause-only behavior | ✅ |

## Verdict

**APPROVED** — All security, privacy, and scope-fidelity checks pass. Default-deny enforced. No secret/CV leakage. Retention purge works correctly. Scope boundaries respected.
