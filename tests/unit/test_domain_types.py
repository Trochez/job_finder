from __future__ import annotations

import pytest
from src.job_finder.domain.errors import InvalidStateTagError, InvalidTimezoneError
from src.job_finder.domain.ids import CandidateId, JobId, UserTimezone
from src.job_finder.domain.states import (
    EligibilityDecision,
    WorkflowState,
    parse_workflow_state,
)


def test_ids_preserve_distinct_domain_concepts() -> None:
    candidate_id = CandidateId("candidate-123")
    job_id = JobId("job-456")

    assert candidate_id == "candidate-123"
    assert job_id == "job-456"
    assert candidate_id != job_id


def test_user_timezone_accepts_valid_iana_name() -> None:
    timezone = UserTimezone.from_name("Europe/Warsaw")

    assert timezone.name == "Europe/Warsaw"
    assert str(timezone.zoneinfo) == "Europe/Warsaw"


def test_user_timezone_rejects_invalid_iana_name() -> None:
    with pytest.raises(InvalidTimezoneError) as exc_info:
        _ = UserTimezone.from_name("Mars/Olympus")
    assert exc_info.value.timezone_name == "Mars/Olympus"
    assert "Mars/Olympus" in str(exc_info.value)


def test_parse_workflow_state_returns_tagged_state() -> None:
    assert parse_workflow_state("ready_for_user") is WorkflowState.READY_FOR_USER
    assert WorkflowState.READY_FOR_USER.tag == "ready_for_user"
    assert EligibilityDecision.ELIGIBLE.tag == "eligible"


def test_parse_workflow_state_rejects_unknown_tag() -> None:
    with pytest.raises(InvalidStateTagError) as exc_info:
        _ = parse_workflow_state("teleported")
    assert exc_info.value.state_kind == "workflow"
    assert exc_info.value.state_tag == "teleported"
    assert "teleported" in str(exc_info.value)
