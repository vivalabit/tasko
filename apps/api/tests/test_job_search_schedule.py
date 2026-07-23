from datetime import UTC, datetime, time

import pytest

from app.services.job_search_schedule import (
    JobSearchScheduleValidationError,
    calculate_next_run_at,
)


def next_run(
    *,
    now: datetime,
    frequency: str = "daily",
    weekdays: list[int] | None = None,
    local_time: time = time(7, 30),
    timezone: str = "Europe/Zurich",
) -> datetime:
    return calculate_next_run_at(
        frequency=frequency,
        weekdays=weekdays,
        local_time=local_time,
        timezone=timezone,
        now=now,
    )


def test_daily_schedule_uses_today_or_tomorrow() -> None:
    assert next_run(now=datetime(2026, 7, 20, 4, 0, tzinfo=UTC)) == datetime(
        2026,
        7,
        20,
        5,
        30,
        tzinfo=UTC,
    )
    assert next_run(now=datetime(2026, 7, 20, 6, 0, tzinfo=UTC)) == datetime(
        2026,
        7,
        21,
        5,
        30,
        tzinfo=UTC,
    )


def test_weekday_schedule_skips_the_weekend() -> None:
    assert next_run(
        now=datetime(2026, 7, 17, 6, 0, tzinfo=UTC),
        frequency="weekdays",
    ) == datetime(2026, 7, 20, 5, 30, tzinfo=UTC)


def test_selected_days_schedule_uses_python_weekday_numbers() -> None:
    assert next_run(
        now=datetime(2026, 7, 20, 6, 0, tzinfo=UTC),
        frequency="selected_days",
        weekdays=[2, 6],
    ) == datetime(2026, 7, 22, 5, 30, tzinfo=UTC)


def test_spring_dst_transition_keeps_zurich_wall_clock_time() -> None:
    before_transition = next_run(
        now=datetime(2026, 3, 27, 7, 0, tzinfo=UTC),
    )
    after_transition = next_run(now=before_transition)

    assert before_transition == datetime(2026, 3, 28, 6, 30, tzinfo=UTC)
    assert after_transition == datetime(2026, 3, 29, 5, 30, tzinfo=UTC)


def test_nonexistent_spring_time_moves_forward_by_the_dst_gap() -> None:
    assert next_run(
        now=datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
        local_time=time(2, 30),
    ) == datetime(2026, 3, 29, 1, 30, tzinfo=UTC)


def test_autumn_dst_transition_runs_ambiguous_time_only_once() -> None:
    first_occurrence = next_run(
        now=datetime(2026, 10, 24, 12, 0, tzinfo=UTC),
        local_time=time(2, 30),
    )
    following_run = next_run(
        now=first_occurrence,
        local_time=time(2, 30),
    )

    assert first_occurrence == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    assert following_run == datetime(2026, 10, 26, 1, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"timezone": "Mars/Olympus"}, "timezone is invalid"),
        ({"timezone": ""}, "timezone is required"),
        ({"local_time": None}, "local_time must be a valid local time"),
        (
            {"local_time": time(7, 30, tzinfo=UTC)},
            "local_time must be a valid local time",
        ),
        (
            {"frequency": "selected_days", "weekdays": []},
            "weekdays must not be empty",
        ),
        (
            {"frequency": "selected_days", "weekdays": [7]},
            "weekdays must contain integers from 0 to 6",
        ),
        ({"frequency": "monthly"}, "frequency must be"),
    ],
)
def test_schedule_validation_rejects_invalid_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    arguments = {
        "now": datetime(2026, 7, 20, 4, 0, tzinfo=UTC),
        "frequency": "daily",
        "weekdays": [],
        "local_time": time(7, 30),
        "timezone": "Europe/Zurich",
        **overrides,
    }
    with pytest.raises(JobSearchScheduleValidationError, match=message):
        calculate_next_run_at(**arguments)


def test_schedule_validation_rejects_naive_reference_time() -> None:
    with pytest.raises(JobSearchScheduleValidationError, match="timezone-aware"):
        next_run(now=datetime(2026, 7, 20, 4, 0))
