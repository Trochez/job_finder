"""Telegram notification port and redaction-safe adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, override

if TYPE_CHECKING:
    from collections.abc import Sequence

_REDACTION_PATTERNS: Sequence[re.Pattern[str]] = [
    re.compile(r"https?://\S+"),
    re.compile(r"[\U0001F300-\U0010FFFF]"),
    re.compile(r"CV|curriculum\s*vitae|candidate\s*profile", re.IGNORECASE),
    re.compile(r"evidence|attachment", re.IGNORECASE),
]


@dataclass(frozen=True, slots=True)
class TelegramRedactionError(Exception):
    """Raised when a message contains content that must not be sent via Telegram."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


def _validate_message_field(value: str, field_name: str) -> None:
    for pattern in _REDACTION_PATTERNS:
        match = pattern.search(value)
        if match is not None:
            raise TelegramRedactionError(
                field_name=field_name,
                detail=(
                    f"field contains forbidden content "
                    f"matching {pattern.pattern!r}"
                ),
            )


class TelegramNotifierPort(Protocol):
    """Capability contract for sending redacted status notifications."""

    def send_status(
        self,
        workflow_status: str,
        aggregate_score: int | None = None,
    ) -> None:
        """Send a redacted workflow-status notification.

        Only *workflow_status* and *aggregate_score* are permitted.
        The implementation MUST reject any message that contains
        emoji, URLs, CV data, or evidence references.
        """
        ...


class FakeTelegramNotifier:
    """In-memory fake implementing TelegramNotifierPort for tests."""

    def __init__(self) -> None:
        """Initialise an empty sent-messages list."""
        self.sent: list[tuple[str, int | None]] = []

    def send_status(
        self,
        workflow_status: str,
        aggregate_score: int | None = None,
    ) -> None:
        """Record the call for test inspection after validating fields."""
        _validate_message_field(workflow_status, "workflow_status")
        self.sent.append((workflow_status, aggregate_score))
