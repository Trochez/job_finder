"""SQLite-backed repository for evaluation audit entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, final, override

from job_finder.domain.ids import JobId, RunId
from job_finder.domain.states import EligibilityDecision, parse_eligibility_decision

from ._query_helpers import (
    execute_sql,
    fetchall_rows,
    read_datetime,
    read_optional_text,
    read_required_text,
)

if TYPE_CHECKING:
    import sqlite3
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class EvaluationAuditEntry:
    """A single row from the evaluation_audit table."""

    entry_id: str
    job_id: JobId
    run_id: RunId
    decision: EligibilityDecision
    applied_threshold: int | None
    score_value: int | None
    scoring_policy_version: str
    factor_breakdown_json: str
    evidence_references: str
    cv_artifact_reference: str | None
    evaluated_at_utc: datetime


@dataclass(frozen=True, slots=True)
class AuditPersistenceError(Exception):
    """A database operation on audit entries failed."""

    entry_id: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.entry_id}: {self.detail}"


@final
class SqliteAuditRepository:
    """Persistence adapter for the evaluation_audit table."""

    _connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with an open SQLite connection."""
        self._connection = connection

    def append_evaluation(self, entry: EvaluationAuditEntry) -> None:
        """Insert a new evaluation audit entry."""
        with self._connection:
            _ = execute_sql(
                self._connection,
                (
                    "INSERT INTO evaluation_audit ("
                    "entry_id, job_id, run_id, decision, applied_threshold, "
                    "score_value, scoring_policy_version, factor_breakdown_json, "
                    "evidence_references, cv_artifact_reference, evaluated_at_utc"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    entry.entry_id,
                    entry.job_id,
                    entry.run_id,
                    entry.decision.tag,
                    entry.applied_threshold,
                    entry.score_value,
                    entry.scoring_policy_version,
                    entry.factor_breakdown_json,
                    entry.evidence_references,
                    entry.cv_artifact_reference,
                    entry.evaluated_at_utc.isoformat(),
                ),
            )

    def list_for_job(self, job_id: JobId) -> tuple[EvaluationAuditEntry, ...]:
        """Return all audit entries for a job, ordered by evaluation time."""
        rows = fetchall_rows(
            self._connection,
            "SELECT * FROM evaluation_audit "
            "WHERE job_id = ? ORDER BY evaluated_at_utc ASC",
            (job_id,),
        )
        return tuple(_row_to_audit_entry(row) for row in rows)

    def list_older_than(
        self, cutoff: datetime,
    ) -> tuple[EvaluationAuditEntry, ...]:
        """Return entries evaluated before the given cutoff."""
        rows = fetchall_rows(
            self._connection,
            "SELECT * FROM evaluation_audit "
            "WHERE evaluated_at_utc < ? ORDER BY evaluated_at_utc ASC",
            (cutoff.isoformat(),),
        )
        return tuple(_row_to_audit_entry(row) for row in rows)


def _read_optional_int(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = f"expected INTEGER column for {field_name}, got {type(value).__name__}"
    raise TypeError(msg)


def _row_to_audit_entry(row: sqlite3.Row) -> EvaluationAuditEntry:
    return EvaluationAuditEntry(
        entry_id=read_required_text(row["entry_id"], field_name="entry_id"),
        job_id=JobId(read_required_text(row["job_id"], field_name="job_id")),
        run_id=RunId(read_required_text(row["run_id"], field_name="run_id")),
        decision=parse_eligibility_decision(
            read_required_text(row["decision"], field_name="decision"),
        ),
        applied_threshold=_read_optional_int(
            row["applied_threshold"], field_name="applied_threshold"
        ),
        score_value=_read_optional_int(row["score_value"], field_name="score_value"),
        scoring_policy_version=read_required_text(
            row["scoring_policy_version"],
            field_name="scoring_policy_version",
        ),
        factor_breakdown_json=read_required_text(
            row["factor_breakdown_json"],
            field_name="factor_breakdown_json",
        ),
        evidence_references=read_required_text(
            row["evidence_references"],
            field_name="evidence_references",
        ),
        cv_artifact_reference=read_optional_text(
            row["cv_artifact_reference"],
            field_name="cv_artifact_reference",
        ),
        evaluated_at_utc=read_datetime(
            row["evaluated_at_utc"], field_name="evaluated_at_utc",
        ),
    )
