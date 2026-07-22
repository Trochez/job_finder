"""State enums and parsers for job_finder workflow states."""

from __future__ import annotations

from enum import StrEnum, unique

from .errors import InvalidStateTagError


@unique
class WorkflowState(StrEnum):
    """State of a job application workflow."""

    EVALUATED = "evaluated"
    INELIGIBLE = "ineligible"
    READY_FOR_USER = "ready_for_user"
    HUMAN_CHECKPOINT_PAUSE = "human_checkpoint_pause"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def tag(self) -> str:
        """Return the state value as a tag string."""
        return str(self)


@unique
class EligibilityDecision(StrEnum):
    """Decision outcome of an eligibility evaluation."""

    ELIGIBLE = "eligible"
    HARD_FILTER_BLOCKED = "hard_filter_blocked"
    INELIGIBLE = "ineligible"
    THRESHOLD_UNSET = "threshold_unset"

    @property
    def tag(self) -> str:
        """Return the decision value as a tag string."""
        return str(self)


@unique
class CheckpointState(StrEnum):
    """State of a workflow checkpoint such as captcha or login challenges."""

    ANTI_AUTOMATION = "anti_automation"
    CAPTCHA = "captcha"
    LOGIN_CHALLENGE = "login_challenge"
    TWO_FACTOR = "two_factor"
    UNKNOWN_SCREENING_QUESTION = "unknown_screening_question"

    @property
    def tag(self) -> str:
        """Return the state value as a tag string."""
        return str(self)


def parse_workflow_state(state_tag: str) -> WorkflowState:
    """Parse a string tag into a WorkflowState enum value."""
    try:
        return WorkflowState(state_tag)
    except ValueError as error:
        raise InvalidStateTagError(
            state_kind="workflow",
            state_tag=state_tag,
        ) from error


def parse_eligibility_decision(state_tag: str) -> EligibilityDecision:
    """Parse a string tag into an EligibilityDecision enum value."""
    match state_tag:
        case EligibilityDecision.ELIGIBLE.value:
            return EligibilityDecision.ELIGIBLE
        case EligibilityDecision.HARD_FILTER_BLOCKED.value:
            return EligibilityDecision.HARD_FILTER_BLOCKED
        case EligibilityDecision.INELIGIBLE.value:
            return EligibilityDecision.INELIGIBLE
        case EligibilityDecision.THRESHOLD_UNSET.value:
            return EligibilityDecision.THRESHOLD_UNSET
        case _:
            raise InvalidStateTagError(state_kind="eligibility", state_tag=state_tag)


def parse_checkpoint_state(state_tag: str) -> CheckpointState:
    """Parse a string tag into a CheckpointState enum value."""
    match state_tag:
        case CheckpointState.ANTI_AUTOMATION.value:
            return CheckpointState.ANTI_AUTOMATION
        case CheckpointState.CAPTCHA.value:
            return CheckpointState.CAPTCHA
        case CheckpointState.LOGIN_CHALLENGE.value:
            return CheckpointState.LOGIN_CHALLENGE
        case CheckpointState.TWO_FACTOR.value:
            return CheckpointState.TWO_FACTOR
        case CheckpointState.UNKNOWN_SCREENING_QUESTION.value:
            return CheckpointState.UNKNOWN_SCREENING_QUESTION
        case _:
            raise InvalidStateTagError(state_kind="checkpoint", state_tag=state_tag)
