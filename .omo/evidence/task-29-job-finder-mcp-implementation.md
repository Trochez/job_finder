# Task 29 Evidence — Privacy, retention, logging, and no-live-call regression suite

## Scope

Sentinel-data tests for logs, responses, evidence, purge, notification payloads, package manifests, process spawning.

## Files

- `tests/security/test_privacy_retention_default_deny.py`
- `tests/fakes/sentinels.py`

## Red

- `uv run pytest -q tests/security/` — initial failure before implementation

## Green

- `uv run pytest -q tests/security/`
- Result: 14 passed

## Sentinel tests verified

- **API key sentinel not in fake notifier payloads** — sentinel API key is not leaked via notifications
- **CV text sentinel not in fake notifier payloads** — CV text caught by redaction patterns
- **Evidence link sentinel not in fake notifier payloads** — URL caught by redaction patterns
- **Sentinel data not in health endpoint HTTP response** — no sentinel values leak through API
- **Sentinel data not in audit routes HTTP response** — audit views redact sentinel data
- **Live MCP adapter raises LiveAccessDeniedError** — default-deny enforced
- **Live MCP adapter never makes network calls** — `FakeJobSourcePort` intercepts all calls
- **Expired retention purge removes audit entries** — 90-day retention enforced
- **Expired retention purge does NOT remove recent audit entries** — data within window preserved
- **Purge preserves submission tombstones** — dedupe works after purge
- **Telegram redaction rejects URLs** — URL sentinel blocked
- **Telegram redaction rejects emoji** — emoji content blocked
- **Telegram redaction rejects CV mentions** — CV text blocked
- **Telegram redaction rejects evidence mentions** — evidence text blocked

## Final verification snapshot

- `uv run pytest -q` → 286 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- `SentinelDataSet` fixture provides 6 sentinel types (API key, token, email, phone, evidence link, CV text)
- No sentinel values appear in HTTP responses, notifications, or retained records after purge
- Live adapter invocation is always denied in test configuration
