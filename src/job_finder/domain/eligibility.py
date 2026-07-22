"""Eligibility determination models for job_finder."""

from __future__ import annotations

from dataclasses import dataclass

from .states import EligibilityDecision


@dataclass(frozen=True, slots=True)
class HardFilter:
    """A binary pass/fail filter applied during eligibility determination."""

    name: str
    passed: bool

    @property
    def tag(self) -> str:
        """Return the filter name as a tag value."""
        return self.name


@dataclass(frozen=True, slots=True)
class EligibilityRule:
    """A rule combining a score threshold with hard filters."""

    threshold: int | None
    hard_filters: tuple[HardFilter, ...]


@dataclass(frozen=True, slots=True)
class EligibilityVerdict:
    """The outcome of evaluating eligibility for a candidate."""

    decision: EligibilityDecision
    reason: str
    score_used: int | None
    filter_results: tuple[HardFilter, ...]


def determine_eligibility(
    *,
    score: int | None,
    threshold: int | None,
    hard_filters: tuple[HardFilter, ...],
) -> EligibilityVerdict:
    """Evaluate candidate eligibility against a threshold and hard filters."""
    filter_results = hard_filters

    if threshold is None:
        return EligibilityVerdict(
            decision=EligibilityDecision.THRESHOLD_UNSET,
            reason="eligibility threshold is not configured",
            score_used=score,
            filter_results=filter_results,
        )

    for hard_filter in hard_filters:
        if not hard_filter.passed:
            return EligibilityVerdict(
                decision=EligibilityDecision.HARD_FILTER_BLOCKED,
                reason=f"hard filter '{hard_filter.name}' failed",
                score_used=score,
                filter_results=filter_results,
            )

    if score is None:
        return EligibilityVerdict(
            decision=EligibilityDecision.INELIGIBLE,
            reason="score is not available",
            score_used=None,
            filter_results=filter_results,
        )

    if score >= threshold:
        return EligibilityVerdict(
            decision=EligibilityDecision.ELIGIBLE,
            reason=f"score {score} meets threshold {threshold}",
            score_used=score,
            filter_results=filter_results,
        )

    return EligibilityVerdict(
        decision=EligibilityDecision.INELIGIBLE,
        reason=f"score {score} below threshold {threshold}",
        score_used=score,
        filter_results=filter_results,
    )
