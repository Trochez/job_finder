"""Data retention and purging utilities for the job-finder database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from job_finder.adapters.repositories._query_helpers import execute_sql, fetchall_rows

if TYPE_CHECKING:
    import sqlite3


@dataclass(frozen=True, slots=True)
class SubmissionTombstone:
    """Minimal tombstone entry for a purged submission."""

    job_identity_hash: str
    purged_at: datetime
    reason: str


def purge_aged_audit_data(connection: sqlite3.Connection, cutoff: datetime) -> int:
    """Delete evaluation_audit entries older than *cutoff*.

    For each purged entry the associated job identity hash is recorded as a
    tombstone so that deduplication data survives the audit purge.

    Returns the number of purged entries.
    """
    rows = fetchall_rows(
        connection,
        (
            "SELECT ea.entry_id, cj.identity_hash "
            "FROM evaluation_audit ea "
            "LEFT JOIN canonical_jobs cj ON cj.job_id = ea.job_id "
            "WHERE ea.evaluated_at_utc < ?"
        ),
        (cutoff.isoformat(),),
    )

    purged_count = 0
    with connection:
        for row in rows:
            identity_hash = row["identity_hash"]
            if identity_hash is not None:
                _ = execute_sql(
                    connection,
                    (
                        "INSERT OR IGNORE INTO submission_tombstones "
                        "(identity_hash, purged_at_utc, reason) VALUES (?, ?, ?)"
                    ),
                    (
                        identity_hash,
                        datetime.now(tz=UTC).isoformat(),
                        "audit_retention_purge",
                    ),
                )

            entry_id = row["entry_id"]
            _ = execute_sql(
                connection,
                "DELETE FROM evaluation_audit WHERE entry_id = ?",
                (entry_id,),
            )
            purged_count += 1

    return purged_count
