"""Shared helpers for interpreting bounded time ranges.

Available to any connector implementation; parsing/validation rules are
common enough across vendors to share, while each connector still decides
how results map onto its own data.
"""

from datetime import datetime, timezone

from .contracts import InvalidTimeRangeError
from .models import TimeRange


def parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidTimeRangeError(f"Invalid timestamp: {value}") from exc
    if timestamp.tzinfo is None:
        raise InvalidTimeRangeError(f"Timestamp must include timezone information: {value}")
    return timestamp.astimezone(timezone.utc)


def validate_time_range(time_range: TimeRange) -> tuple[datetime, datetime]:
    if "start" not in time_range or "end" not in time_range:
        raise InvalidTimeRangeError("Invalid time range: time_range must contain 'start' and 'end'.")

    start_dt = parse_iso8601(str(time_range["start"]))
    end_dt = parse_iso8601(str(time_range["end"]))
    if start_dt >= end_dt:
        raise InvalidTimeRangeError("Invalid time range: start must be earlier than end.")
    return start_dt, end_dt
