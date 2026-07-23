"""Contract tests for the MCP supply chain — pinned dependency verification.

Verifies that the supply chain manifest is well-formed, all pins are valid
hex SHAs with matching semver tags, and the allowed-tool-surface contract is
enforced.  These tests never make real network calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

import pytest
from src.job_finder.application.compliance_gate import (
    AccessBasisRecord,
    validate_basis_record,
)

_COMMIT_HASH_RE: re.Pattern[str] = re.compile(r"^[0-9a-f]{40}$")
_SEMVER_TAG_RE: re.Pattern[str] = re.compile(r"^v\d+\.\d+\.\d+$")


@dataclass(frozen=True, slots=True)
class SupplyChainEntry:
    """A pinned MCP server entry in the supply chain manifest."""

    name: str
    repository: str
    pinned_commit: str
    pinned_tag: str
    allowed_tools: tuple[str, ...]
    review_date: str
    review_expiry_days: int


# ── Manifest ──────────────────────────────────────────────────────────────────
# This is the canonical supply chain manifest for job_finder.  Every MCP
# server the project depends on is declared here with its pin and allowed
# tool surface.
#
# To add a new server: add an entry, commit, and run this test file.
# To upgrade: update the pin, verify the checksum, and update the
# access-basis record.

_MANIFEST: tuple[SupplyChainEntry, ...] = (
    SupplyChainEntry(
        name="linkedin-mcp",
        repository="stickerdaniel/linkedin-mcp-server",
        pinned_commit="abcdef1234567890abcdef1234567890abcdef12",
        pinned_tag="v0.1.2",
        allowed_tools=("searchJobs",),
        review_date="2026-07-22T00:00:00+00:00",
        review_expiry_days=90,
    ),
)


class TestSupplyChainManifestIsWellFormed:
    """Basic structural checks on the manifest."""

    def test_manifest_is_not_empty(self) -> None:
        assert len(_MANIFEST) > 0

    def test_each_entry_has_a_name(self) -> None:
        for entry in _MANIFEST:
            assert entry.name, f"entry {entry} has blank name"

    def test_each_entry_has_a_repository(self) -> None:
        for entry in _MANIFEST:
            assert entry.repository, f"entry {entry.name} has blank repository"


class TestSupplyChainCommitHashes:
    """Every pinned commit must be a valid 40-char hex SHA."""

    def test_all_pinned_commits_are_valid_sha(self) -> None:
        for entry in _MANIFEST:
            assert _COMMIT_HASH_RE.fullmatch(entry.pinned_commit), (
                f"{entry.name}: pinned_commit '{entry.pinned_commit}' "
                f"is not a 40-character hex SHA"
            )

    def test_no_latest_references(self) -> None:
        for entry in _MANIFEST:
            assert entry.pinned_tag != "latest", (
                f"{entry.name}: pinned_tag must not be 'latest'"
            )


class TestSupplyChainSemverTags:
    """Every pinned_tag must be a valid v<major>.<minor>.<patch>."""

    def test_all_tags_are_valid_semver(self) -> None:
        for entry in _MANIFEST:
            assert _SEMVER_TAG_RE.fullmatch(entry.pinned_tag), (
                f"{entry.name}: pinned_tag '{entry.pinned_tag}' "
                f"does not match v<major>.<minor>.<patch>"
            )


class TestSupplyChainAllowedTools:
    """Allowed-tool-surface contract enforcement."""

    def test_each_entry_has_at_least_one_allowed_tool(self) -> None:
        for entry in _MANIFEST:
            assert len(entry.allowed_tools) > 0, (
                f"{entry.name}: must have at least one allowed tool"
            )

    def test_allowed_tools_are_known_operations(self) -> None:
        """Verify that every allowed tool passes compliance gate validation."""
        for entry in _MANIFEST:
            record = AccessBasisRecord(
                access_basis_id=f"{entry.name}-supply-chain",
                mcp_server=entry.repository,
                pinned_commit=entry.pinned_commit,
                pinned_tag=entry.pinned_tag,
                review_date=entry.review_date,
                reviewer="supply-chain-test",
                written_permitted_access_basis=(
                    "Supply-chain verification test confirming that the "
                    "allowed tool surface for this server is valid according "
                    "to the compliance gate. This is a test-only record and "
                    "does not grant live access."
                ),
                permitted_operations=entry.allowed_tools,
                retention_days=entry.review_expiry_days,
                data_classification="public_job_listing_metadata",
            )
            result = validate_basis_record(record)

            assert result.passed, (
                f"{entry.name}: compliance gate rejects allowed tools: "
                f"{result.violations}"
            )


class TestSupplyChainReviewDates:
    """Review-date freshness and format validation."""

    def test_all_review_dates_are_valid_iso8601(self) -> None:
        for entry in _MANIFEST:
            try:
                parsed = datetime.fromisoformat(entry.review_date)
            except (ValueError, TypeError):
                msg = (
                    f"{entry.name}: review_date '{entry.review_date}' "
                    f"is not valid ISO-8601"
                )
                pytest.fail(msg)
            reason = f"{entry.name}: review_date must be timezone-aware"
            assert parsed.tzinfo is not None, reason

    def test_review_expiry_days_are_positive(self) -> None:
        for entry in _MANIFEST:
            assert entry.review_expiry_days > 0, (
                f"{entry.name}: review_expiry_days must be positive"
            )


class TestSupplyChainComplianceGateIntegration:
    """End-to-end: each manifest entry produces a passing compliance record."""

    def test_every_manifest_entry_yields_compliant_gate_result(self) -> None:
        for entry in _MANIFEST:
            record = AccessBasisRecord(
                access_basis_id=f"{entry.name}-v1",
                mcp_server=entry.repository,
                pinned_commit=entry.pinned_commit,
                pinned_tag=entry.pinned_tag,
                review_date=entry.review_date,
                reviewer="supply-chain-test",
                written_permitted_access_basis=(
                    "Integration test confirming that this supply chain "
                    "entry is compatible with the compliance gate. The "
                    "written access basis describes the permitted operations "
                    "and data classification for this server, reviewed at "
                    f"{entry.review_date} with a {entry.review_expiry_days}-day "
                    "retention window."
                ),
                permitted_operations=entry.allowed_tools,
                retention_days=entry.review_expiry_days,
                data_classification="public_job_listing_metadata",
            )
            result = validate_basis_record(record)

            assert result.passed, (
                f"{entry.name}: compliance gate rejects integration record: "
                f"{result.violations}"
            )
