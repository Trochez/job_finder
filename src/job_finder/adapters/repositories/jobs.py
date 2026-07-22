"""SQLite-backed repository for canonical job records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final, override
from uuid import uuid4

from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.domain.ids import CandidateProfileId, JobId
from job_finder.domain.job_identity import (
    CanonicalJobIdentity,
    IdentityUnverified,
    JobIdentityHash,
)

from ._query_helpers import (
    execute_sql,
    fetchone_row,
    read_datetime,
    read_optional_text,
    read_required_text,
)

if TYPE_CHECKING:
    import sqlite3
    from datetime import datetime
    from pathlib import Path

_CANONICAL_IDENTITY_STATUS: Final = "canonical"


@dataclass(frozen=True, slots=True)
class CanonicalJobUpsert:
    """Parameters for inserting a fully-identified job."""

    candidate_profile_id: CandidateProfileId
    identity: CanonicalJobIdentity
    discovered_at: datetime


@dataclass(frozen=True, slots=True)
class IdentityUnverifiedInsert:
    """Parameters for inserting an unverified-identity job."""

    candidate_profile_id: CandidateProfileId
    identity: IdentityUnverified
    discovered_at: datetime


@dataclass(frozen=True, slots=True)
class StoredJobRecord:
    """A single row from the canonical_jobs table."""

    job_id: JobId
    candidate_profile_id: CandidateProfileId
    source: str
    external_job_id: str | None
    canonical_company_key: str
    identity_hash: JobIdentityHash | None
    identity_status: str
    identity_unverified_reason: str | None
    discovered_at: datetime


@dataclass(frozen=True, slots=True)
class JobPersistenceError(Exception):
    """A database operation on jobs failed."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


@final
class SqliteJobsRepository:
    """Persistence adapter for the canonical_jobs table."""

    _connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with an open SQLite connection."""
        self._connection = connection

    @classmethod
    def connect(cls, database_path: Path) -> SqliteJobsRepository:
        """Open a migrated database connection and return a new repository."""
        return cls(connect_migrated_sqlite_database(database_path))

    def upsert_canonical_job(self, request: CanonicalJobUpsert) -> StoredJobRecord:
        """Insert or ignore a fully-identified job and return the stored record."""
        job_id = JobId(f"job:{request.identity.identity_hash}")
        with self._connection:
            _ = execute_sql(
                self._connection,
                (
                    "INSERT INTO canonical_jobs ("
                    "job_id, candidate_profile_id, source, external_job_id, "
                    "canonical_company_key, identity_hash, identity_status, "
                    "identity_unverified_reason, discovered_at_utc"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(identity_hash) DO NOTHING"
                ),
                (
                    job_id,
                    request.candidate_profile_id,
                    request.identity.source,
                    request.identity.external_job_id,
                    request.identity.canonical_company_key,
                    request.identity.identity_hash,
                    _CANONICAL_IDENTITY_STATUS,
                    None,
                    request.discovered_at.isoformat(),
                ),
            )
        return self._get_by_identity_hash(request.identity.identity_hash)

    def insert_identity_unverified_job(
        self, request: IdentityUnverifiedInsert
    ) -> StoredJobRecord:
        """Insert a job whose identity could not be verified and return the record."""
        job_id = JobId(f"job:{_uuid4()}")
        with self._connection:
            _ = execute_sql(
                self._connection,
                (
                    "INSERT INTO canonical_jobs ("
                    "job_id, candidate_profile_id, source, external_job_id, "
                    "canonical_company_key, identity_hash, identity_status, "
                    "identity_unverified_reason, discovered_at_utc"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    job_id,
                    request.candidate_profile_id,
                    request.identity.source,
                    None,
                    request.identity.canonical_company_key,
                    None,
                    request.identity.audit_status,
                    request.identity.reason.tag,
                    request.discovered_at.isoformat(),
                ),
            )
        return self._get_by_job_id(job_id)

    def _get_by_identity_hash(self, identity_hash: JobIdentityHash) -> StoredJobRecord:
        row = fetchone_row(
            self._connection,
            "SELECT * FROM canonical_jobs WHERE identity_hash = ?",
            (identity_hash,),
        )
        if row is None:
            raise JobPersistenceError(
                detail=f"missing job for identity hash {identity_hash}",
            )
        return _row_to_stored_job(row)

    def _get_by_job_id(self, job_id: JobId) -> StoredJobRecord:
        row = fetchone_row(
            self._connection,
            "SELECT * FROM canonical_jobs WHERE job_id = ?",
            (job_id,),
        )
        if row is None:
            raise JobPersistenceError(detail=f"missing job {job_id}")
        return _row_to_stored_job(row)


def _uuid4() -> str:
    return str(uuid4())


def _row_to_stored_job(row: sqlite3.Row) -> StoredJobRecord:
    return StoredJobRecord(
        job_id=JobId(read_required_text(row["job_id"], field_name="job_id")),
        candidate_profile_id=CandidateProfileId(
            read_required_text(
                row["candidate_profile_id"],
                field_name="candidate_profile_id",
            )
        ),
        source=read_required_text(row["source"], field_name="source"),
        external_job_id=read_optional_text(
            row["external_job_id"], field_name="external_job_id",
        ),
        canonical_company_key=read_required_text(
            row["canonical_company_key"],
            field_name="canonical_company_key",
        ),
        identity_hash=None
        if row["identity_hash"] is None
        else JobIdentityHash(
            read_required_text(row["identity_hash"], field_name="identity_hash")
        ),
        identity_status=read_required_text(
            row["identity_status"], field_name="identity_status",
        ),
        identity_unverified_reason=read_optional_text(
            row["identity_unverified_reason"],
            field_name="identity_unverified_reason",
        ),
        discovered_at=read_datetime(
            row["discovered_at_utc"], field_name="discovered_at_utc",
        ),
    )
