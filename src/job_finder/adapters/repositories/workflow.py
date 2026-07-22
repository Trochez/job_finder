"""SQLite-backed repository for workflow state and transitions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, final, override

from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
    JobId,
    RunId,
)
from job_finder.domain.states import WorkflowState, parse_workflow_state

from ._query_helpers import (
    execute_sql,
    fetchall_rows,
    fetchone_row,
    read_datetime,
    read_positive_int,
    read_required_text,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class CandidateProfileRecord:
    """A row from the candidate_profiles table."""

    profile_id: CandidateProfileId
    candidate_id: CandidateId
    active_version: CandidateProfileVersionId
    timezone_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RunWatermarkRecord:
    """A row from the run_watermarks table tracking the last successful run."""

    candidate_profile_id: CandidateProfileId
    run_id: RunId
    previous_successful_watermark: datetime
    successful_through: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowTransitionAppend:
    """Parameters for appending a new workflow transition."""

    transition_id: str
    job_id: JobId
    run_id: RunId
    sequence_number: int
    from_state: WorkflowState | None
    to_state: WorkflowState
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class StoredWorkflowTransition:
    """A single row from the workflow_transitions table."""

    transition_id: str
    job_id: JobId
    run_id: RunId
    sequence_number: int
    from_state: WorkflowState | None
    to_state: WorkflowState
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowTransitionConflictError(Exception):
    """A workflow transition is not valid given the current state."""

    job_id: JobId
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.job_id}: {self.detail}"


@final
class SqliteWorkflowRepository:
    """Persistence adapter for workflow state and transitions."""

    _connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with an open SQLite connection."""
        self._connection = connection

    @classmethod
    def connect(cls, database_path: Path) -> SqliteWorkflowRepository:
        """Open a migrated database connection and return a new repository."""
        return cls(connect_migrated_sqlite_database(database_path))

    def upsert_candidate_profile(
        self, record: CandidateProfileRecord
    ) -> CandidateProfileRecord:
        """Insert or update a candidate profile with duplicate-candidate guard."""
        existing = fetchone_row(
            self._connection,
            "SELECT profile_id FROM candidate_profiles WHERE candidate_id = ?",
            (record.candidate_id,),
        )
        if existing is not None and existing["profile_id"] != record.profile_id:
            raise WorkflowTransitionConflictError(
                job_id=JobId("candidate-profile"),
                detail=(
                    "candidate "
                    f"{record.candidate_id} is already bound to profile "
                    f"{existing['profile_id']}"
                ),
            )

        with self._connection:
            _ = execute_sql(
                self._connection,
                (
                    "INSERT INTO candidate_profiles ("
                    "profile_id, candidate_id, active_version_id, "
                    "timezone_name, created_at_utc"
                    ") VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(profile_id) DO UPDATE SET "
                    "active_version_id = excluded.active_version_id, "
                    "timezone_name = excluded.timezone_name"
                ),
                (
                    record.profile_id,
                    record.candidate_id,
                    record.active_version,
                    record.timezone_name,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def save_run_watermark(self, record: RunWatermarkRecord) -> None:
        """Upsert a run watermark for the given candidate profile."""
        with self._connection:
            _ = execute_sql(
                self._connection,
                (
                    "INSERT INTO run_watermarks ("
                    "candidate_profile_id, run_id, previous_successful_watermark_utc, "
                    "successful_through_utc, updated_at_utc"
                    ") VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(candidate_profile_id) DO UPDATE SET "
                    "run_id = excluded.run_id, "
                    "previous_successful_watermark_utc = "
                    "excluded.previous_successful_watermark_utc, "
                    "successful_through_utc = excluded.successful_through_utc, "
                    "updated_at_utc = excluded.updated_at_utc"
                ),
                (
                    record.candidate_profile_id,
                    record.run_id,
                    record.previous_successful_watermark.isoformat(),
                    record.successful_through.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )

    def get_run_watermark(
        self, candidate_profile_id: CandidateProfileId
    ) -> RunWatermarkRecord | None:
        """Retrieve the run watermark for a profile, or None if none exists."""
        row = fetchone_row(
            self._connection,
            "SELECT * FROM run_watermarks WHERE candidate_profile_id = ?",
            (candidate_profile_id,),
        )
        if row is None:
            return None
        return RunWatermarkRecord(
            candidate_profile_id=CandidateProfileId(
                read_required_text(
                    row["candidate_profile_id"],
                    field_name="candidate_profile_id",
                )
            ),
            run_id=RunId(
                read_required_text(row["run_id"], field_name="run_id"),
            ),
            previous_successful_watermark=read_datetime(
                row["previous_successful_watermark_utc"],
                field_name="previous_successful_watermark_utc",
            ),
            successful_through=read_datetime(
                row["successful_through_utc"],
                field_name="successful_through_utc",
            ),
            updated_at=read_datetime(
                row["updated_at_utc"], field_name="updated_at_utc",
            ),
        )

    def append_transition(
        self, transition: WorkflowTransitionAppend
    ) -> StoredWorkflowTransition:
        """Append a workflow transition, raising on state or integrity error."""
        current_state = self._current_state(transition.job_id)
        if current_state != transition.from_state:
            raise WorkflowTransitionConflictError(
                job_id=transition.job_id,
                detail=(
                    f"expected from_state {current_state!r}, "
                    f"got {transition.from_state!r}"
                ),
            )

        try:
            with self._connection:
                _ = execute_sql(
                    self._connection,
                    (
                        "INSERT INTO workflow_transitions ("
                        "transition_id, job_id, run_id, sequence_number, "
                        "from_state, to_state, occurred_at_utc"
                        ") VALUES (?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        transition.transition_id,
                        transition.job_id,
                        transition.run_id,
                        transition.sequence_number,
                        (
                            None
                            if transition.from_state is None
                            else transition.from_state.tag
                        ),
                        transition.to_state.tag,
                        transition.occurred_at.isoformat(),
                    ),
                )
                _ = execute_sql(
                    self._connection,
                    "UPDATE canonical_jobs "
                    "SET current_workflow_state = ? WHERE job_id = ?",
                    (transition.to_state.tag, transition.job_id),
                )
        except sqlite3.IntegrityError as error:
            raise WorkflowTransitionConflictError(
                job_id=transition.job_id,
                detail=(
                    f"cannot append workflow transition "
                    f"at sequence {transition.sequence_number}"
                ),
            ) from error

        return StoredWorkflowTransition(
            transition_id=transition.transition_id,
            job_id=transition.job_id,
            run_id=transition.run_id,
            sequence_number=transition.sequence_number,
            from_state=transition.from_state,
            to_state=transition.to_state,
            occurred_at=transition.occurred_at,
        )

    def list_transitions(
        self, job_id: JobId
    ) -> tuple[StoredWorkflowTransition, ...]:
        """Return all transitions for a job, ordered by sequence number."""
        rows = fetchall_rows(
            self._connection,
            "SELECT * FROM workflow_transitions "
            "WHERE job_id = ? ORDER BY sequence_number ASC",
            (job_id,),
        )
        return tuple(_row_to_transition(row) for row in rows)

    def _current_state(self, job_id: JobId) -> WorkflowState | None:
        row = fetchone_row(
            self._connection,
            "SELECT current_workflow_state FROM canonical_jobs WHERE job_id = ?",
            (job_id,),
        )
        if row is None:
            raise WorkflowTransitionConflictError(
                job_id=job_id, detail="job does not exist",
            )

        state_tag = row["current_workflow_state"]
        if state_tag is None:
            return None
        return parse_workflow_state(
            read_required_text(state_tag, field_name="current_workflow_state")
        )


def _row_to_transition(row: sqlite3.Row) -> StoredWorkflowTransition:
    from_state_tag = row["from_state"]
    return StoredWorkflowTransition(
        transition_id=read_required_text(
            row["transition_id"], field_name="transition_id",
        ),
        job_id=JobId(
            read_required_text(row["job_id"], field_name="job_id"),
        ),
        run_id=RunId(
            read_required_text(row["run_id"], field_name="run_id"),
        ),
        sequence_number=read_positive_int(
            row["sequence_number"], field_name="sequence_number",
        ),
        from_state=None
        if from_state_tag is None
        else parse_workflow_state(
            read_required_text(from_state_tag, field_name="from_state")
        ),
        to_state=parse_workflow_state(
            read_required_text(row["to_state"], field_name="to_state"),
        ),
        occurred_at=read_datetime(
            row["occurred_at_utc"], field_name="occurred_at_utc",
        ),
    )
