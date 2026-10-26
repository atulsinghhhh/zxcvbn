"""UTC / UK-local timestamp utilities.

All functions require timezone-aware datetimes.  Naive datetimes are rejected
explicitly to prevent silent offset errors.

Assumption: the day-ahead decision cutoff is cutoff_hour:00 UK local time on
the calendar day before the delivery date.  The default of 11:00 approximates
the N2EX/EPEX Spot day-ahead gate closure but is NOT a claimed market rule —
callers should treat it as a configurable convention.

DST is handled via zoneinfo.ZoneInfo("Europe/London"):
  - GMT (UTC+0): in effect from the last Sunday of October to the last Sunday
    of March.  All January 2026 dates fall here; 11:00 UK = 11:00 UTC.
  - BST (UTC+1): in effect from the last Sunday of March to the last Sunday
    of October.  11:00 UK = 10:00 UTC.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")
UTC = UTC


def ensure_utc(dt: datetime) -> datetime:
    """Return *dt* converted to UTC.  Raises ValueError for naive datetimes."""
    if dt.tzinfo is None:
        raise ValueError(
            f"Naive datetime is not allowed; received {dt!r}. "
            "Supply a UTC-aware datetime (e.g. datetime(..., tzinfo=timezone.utc))."
        )
    return dt.astimezone(UTC)


def to_uk(dt: datetime) -> datetime:
    """Convert any UTC-aware datetime to UK local (GMT or BST as appropriate)."""
    return ensure_utc(dt).astimezone(UK_TZ)


def uk_midnight_utc(uk_date: date) -> datetime:
    """Return the UTC instant of midnight at the start of *uk_date* in UK local time.

    Examples:
        uk_midnight_utc(date(2026, 1, 2)) → datetime(2026, 1, 2, 0, 0, tzinfo=UTC)   # GMT
        uk_midnight_utc(date(2026, 7, 2)) → datetime(2026, 7, 1, 23, 0, tzinfo=UTC)  # BST
    """
    midnight_uk = datetime(uk_date.year, uk_date.month, uk_date.day, 0, 0, 0, tzinfo=UK_TZ)
    return midnight_uk.astimezone(UTC)


def decision_cutoff_utc(delivery_date: date, cutoff_hour: int = 11) -> datetime:
    """Return the decision cutoff as a UTC datetime.

    The cutoff is defined as cutoff_hour:00 UK local time on the calendar day
    immediately before *delivery_date*.

    Args:
        delivery_date: The UK calendar date of the delivery day being purchased.
        cutoff_hour:   Hour of the cutoff in UK local time (0–23). Default 11.

    Returns:
        UTC-aware datetime of the cutoff instant.

    Raises:
        ValueError: If cutoff_hour is outside [0, 23].
    """
    if not (0 <= cutoff_hour <= 23):
        raise ValueError(f"cutoff_hour must be 0–23; got {cutoff_hour}")

    preceding_day = delivery_date - timedelta(days=1)
    cutoff_uk = datetime(
        preceding_day.year,
        preceding_day.month,
        preceding_day.day,
        cutoff_hour,
        0,
        0,
        tzinfo=UK_TZ,
    )
    return cutoff_uk.astimezone(UTC)


def delivery_window_utc(delivery_date: date) -> tuple[datetime, datetime]:
    """Return [window_start, window_end) in UTC for the UK calendar day.

    The window spans from midnight at the start of delivery_date to midnight
    at the start of the following day, both in UK local time.

    On DST transition days the window is not 24 hours:
      - Spring forward (March): 23 hours.
      - Fall back (October):    25 hours.
    """
    start = uk_midnight_utc(delivery_date)
    end = uk_midnight_utc(delivery_date + timedelta(days=1))
    return start, end
