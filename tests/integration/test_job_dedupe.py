from __future__ import annotations

from typing import TYPE_CHECKING, final

from job_finder.domain.job_identity import (
    CanonicalJobIdentity,
    IdentityUnverified,
    build_job_identity,
)

if TYPE_CHECKING:
    import sqlite3


def _require_verified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> CanonicalJobIdentity:
    match identity_result:
        case CanonicalJobIdentity() as identity:
            return identity
        case IdentityUnverified() as unexpected:
            msg = f"expected a verified identity, got {unexpected.audit_status}"
            raise AssertionError(msg)


def _require_unverified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> IdentityUnverified:
    match identity_result:
        case IdentityUnverified() as unverified:
            return unverified
        case CanonicalJobIdentity() as unexpected:
            msg = f"expected identity_unverified, got {unexpected.identity_hash}"
            raise AssertionError(msg)


@final
class SqliteJobDedupeLedger:
    _connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        _ = self._connection.execute(
            "CREATE TABLE jobs ("
            "id INTEGER PRIMARY KEY, "
            "source TEXT NOT NULL, "
            "external_job_id TEXT NOT NULL, "
            "canonical_company_key TEXT NOT NULL, "
            "identity_hash TEXT NOT NULL UNIQUE"
            ")"
        )
        _ = self._connection.execute(
            "CREATE TABLE submissions (identity_hash TEXT PRIMARY KEY)"
        )

    def insert_job(self, identity: CanonicalJobIdentity) -> bool:
        changes_before = self._connection.total_changes
        _ = self._connection.execute(
            "INSERT OR IGNORE INTO jobs "
            "(source, external_job_id, canonical_company_key, identity_hash) "
            "VALUES (?, ?, ?, ?)",
            (
                identity.source,
                identity.external_job_id,
                identity.canonical_company_key,
                identity.identity_hash,
            ),
        )
        return self._connection.total_changes > changes_before

    def mark_submitted(self, identity: CanonicalJobIdentity) -> bool:
        changes_before = self._connection.total_changes
        _ = self._connection.execute(
            "INSERT OR IGNORE INTO submissions (identity_hash) VALUES (?)",
            (identity.identity_hash,),
        )
        return self._connection.total_changes > changes_before


def test_duplicate_verified_identity_is_idempotent_and_submission_cannot_repeat(
    sqlite_connection: sqlite3.Connection,
) -> None:
    # Given
    ledger = SqliteJobDedupeLedger(sqlite_connection)
    identity_result = build_job_identity(
        source="linkedin",
        external_job_id=" LI-123 ",
        canonical_company_key="acme-inc",
    )
    identity = _require_verified_identity(identity_result)

    # When
    first_insert = ledger.insert_job(identity)
    second_insert = ledger.insert_job(identity)
    first_submission = ledger.mark_submitted(identity)
    second_submission = ledger.mark_submitted(identity)

    # Then
    assert first_insert is True
    assert second_insert is False
    assert first_submission is True
    assert second_submission is False


def test_missing_external_job_id_is_identity_unverified_and_ineligible(
    sqlite_connection: sqlite3.Connection,
) -> None:
    # Given
    ledger = SqliteJobDedupeLedger(sqlite_connection)

    # When
    identity_result = build_job_identity(
        source="linkedin",
        external_job_id="   ",
        canonical_company_key="acme-inc",
    )
    unverified = _require_unverified_identity(identity_result)

    # Then
    assert unverified.audit_status == "identity_unverified"
    assert unverified.eligible_for_submission is False
    assert ledger is not None
