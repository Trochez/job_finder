"""Unit tests for screening answer retrieval logic.

Tests the pure data-access functions in ``application/checkpoints.py``.
"""

from __future__ import annotations

import pytest

from job_finder.application.checkpoints import ScreeningAnswer, get_answer


class TestGetAnswer:
    """Coverage of exact-match screening answer retrieval."""

    def test_exact_match_returns_answer(self) -> None:
        answers = (
            ScreeningAnswer(question_key="years_experience", answer="5"),
            ScreeningAnswer(question_key="work_authorization", answer="yes"),
        )

        result = get_answer("years_experience", answers)

        assert result == "5"

    def test_no_match_returns_none(self) -> None:
        answers = (
            ScreeningAnswer(question_key="years_experience", answer="5"),
        )

        result = get_answer("unknown_question", answers)

        assert result is None

    def test_empty_answers_returns_none(self) -> None:
        result = get_answer("anything", ())

        assert result is None

    def test_case_sensitive_match(self) -> None:
        """Exact match means case-sensitive key comparison."""
        answers = (
            ScreeningAnswer(question_key="Years_Experience", answer="5"),
        )

        # Wrong case should not match
        assert get_answer("years_experience", answers) is None

        # Exact case should match
        assert get_answer("Years_Experience", answers) == "5"

    def test_multiple_answers_returns_first_match(self) -> None:
        answers = (
            ScreeningAnswer(question_key="q1", answer="a1"),
            ScreeningAnswer(question_key="q2", answer="a2"),
            ScreeningAnswer(question_key="q1", answer="a1-duplicate"),
        )

        result = get_answer("q1", answers)

        assert result == "a1"


class TestScreeningAnswerDataclass:
    """ScreeningAnswer is a simple frozen dataclass."""

    def test_fields(self) -> None:
        answer = ScreeningAnswer(question_key="q", answer="a")

        assert answer.question_key == "q"
        assert answer.answer == "a"

    def test_equality(self) -> None:
        a1 = ScreeningAnswer(question_key="q", answer="a")
        a2 = ScreeningAnswer(question_key="q", answer="a")

        assert a1 == a2

    def test_immutable(self) -> None:
        answer = ScreeningAnswer(question_key="q", answer="a")

        with pytest.raises(AttributeError):
            answer.question_key = "changed"  # type: ignore[reportAttributeAccessIssue]
