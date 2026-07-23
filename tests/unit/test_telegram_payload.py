"""Tests for Telegram notification payload allowlist and redaction."""

from __future__ import annotations

import pytest

from job_finder.adapters.notifications.telegram import (
    FakeTelegramNotifier,
    TelegramRedactionError,
)


class TestTelegramPayloadAllowlist:
    """The notifier must accept only workflow_status and aggregate_score."""

    def test_allowed_payload_passes(self) -> None:
        """Plain status text should pass without error."""
        notifier = FakeTelegramNotifier()
        notifier.send_status("running", 85)
        assert notifier.sent == [("running", 85)]

    def test_allowed_payload_without_score(self) -> None:
        """Status without score should also pass."""
        notifier = FakeTelegramNotifier()
        notifier.send_status("idle")
        assert notifier.sent == [("idle", None)]

    def test_url_in_status_rejected(self) -> None:
        """URLs in the status field must be rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError, match="forbidden"):
            notifier.send_status("click https://example.com/job")

    def test_emoji_in_status_rejected(self) -> None:
        """Emoji characters in the status field must be rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError, match="forbidden"):
            notifier.send_status("job found 🎉")

    def test_cv_mention_in_status_rejected(self) -> None:
        """CV/curriculum vitae mentions in status must be rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError, match="CV"):
            notifier.send_status("CV matched for job")

    def test_evidence_mention_in_status_rejected(self) -> None:
        """Evidence/attachment mentions in status must be rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError, match="evidence"):
            notifier.send_status("evidence attached")

    def test_multiple_notifications_accrue(self) -> None:
        """Multiple send_status calls should accumulate."""
        notifier = FakeTelegramNotifier()
        notifier.send_status("running", 50)
        notifier.send_status("completed", 90)
        assert notifier.sent == [("running", 50), ("completed", 90)]
