"""Integration tests for daily application cap accounting."""

from __future__ import annotations

import pytest

from job_finder.application.daily_cap import (
    ApplicationAttemptStarted,
    CapCounter,
    CapReached,
    DailyCapPolicy,
    InvalidCapLimitError,
    check_cap,
)
from job_finder.domain.ids import JobId, RunId


class TestDailyCapPolicy:
    """``DailyCapPolicy`` construction and validation."""

    def test_default_limit_is_25(self) -> None:
        policy = DailyCapPolicy()
        assert policy.limit == 25

    def test_custom_limit(self) -> None:
        policy = DailyCapPolicy(limit=10)
        assert policy.limit == 10

    def test_zero_limit_raises(self) -> None:
        with pytest.raises(InvalidCapLimitError, match="positive"):
            _ = DailyCapPolicy(limit=0)

    def test_negative_limit_raises(self) -> None:
        with pytest.raises(InvalidCapLimitError, match="positive"):
            _ = DailyCapPolicy(limit=-1)

    def test_limit_above_100_is_accepted(self) -> None:
        policy = DailyCapPolicy(limit=200)
        assert policy.limit == 200


class TestCapCounter:
    """``CapCounter`` attempt tracking."""

    def test_initial_count_is_zero(self) -> None:
        counter = CapCounter()
        assert counter.count_for(RunId("run-1")) == 0

    def test_single_attempt_increments(self) -> None:
        counter = CapCounter()
        event = ApplicationAttemptStarted(
            run_id=RunId("run-1"), job_id=JobId("job:abc"),
        )
        counter.record(event)
        assert counter.count_for(RunId("run-1")) == 1

    def test_multiple_attempts_accumulate(self) -> None:
        counter = CapCounter()
        run_id = RunId("run-1")
        for i in range(10):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_id, job_id=JobId(f"job:{i}"),
                ),
            )
        assert counter.count_for(run_id) == 10


class TestCheckCap:
    """``check_cap`` decision logic."""

    def test_under_cap_returns_true(self) -> None:
        policy = DailyCapPolicy(limit=5)
        counter = CapCounter()
        run_id = RunId("run-1")
        for _ in range(4):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_id, job_id=JobId("job:x"),
                ),
            )
        assert check_cap(policy, counter, run_id) is True

    def test_at_cap_returns_false(self) -> None:
        policy = DailyCapPolicy(limit=5)
        counter = CapCounter()
        run_id = RunId("run-1")
        for _ in range(5):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_id, job_id=JobId("job:x"),
                ),
            )
        assert check_cap(policy, counter, run_id) is False

    def test_exceeding_cap_returns_false(self) -> None:
        policy = DailyCapPolicy(limit=3)
        counter = CapCounter()
        run_id = RunId("run-1")
        for _ in range(6):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_id, job_id=JobId("job:x"),
                ),
            )
        assert check_cap(policy, counter, run_id) is False

    def test_default_25_works_26th_halts(self) -> None:
        policy = DailyCapPolicy()
        counter = CapCounter()
        run_id = RunId("run-default")
        for _ in range(25):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_id, job_id=JobId("job:ok"),
                ),
            )
        assert check_cap(policy, counter, run_id) is False

    def test_cap_is_per_run_not_global(self) -> None:
        policy = DailyCapPolicy(limit=3)
        counter = CapCounter()
        run_a = RunId("run-a")
        run_b = RunId("run-b")

        for _ in range(3):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_a, job_id=JobId("job:a"),
                ),
            )

        assert check_cap(policy, counter, run_a) is False
        # Run B has zero attempts — should still be allowed
        assert check_cap(policy, counter, run_b) is True

        # After a few on B
        for _ in range(2):
            counter.record(
                ApplicationAttemptStarted(
                    run_id=run_b, job_id=JobId("job:b"),
                ),
            )
        assert check_cap(policy, counter, run_b) is True

        # B hits the cap
        counter.record(
            ApplicationAttemptStarted(
                run_id=run_b, job_id=JobId("job:b3"),
            ),
        )
        assert check_cap(policy, counter, run_b) is False


class TestCapReachedEvent:
    """``CapReached`` event shape."""

    def test_event_holds_run_id_and_count(self) -> None:
        event = CapReached(run_id=RunId("run-99"), count=25)
        assert event.run_id == "run-99"
        assert event.count == 25
