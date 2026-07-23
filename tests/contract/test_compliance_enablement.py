"""Contract tests for the compliance gate — written-access-basis validation.

The compliance gate is a **read-only validator**.  These tests verify that
it correctly validates access-basis records but never enables live access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.job_finder.application.compliance_gate import (
    AccessBasisRecord,
    ComplianceViolationError,
    validate_basis_record,
)

_VALID_ACCESS_BASIS_ID = "linkedin-mcp-v1"
_VALID_MCP_SERVER = "stickerdaniel/linkedin-mcp-server"
_VALID_COMMIT = "abcdef1234567890abcdef1234567890abcdef12"
_VALID_TAG = "v0.1.2"
_VALID_REVIEW_DATE = "2026-07-22T00:00:00+00:00"
_VALID_REVIEWER = "operator-name"
_VALID_WRITTEN_BASIS = (
    "The operator reviewed the linkedin-mcp-server source pinned at commit "
    "abcdef1234 and confirmed that: searchJobs searches LinkedIn job listings "
    "via public-search surface. No write operations are enabled. No candidate "
    "PII is exfiltrated beyond job listing metadata."
)
_VALID_OPERATIONS = ("searchJobs",)
_VALID_RETENTION_DAYS = 90
_VALID_CLASSIFICATION = "public_job_listing_metadata"


def _valid_record(  # noqa: PLR0913 — test fixture with many fields
    *,
    access_basis_id: str = _VALID_ACCESS_BASIS_ID,
    mcp_server: str = _VALID_MCP_SERVER,
    pinned_commit: str = _VALID_COMMIT,
    pinned_tag: str = _VALID_TAG,
    review_date: str = _VALID_REVIEW_DATE,
    reviewer: str = _VALID_REVIEWER,
    written_permitted_access_basis: str = _VALID_WRITTEN_BASIS,
    permitted_operations: tuple[str, ...] = _VALID_OPERATIONS,
    retention_days: int = _VALID_RETENTION_DAYS,
    data_classification: str = _VALID_CLASSIFICATION,
) -> AccessBasisRecord:
    """Build a valid AccessBasisRecord with optional keyword overrides."""
    return AccessBasisRecord(
        access_basis_id=access_basis_id,
        mcp_server=mcp_server,
        pinned_commit=pinned_commit,
        pinned_tag=pinned_tag,
        review_date=review_date,
        reviewer=reviewer,
        written_permitted_access_basis=written_permitted_access_basis,
        permitted_operations=permitted_operations,
        retention_days=retention_days,
        data_classification=data_classification,
    )


class TestComplianceGateAcceptsValidRecord:
    """Happy path — all fields valid."""

    def test_valid_record_passes(self) -> None:
        record = _valid_record()
        result = validate_basis_record(record)

        assert result.passed
        assert result.violations == ()


class TestComplianceGateAccessBasisId:
    """access_basis_id validation."""

    def test_rejects_blank_access_basis_id(self) -> None:
        result = validate_basis_record(_valid_record(access_basis_id="   "))

        assert not result.passed
        assert result.violations[0].field == "access_basis_id"


class TestComplianceGateMcpServer:
    """mcp_server validation."""

    def test_rejects_blank_mcp_server(self) -> None:
        result = validate_basis_record(_valid_record(mcp_server=""))

        assert not result.passed
        assert result.violations[0].field == "mcp_server"


class TestComplianceGateCommitHash:
    """pinned_commit validation."""

    def test_rejects_short_hash(self) -> None:
        result = validate_basis_record(_valid_record(pinned_commit="abc123"))

        assert not result.passed
        assert result.violations[0].field == "pinned_commit"

    def test_rejects_non_hex_hash(self) -> None:
        result = validate_basis_record(
            _valid_record(
                pinned_commit="zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
            ),
        )

        assert not result.passed
        assert result.violations[0].field == "pinned_commit"

    def test_accepts_valid_40_char_hash(self) -> None:
        record = _valid_record(
            pinned_commit="abcdef1234567890abcdef1234567890abcdef12",
        )
        result = validate_basis_record(record)

        assert result.passed


class TestComplianceGateTag:
    """pinned_tag validation."""

    def test_rejects_non_semver_tag(self) -> None:
        result = validate_basis_record(_valid_record(pinned_tag="latest"))

        assert not result.passed
        assert result.violations[0].field == "pinned_tag"

    def test_accepts_valid_semver_tag(self) -> None:
        result = validate_basis_record(_valid_record(pinned_tag="v0.1.2"))

        assert result.passed


class TestComplianceGateReviewDate:
    """review_date validation."""

    def test_rejects_invalid_date_format(self) -> None:
        result = validate_basis_record(_valid_record(review_date="not-a-date"))

        assert not result.passed
        assert result.violations[0].field == "review_date"

    def test_rejects_naive_datetime(self) -> None:
        result = validate_basis_record(
            _valid_record(review_date="2026-07-22T00:00:00"),
        )

        assert not result.passed
        assert result.violations[0].field == "review_date"

    def test_rejects_future_date(self) -> None:
        future = (datetime.now(tz=UTC) + timedelta(days=365)).isoformat()
        result = validate_basis_record(_valid_record(review_date=future))

        assert not result.passed
        assert result.violations[0].field == "review_date"

    def test_accepts_valid_past_date(self) -> None:
        result = validate_basis_record(
            _valid_record(review_date="2026-01-15T00:00:00+00:00"),
        )

        assert result.passed


class TestComplianceGateReviewer:
    """reviewer validation."""

    def test_rejects_blank_reviewer(self) -> None:
        result = validate_basis_record(_valid_record(reviewer=""))

        assert not result.passed
        assert result.violations[0].field == "reviewer"


class TestComplianceGateWrittenBasis:
    """written_permitted_access_basis validation."""

    def test_rejects_blank_written_basis(self) -> None:
        result = validate_basis_record(
            _valid_record(written_permitted_access_basis=""),
        )

        assert not result.passed
        assert result.violations[0].field == "written_permitted_access_basis"

    def test_rejects_short_written_basis(self) -> None:
        result = validate_basis_record(
            _valid_record(written_permitted_access_basis="too short"),
        )

        assert not result.passed
        assert result.violations[0].field == "written_permitted_access_basis"


class TestComplianceGatePermittedOperations:
    """permitted_operations validation."""

    def test_rejects_empty_operations(self) -> None:
        result = validate_basis_record(
            _valid_record(permitted_operations=()),
        )

        assert not result.passed
        assert result.violations[0].field == "permitted_operations"

    def test_rejects_unknown_operation(self) -> None:
        result = validate_basis_record(
            _valid_record(permitted_operations=("writeMessage",)),
        )

        assert not result.passed
        assert result.violations[0].field == "permitted_operations"


class TestComplianceGateRetentionDays:
    """retention_days validation."""

    def test_rejects_zero_retention_days(self) -> None:
        result = validate_basis_record(_valid_record(retention_days=0))

        assert not result.passed
        assert result.violations[0].field == "retention_days"

    def test_rejects_negative_retention_days(self) -> None:
        result = validate_basis_record(_valid_record(retention_days=-1))

        assert not result.passed
        assert result.violations[0].field == "retention_days"


class TestComplianceGateDataClassification:
    """data_classification validation."""

    def test_rejects_unknown_classification(self) -> None:
        result = validate_basis_record(
            _valid_record(data_classification="secret_stuff"),
        )

        assert not result.passed
        assert result.violations[0].field == "data_classification"


class TestComplianceGateAccumulatesMultipleViolations:
    """Multiple validation failures at once."""

    def test_reports_multiple_violations(self) -> None:
        result = validate_basis_record(
            _valid_record(
                access_basis_id="",
                pinned_commit="bad",
                retention_days=-1,
            ),
        )

        assert not result.passed
        assert len(result.violations) >= 3

    def test_violations_have_structured_fields(self) -> None:
        result = validate_basis_record(
            _valid_record(pinned_commit="bad"),
        )

        violation = result.violations[0]
        assert isinstance(violation, ComplianceViolationError)
        assert violation.field == "pinned_commit"
        assert "40-character" in violation.reason


class TestAccessBasisRecordExpiry:
    """AccessBasisRecord expiry logic."""

    def test_recent_record_is_not_expired(self) -> None:
        record = _valid_record(
            review_date=(datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
        )

        assert not record.is_expired()

    def test_old_record_exceeding_retention_is_expired(self) -> None:
        record = _valid_record(
            review_date=(datetime.now(tz=UTC) - timedelta(days=180)).isoformat(),
            retention_days=90,
        )

        assert record.is_expired()
