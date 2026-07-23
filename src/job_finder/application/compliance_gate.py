"""Written-access-basis validation for MCP server compliance.

The compliance gate validates access-basis records but **never enables** live
access.  It is a read-only validator that answers "is this record valid?"
Enforcement is handled separately by the policy gate in ``adapters/mcp/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import override

from job_finder.domain.errors import DomainError

_COMMIT_HASH_RE: re.Pattern[str] = re.compile(r"^[0-9a-f]{40}$")
_SEMVER_TAG_RE: re.Pattern[str] = re.compile(r"^v\d+\.\d+\.\d+$")
_MIN_BASIS_LENGTH: int = 100

_KNOWN_OPERATIONS: frozenset[str] = frozenset({
    "searchJobs",
    "search",
    "getJobDetails",
})
_KNOWN_CLASSIFICATIONS: frozenset[str] = frozenset({
    "public_job_listing_metadata",
    "candidate_profile",
    "audit_log",
    "internal_configuration",
})


@dataclass(frozen=True, slots=True)
class ComplianceViolationError(DomainError):
    """A single validation failure in an access-basis record."""

    field: str
    reason: str

    @override
    def __str__(self) -> str:
        return f"{self.field}: {self.reason}"


@dataclass(frozen=True, slots=True)
class ComplianceGateResult:
    """The outcome of running the compliance gate on an access-basis record.

    Attributes:
        passed: True when every validation rule passes.
        violations: Tuple of individual compliance violations found.
    """

    passed: bool
    violations: tuple[ComplianceViolationError, ...]


@dataclass(frozen=True, slots=True)
class AccessBasisRecord:
    """A written access-basis record describing permitted MCP access.

    Attributes:
        access_basis_id: Unique identifier for this record.
        mcp_server: GitHub repo path of the MCP server.
        pinned_commit: Full SHA commit hash the review was based on.
        pinned_tag: Semver tag matching the pinned commit.
        review_date: ISO-8601 date of the last human review.
        reviewer: Identity of the person who performed the review.
        written_permitted_access_basis: Narrative justification.
        permitted_operations: List of MCP tool names allowed after review.
        retention_days: Data retention window in days.
        data_classification: Classification label for the data accessed.
    """

    access_basis_id: str
    mcp_server: str
    pinned_commit: str
    pinned_tag: str
    review_date: str
    reviewer: str
    written_permitted_access_basis: str
    permitted_operations: tuple[str, ...]
    retention_days: int
    data_classification: str

    def days_since_review(self) -> int:
        """Return the number of days between review_date and today (UTC)."""
        review = datetime.fromisoformat(self.review_date)
        today = datetime.now(tz=UTC)
        delta = today - review.replace(tzinfo=UTC)
        return delta.days

    def is_expired(self) -> bool:
        """Return True when the review date exceeds the retention window."""
        return self.days_since_review() > self.retention_days


def validate_basis_record(record: AccessBasisRecord) -> ComplianceGateResult:
    """Run all validation rules against an access-basis record.

    This is a **read-only** validator.  It inspects the record and returns
    a ``ComplianceGateResult`` but never modifies state, never enables
    live access, and never raises exceptions.

    Returns:
        A ``ComplianceGateResult`` with pass/fail and any violations.
    """
    violations: list[ComplianceViolationError] = []

    _require_non_blank(record.access_basis_id, "access_basis_id", violations)
    _require_non_blank(record.mcp_server, "mcp_server", violations)
    _validate_commit_hash(record.pinned_commit, violations)
    _validate_tag(record.pinned_tag, violations)
    _validate_review_date(record.review_date, violations)
    _require_non_blank(record.reviewer, "reviewer", violations)
    _validate_written_basis(record.written_permitted_access_basis, violations)
    _validate_permitted_operations(record.permitted_operations, violations)
    _validate_retention_days(record.retention_days, violations)
    _validate_classification(record.data_classification, violations)

    return ComplianceGateResult(
        passed=len(violations) == 0,
        violations=tuple(violations),
    )


def _require_non_blank(
    value: str,
    field: str,
    violations: list[ComplianceViolationError],
) -> None:
    if not value.strip():
        violations.append(
            ComplianceViolationError(field=field, reason="must not be blank"),
        )


def _validate_commit_hash(
    value: str,
    violations: list[ComplianceViolationError],
) -> None:
    if not _COMMIT_HASH_RE.fullmatch(value):
        violations.append(
            ComplianceViolationError(
                field="pinned_commit",
                reason="must be a 40-character hex SHA hash",
            ),
        )


def _validate_tag(
    value: str,
    violations: list[ComplianceViolationError],
) -> None:
    if not _SEMVER_TAG_RE.fullmatch(value):
        violations.append(
            ComplianceViolationError(
                field="pinned_tag",
                reason="must match v<major>.<minor>.<patch> (e.g. v0.1.2)",
            ),
        )


def _validate_review_date(
    value: str,
    violations: list[ComplianceViolationError],
) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        violations.append(
            ComplianceViolationError(
                field="review_date",
                reason="must be a valid ISO-8601 date string",
            ),
        )
        return

    if parsed.tzinfo is None:
        violations.append(
            ComplianceViolationError(
                field="review_date",
                reason="must be timezone-aware",
            ),
        )
        return

    if parsed > datetime.now(tz=UTC):
        violations.append(
            ComplianceViolationError(
                field="review_date",
                reason="must not be in the future",
            ),
        )


def _validate_written_basis(
    value: str,
    violations: list[ComplianceViolationError],
) -> None:
    _require_non_blank(value, "written_permitted_access_basis", violations)
    if len(value.strip()) < _MIN_BASIS_LENGTH:
        violations.append(
            ComplianceViolationError(
                field="written_permitted_access_basis",
                reason=f"must be at least {_MIN_BASIS_LENGTH} characters",
            ),
        )


def _validate_permitted_operations(
    operations: tuple[str, ...],
    violations: list[ComplianceViolationError],
) -> None:
    if not operations:
        violations.append(
            ComplianceViolationError(
                field="permitted_operations",
                reason="must include at least one operation",
            ),
        )
        return

    violations.extend(
        ComplianceViolationError(
            field="permitted_operations",
            reason=f"unknown operation: {op}",
        )
        for op in operations
        if op not in _KNOWN_OPERATIONS
    )


def _validate_retention_days(
    value: int,
    violations: list[ComplianceViolationError],
) -> None:
    if value < 1:
        violations.append(
            ComplianceViolationError(
                field="retention_days",
                reason="must be a positive integer",
            ),
        )


def _validate_classification(
    value: str,
    violations: list[ComplianceViolationError],
) -> None:
    if value not in _KNOWN_CLASSIFICATIONS:
        violations.append(
            ComplianceViolationError(
                field="data_classification",
                reason=f"unknown classification: {value}",
            ),
        )
