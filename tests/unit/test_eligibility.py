from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from src.job_finder.domain.eligibility import (
    EligibilityRule,
    HardFilter,
    determine_eligibility,
)
from src.job_finder.domain.states import EligibilityDecision


def test_hard_filter_tag_returns_name() -> None:
    hf = HardFilter(name="location", passed=True)
    assert hf.tag == "location"


def test_hard_filter_tag_returns_name_even_when_failed() -> None:
    hf = HardFilter(name="years_experience", passed=False)
    assert hf.tag == "years_experience"


def test_eligibility_rule_stores_threshold_and_filters() -> None:
    filters = (HardFilter(name="location", passed=True),)
    rule = EligibilityRule(threshold=50, hard_filters=filters)
    assert rule.threshold == 50
    assert rule.hard_filters == filters


def test_eligibility_rule_allows_none_threshold() -> None:
    rule = EligibilityRule(threshold=None, hard_filters=())
    assert rule.threshold is None


def test_determine_eligibility_threshold_unset() -> None:
    """When threshold is None, result is THRESHOLD_UNSET regardless of score."""
    verdict = determine_eligibility(
        score=100,
        threshold=None,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.THRESHOLD_UNSET
    assert verdict.reason == "eligibility threshold is not configured"
    assert verdict.score_used == 100
    assert verdict.filter_results == ()


def test_determine_eligibility_threshold_unset_with_failed_filters() -> None:
    """Hard filters are not even checked when threshold is None."""
    filters = (HardFilter(name="location", passed=False),)
    verdict = determine_eligibility(
        score=100,
        threshold=None,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.THRESHOLD_UNSET
    assert verdict.filter_results == filters


def test_determine_eligibility_threshold_unset_with_none_score() -> None:
    verdict = determine_eligibility(
        score=None,
        threshold=None,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.THRESHOLD_UNSET
    assert verdict.score_used is None


def test_determine_eligibility_hard_filter_blocked_first_failure() -> None:
    """First failed filter is reported in the reason."""
    filters = (
        HardFilter(name="location", passed=True),
        HardFilter(name="years_experience", passed=False),
        HardFilter(name="visa", passed=False),
    )
    verdict = determine_eligibility(
        score=80,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.HARD_FILTER_BLOCKED
    assert verdict.reason == "hard filter 'years_experience' failed"
    assert verdict.score_used == 80
    assert verdict.filter_results == filters


def test_determine_eligibility_hard_filter_blocked_returns_first_failure() -> None:
    """When multiple filters fail, the first one is the blocking reason."""
    filters = (
        HardFilter(name="visa", passed=False),
        HardFilter(name="location", passed=False),
    )
    verdict = determine_eligibility(
        score=90,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.HARD_FILTER_BLOCKED
    assert verdict.reason == "hard filter 'visa' failed"


def test_determine_eligibility_hard_filter_blocked_with_none_score() -> None:
    """Hard filter failure is checked before score availability."""
    filters = (HardFilter(name="location", passed=False),)
    verdict = determine_eligibility(
        score=None,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.HARD_FILTER_BLOCKED
    assert verdict.reason == "hard filter 'location' failed"
    assert verdict.score_used is None


def test_determine_eligibility_score_none_after_filters_pass() -> None:
    """When score is None after filters pass, result is INELIGIBLE."""
    verdict = determine_eligibility(
        score=None,
        threshold=50,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.INELIGIBLE
    assert verdict.reason == "score is not available"
    assert verdict.score_used is None


def test_determine_eligibility_score_none_with_all_passing_filters() -> None:
    filters = (HardFilter(name="location", passed=True),)
    verdict = determine_eligibility(
        score=None,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.INELIGIBLE
    assert verdict.reason == "score is not available"
    assert verdict.score_used is None


def test_determine_eligibility_eligible_score_meets_threshold() -> None:
    verdict = determine_eligibility(
        score=75,
        threshold=50,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.ELIGIBLE
    assert verdict.reason == "score 75 meets threshold 50"
    assert verdict.score_used == 75
    assert verdict.filter_results == ()


def test_determine_eligibility_eligible_score_exactly_threshold() -> None:
    verdict = determine_eligibility(
        score=50,
        threshold=50,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.ELIGIBLE
    assert verdict.reason == "score 50 meets threshold 50"
    assert verdict.score_used == 50


def test_determine_eligibility_eligible_all_filters_pass() -> None:
    filters = (
        HardFilter(name="location", passed=True),
        HardFilter(name="years_experience", passed=True),
    )
    verdict = determine_eligibility(
        score=80,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.ELIGIBLE
    assert verdict.reason == "score 80 meets threshold 50"
    assert verdict.score_used == 80
    assert verdict.filter_results == filters


def test_determine_eligibility_ineligible_below_threshold() -> None:
    verdict = determine_eligibility(
        score=30,
        threshold=50,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.INELIGIBLE
    assert verdict.reason == "score 30 below threshold 50"
    assert verdict.score_used == 30
    assert verdict.filter_results == ()


def test_determine_eligibility_ineligible_zero_score_below_threshold() -> None:
    verdict = determine_eligibility(
        score=0,
        threshold=50,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.INELIGIBLE
    assert verdict.reason == "score 0 below threshold 50"
    assert verdict.score_used == 0


def test_determine_eligibility_ineligible_filters_passed_but_score_too_low() -> None:
    filters = (HardFilter(name="location", passed=True),)
    verdict = determine_eligibility(
        score=40,
        threshold=50,
        hard_filters=filters,
    )
    assert verdict.decision is EligibilityDecision.INELIGIBLE
    assert verdict.reason == "score 40 below threshold 50"
    assert verdict.filter_results == filters


def test_determine_eligibility_eligible_high_score() -> None:
    verdict = determine_eligibility(
        score=100,
        threshold=1,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.ELIGIBLE
    assert verdict.reason == "score 100 meets threshold 1"
    assert verdict.score_used == 100


def test_determine_eligibility_zero_threshold_with_zero_score() -> None:
    """Zero meets threshold of zero."""
    verdict = determine_eligibility(
        score=0,
        threshold=0,
        hard_filters=(),
    )
    assert verdict.decision is EligibilityDecision.ELIGIBLE
    assert verdict.reason == "score 0 meets threshold 0"


def test_eligibility_verdict_immutable() -> None:
    verdict = determine_eligibility(
        score=80,
        threshold=50,
        hard_filters=(),
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        verdict.decision = "something"  # type: ignore[assignment]


def test_hard_filter_immutable() -> None:
    hf = HardFilter(name="location", passed=True)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        hf.name = "visa"  # type: ignore[assignment]


def test_eligibility_rule_immutable() -> None:
    flt = HardFilter(name="location", passed=True)
    rule = EligibilityRule(threshold=50, hard_filters=(flt,))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        rule.threshold = 100  # type: ignore[assignment]
