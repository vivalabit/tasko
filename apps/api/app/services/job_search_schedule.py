from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DAILY = "daily"
WEEKDAYS = "weekdays"
SELECTED_DAYS = "selected_days"
SUPPORTED_FREQUENCIES = frozenset({DAILY, WEEKDAYS, SELECTED_DAYS})


class JobSearchScheduleValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedJobSearchSchedule:
    frequency: str
    weekdays: frozenset[int]
    local_time: time
    timezone: ZoneInfo


def validate_search_schedule(
    *,
    frequency: str,
    weekdays: Sequence[int] | None,
    local_time: time,
    timezone: str,
) -> ValidatedJobSearchSchedule:
    """Validate a schedule; weekday numbers follow datetime.weekday (Monday is 0)."""
    if frequency not in SUPPORTED_FREQUENCIES:
        raise JobSearchScheduleValidationError(
            "frequency must be daily, weekdays, or selected_days"
        )
    if not isinstance(local_time, time) or local_time.tzinfo is not None:
        raise JobSearchScheduleValidationError("local_time must be a valid local time")
    if not isinstance(timezone, str) or not timezone.strip():
        raise JobSearchScheduleValidationError("timezone is required")
    try:
        zone = ZoneInfo(timezone.strip())
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise JobSearchScheduleValidationError("timezone is invalid") from exc

    normalized_weekdays = _validate_weekdays(weekdays)
    if frequency == DAILY:
        allowed_weekdays = frozenset(range(7))
    elif frequency == WEEKDAYS:
        allowed_weekdays = frozenset(range(5))
    else:
        if not normalized_weekdays:
            raise JobSearchScheduleValidationError("weekdays must not be empty for selected_days")
        allowed_weekdays = normalized_weekdays

    return ValidatedJobSearchSchedule(
        frequency=frequency,
        weekdays=allowed_weekdays,
        local_time=local_time,
        timezone=zone,
    )


def calculate_next_run_at(
    *,
    frequency: str,
    weekdays: Sequence[int] | None,
    local_time: time,
    timezone: str,
    now: datetime | None = None,
) -> datetime:
    """Return the first UTC run strictly after now.

    Ambiguous fall-back times use the first occurrence. Nonexistent spring-forward
    times move forward by the DST gap, preserving minutes.
    """
    schedule = validate_search_schedule(
        frequency=frequency,
        weekdays=weekdays,
        local_time=local_time,
        timezone=timezone,
    )
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise JobSearchScheduleValidationError("now must be timezone-aware")
    reference_utc = reference.astimezone(UTC)
    local_date = reference_utc.astimezone(schedule.timezone).date()

    for day_offset in range(8):
        candidate_date = local_date + timedelta(days=day_offset)
        if candidate_date.weekday() not in schedule.weekdays:
            continue
        candidate = _resolve_local_datetime(
            candidate_date,
            schedule.local_time,
            schedule.timezone,
        ).astimezone(UTC)
        if candidate > reference_utc:
            return candidate

    raise RuntimeError("Unable to calculate the next job search run")


def _validate_weekdays(weekdays: Sequence[int] | None) -> frozenset[int]:
    normalized: set[int] = set()
    for weekday in weekdays or ():
        if isinstance(weekday, bool) or not isinstance(weekday, int):
            raise JobSearchScheduleValidationError("weekdays must contain integers from 0 to 6")
        if weekday < 0 or weekday > 6:
            raise JobSearchScheduleValidationError("weekdays must contain integers from 0 to 6")
        normalized.add(weekday)
    return frozenset(normalized)


def _resolve_local_datetime(
    local_date: date,
    local_time: time,
    timezone: ZoneInfo,
) -> datetime:
    naive = datetime.combine(local_date, local_time)
    valid_candidates: dict[datetime, datetime] = {}
    normalized_candidates: list[datetime] = []

    for fold in (0, 1):
        candidate = naive.replace(tzinfo=timezone, fold=fold)
        round_trip = candidate.astimezone(UTC).astimezone(timezone)
        if round_trip.replace(tzinfo=None) == naive:
            valid_candidates[candidate.astimezone(UTC)] = candidate
        elif round_trip.replace(tzinfo=None) > naive:
            normalized_candidates.append(round_trip)

    if valid_candidates:
        earliest_utc = min(valid_candidates)
        return valid_candidates[earliest_utc]
    if normalized_candidates:
        return min(
            normalized_candidates,
            key=lambda candidate: candidate.replace(tzinfo=None),
        )
    raise RuntimeError("Unable to resolve local job search time")
