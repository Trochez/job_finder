"""Unit tests for workflow transition validation and kill-switch logic.

Tests the pure validation functions in ``application/workflow.py`` directly.
"""

from __future__ import annotations

import pytest

from job_finder.application.workflow import (
    LEGAL_TRANSITIONS,
    IllegalTransitionError,
    KillSwitch,
    KillSwitchEngagedError,
    _validate_kill_switch,  # type: ignore[reportPrivateUsage]
    _validate_legal,  # type: ignore[reportPrivateUsage]
)
from job_finder.domain.ids import JobId
from job_finder.domain.states import WorkflowState


class TestLegalTransitions:
    """Coverage of the legal transition map."""

    def test_required_initial_transition_present(self) -> None:
        assert (None, WorkflowState.EVALUATED) in LEGAL_TRANSITIONS

    def test_required_evaluation_outcomes_present(self) -> None:
        assert (
            WorkflowState.EVALUATED,
            WorkflowState.INELIGIBLE,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.EVALUATED,
            WorkflowState.READY_FOR_USER,
        ) in LEGAL_TRANSITIONS

    def test_required_user_actions_present(self) -> None:
        assert (
            WorkflowState.READY_FOR_USER,
            WorkflowState.SUBMITTED,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.READY_FOR_USER,
            WorkflowState.CANCELLED,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.READY_FOR_USER,
            WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        ) in LEGAL_TRANSITIONS

    def test_required_checkpoint_pause_resume_present(self) -> None:
        assert (
            WorkflowState.HUMAN_CHECKPOINT_PAUSE,
            WorkflowState.READY_FOR_USER,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.HUMAN_CHECKPOINT_PAUSE,
            WorkflowState.CANCELLED,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.HUMAN_CHECKPOINT_PAUSE,
            WorkflowState.FAILED,
        ) in LEGAL_TRANSITIONS

    def test_required_submission_outcomes_present(self) -> None:
        assert (
            WorkflowState.SUBMITTED,
            WorkflowState.FAILED,
        ) in LEGAL_TRANSITIONS
        assert (
            WorkflowState.SUBMITTED,
            WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        ) in LEGAL_TRANSITIONS

    def test_legal_transition_count(self) -> None:
        """Sanity check: we expect exactly 14 legal transitions."""
        assert len(LEGAL_TRANSITIONS) == 14

    def test_illegal_transition_raises(self) -> None:
        job_id = JobId("job:illegal")
        with pytest.raises(IllegalTransitionError) as exc_info:
            _validate_legal(
                from_state=WorkflowState.INELIGIBLE,
                to_state=WorkflowState.SUBMITTED,
                job_id=job_id,
            )
        assert exc_info.value.job_id == job_id
        assert exc_info.value.from_state is WorkflowState.INELIGIBLE
        assert exc_info.value.to_state is WorkflowState.SUBMITTED

    def test_legal_transition_passes(self) -> None:
        job_id = JobId("job:legal")
        # Should not raise
        _validate_legal(
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            job_id=job_id,
        )
        _validate_legal(
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            job_id=job_id,
        )
        _validate_legal(
            from_state=WorkflowState.READY_FOR_USER,
            to_state=WorkflowState.SUBMITTED,
            job_id=job_id,
        )


class TestKillSwitchValidation:
    """Coverage of the kill-switch guard logic."""

    def test_inactive_kill_switch_passes(self) -> None:
        job_id = JobId("job:kill-inactive")
        kill_switch = KillSwitch(is_active=False)
        # Should not raise
        _validate_kill_switch(
            kill_switch=kill_switch,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            job_id=job_id,
        )

    def test_active_kill_switch_blocks_normal_transition(self) -> None:
        job_id = JobId("job:kill-active")
        kill_switch = KillSwitch(is_active=True)
        with pytest.raises(KillSwitchEngagedError) as exc_info:
            _validate_kill_switch(
                kill_switch=kill_switch,
                from_state=WorkflowState.EVALUATED,
                to_state=WorkflowState.READY_FOR_USER,
                job_id=job_id,
            )
        assert exc_info.value.job_id == job_id
        assert exc_info.value.from_state is WorkflowState.EVALUATED
        assert exc_info.value.to_state is WorkflowState.READY_FOR_USER
        assert "kill switch" in str(exc_info.value)

    def test_active_kill_switch_allows_cancelled(self) -> None:
        job_id = JobId("job:kill-cancel")
        kill_switch = KillSwitch(is_active=True)
        # Should not raise
        _validate_kill_switch(
            kill_switch=kill_switch,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.CANCELLED,
            job_id=job_id,
        )

    def test_active_kill_switch_allows_failed(self) -> None:
        job_id = JobId("job:kill-fail")
        kill_switch = KillSwitch(is_active=True)
        # Should not raise
        _validate_kill_switch(
            kill_switch=kill_switch,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.FAILED,
            job_id=job_id,
        )


class TestKillSwitchDataclass:
    """KillSwitch is a simple frozen dataclass."""

    def test_default_inactive(self) -> None:
        ks = KillSwitch(is_active=False)
        assert not ks.is_active

    def test_active(self) -> None:
        ks = KillSwitch(is_active=True)
        assert ks.is_active
