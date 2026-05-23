"""Small time helpers shared across the API."""

from datetime import datetime, timezone


def ensure_utc(value: datetime | None) -> datetime | None:
    """Treat a timezone-naive datetime as UTC.

    Query-string datetimes can arrive without an offset. Comparing a naive value
    against the timezone-aware stored timestamps raises, so we normalize here.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
