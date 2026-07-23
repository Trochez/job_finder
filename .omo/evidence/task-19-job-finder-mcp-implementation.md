# Task 19 Evidence — Telegram allowlist notification port and fake notifier

## Scope

Serialize only workflow_status and aggregate_score. Fake notifier in tests. Typed failure handling. No forbidden fields.

## Files

- `src/job_finder/adapters/notifications/telegram.py`
- `tests/unit/test_telegram_payload.py`

## Red

- `uv run pytest -q tests/unit/test_telegram_payload.py` — initial failure before implementation

## Green

- `uv run pytest -q tests/unit/test_telegram_payload.py`
- Result: 7 passed (allowlist verified, forbidden fields rejected)

## Final verification snapshot

- `uv run pytest -q` → 158 + 7 = 165 passed
- `uv run ruff check src/ tests/` → All checks passed
- `uv run basedpyright` → 0 errors

## Notes

- FakeTelegramNotifier validates against redaction patterns before recording.
- URLs, emoji, CV mentions, evidence/attachment references all rejected with TelegramRedactionError.
