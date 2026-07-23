"""Sentinel data patterns for security/privacy tests.

Sentinels are synthetic sensitive strings that MUST NOT leak through
logs, HTTP responses, notification payloads, evidence records, or
any other output channel.  Security tests plant sentinels and verify
they stay contained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

# ── Individual sentinel strings ──────────────────────────────────────────────

SENTINEL_API_KEY: Final[str] = "sk-live-7f3a2b1c9d8e4f5a0b1c2d3e4f5a6b7c"
"""Simulated live API key sentinel — must never be logged or rendered."""

SENTINEL_ACCESS_TOKEN: Final[str] = "ghp_sup3rs3cr3tt0k3n"  # noqa: S105
"""Simulated GitHub token sentinel — must never be logged or rendered."""

SENTINEL_EMAIL: Final[str] = "jane.private@supersecret-company.internal"
"""Simulated private email sentinel — must never be leaked."""

SENTINEL_PHONE: Final[str] = "+1-555-SECRET-99"
"""Simulated phone number sentinel — must never be leaked."""

SENTINEL_EVIDENCE_LINK: Final[str] = (
    "https://drive.google.com/file/d/0B5ecrets0nly/view"
)
"""Simulated evidence link sentinel — must not appear in notification text."""

SENTINEL_CV_TEXT: Final[str] = (
    "Curriculum Vitae: classified candidate profile version 7f3a2b"
)
"""Simulated CV excerpt sentinel — must not appear in notification text."""

# ── Structured sentinel set ──────────────────────────────────────────────────


@dataclass(frozen=True)
class SentinelDataSet:
    """Collection of all sentinel values for a security test run.

    Each attribute is a well-known sentinel that must remain
    contained within the test scenario.
    """

    api_key: str = SENTINEL_API_KEY
    access_token: str = SENTINEL_ACCESS_TOKEN
    email: str = SENTINEL_EMAIL
    phone: str = SENTINEL_PHONE
    evidence_link: str = SENTINEL_EVIDENCE_LINK
    cv_text: str = SENTINEL_CV_TEXT
    planted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def all_strings(self) -> tuple[str, ...]:
        """Return every sentinel as a flat tuple for bulk scanning."""
        return (
            self.api_key,
            self.access_token,
            self.email,
            self.phone,
            self.evidence_link,
            self.cv_text,
        )
