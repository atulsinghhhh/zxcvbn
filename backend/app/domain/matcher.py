"""Matching forecast records to actuals by delivery interval.

WINDFOR is hourly; FUELHH is half-hourly.  To compare on a common basis each
WINDFOR hour is paired with the mean of the two FUELHH half-hour periods whose
startTime falls within that hour ([hour_start, hour_start+30min]).

If either half-hour is absent the actual for that hour is None and the hour is
excluded from error metrics (not imputed).

Unresolved ambiguity:
    WINDFOR startTime is the *start* of the forecast hour.  The Elexon data
    dictionary does not state whether the value represents the average or
    instantaneous generation over the hour.  We assume it is an average, which
    is consistent with FUELHH.  If it is instantaneous, the comparison is
    still directionally valid but not precisely like-for-like.
"""

import logging
from datetime import date, datetime, timedelta

from app.domain.models import DeliveryHour
from app.domain.timestamps import delivery_window_utc, ensure_utc, to_uk
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

logger = logging.getLogger(__name__)


def deduplicate_fuelhh(records: list[FuelHHRecord]) -> list[FuelHHRecord]:
    """Remove duplicate (settlementDate, settlementPeriod) pairs.

    When duplicates exist, keep the record with the latest publishTime, which
    is the most recently corrected value.  Ties are broken by input order
    (last occurrence kept).
    """
    best: dict[tuple[str, int], FuelHHRecord] = {}
    for r in records:
        key = (r.settlement_date, r.settlement_period)
        existing = best.get(key)
        if existing is None or r.publish_time >= existing.publish_time:
            if existing is not None and r.publish_time == existing.publish_time:
                logger.warning(
                    "Duplicate FUELHH record with identical publishTime: "
                    "settlementDate=%s period=%d — keeping later occurrence",
                    r.settlement_date,
                    r.settlement_period,
                )
            elif existing is not None:
                logger.warning(
                    "Duplicate FUELHH record: settlementDate=%s period=%d — "
                    "replacing publishTime=%s with %s",
                    r.settlement_date,
                    r.settlement_period,
                    existing.publish_time.isoformat(),
                    r.publish_time.isoformat(),
                )
            best[key] = r
    return list(best.values())


def fuelhh_to_hourly(
    records: list[FuelHHRecord],
    delivery_date: date,
) -> dict[datetime, float | None]:
    """Aggregate FUELHH half-hours to hourly actuals for *delivery_date*.

    Returns a mapping {hour_start_utc: avg_mw_or_None} covering every hour
    in the UK delivery window.  None means one or both half-hours were absent.

    The UK delivery window is [uk_midnight, next_uk_midnight) which is 23, 24,
    or 25 hours depending on DST transitions.

    Args:
        records:       FUELHH records.  All records must have fuel_type "WIND".
                       Passing mixed-fuel records is a programming error and
                       raises ValueError.
        delivery_date: UK calendar date for which actuals are aggregated.

    Raises:
        ValueError: If any record has a fuel_type other than "WIND".
    """
    non_wind = [r.fuel_type for r in records if r.fuel_type != "WIND"]
    if non_wind:
        raise ValueError(
            f"fuelhh_to_hourly expects only WIND records; "
            f"got unexpected fuel types: {sorted(set(non_wind))}"
        )

    window_start, window_end = delivery_window_utc(delivery_date)
    deduped = deduplicate_fuelhh(records)

    # Index all deduped records by their UTC startTime
    by_start: dict[datetime, float] = {}
    for r in deduped:
        st = ensure_utc(r.start_time)
        if window_start <= st < window_end:
            by_start[st] = r.generation

    hourly: dict[datetime, float | None] = {}
    current = window_start
    while current < window_end:
        half1_start = current
        half2_start = current + timedelta(minutes=30)
        g1 = by_start.get(half1_start)
        g2 = by_start.get(half2_start)

        if g1 is not None and g2 is not None:
            hourly[current] = (g1 + g2) / 2.0
        else:
            hourly[current] = None
            missing = []
            if g1 is None:
                missing.append(half1_start.isoformat())
            if g2 is None:
                missing.append(half2_start.isoformat())
            logger.debug("FUELHH: missing half-hours %s", missing)

        current += timedelta(hours=1)

    return hourly


def match_records(
    vintage_records: list[WindForRecord],
    actual_hourly: dict[datetime, float | None],
    selected_vintage_time: datetime,
) -> list[DeliveryHour]:
    """Pair each delivery hour's forecast with its actual.

    Iterates over the delivery window (keys of *actual_hourly*) in chronological
    order.  For each hour:
      - forecast_mw: from the selected vintage (None if that hour is not covered).
      - actual_mw:   from *actual_hourly* (may be None for missing actuals).

    Hours present only in the forecast (outside the delivery window) are ignored.

    Args:
        vintage_records:       Records from the single selected vintage.
        actual_hourly:         Output of fuelhh_to_hourly().
        selected_vintage_time: publishTime of the chosen vintage (stored on each hour).

    Returns:
        List of DeliveryHour in chronological order by start_utc.
    """
    # Index forecast by startTime; duplicates within a vintage are already removed
    # upstream by deduplicate_windfor.  If somehow still present, last wins.
    forecast_index: dict[datetime, float] = {}
    for r in vintage_records:
        forecast_index[ensure_utc(r.start_time)] = r.generation

    hours: list[DeliveryHour] = []
    for hour_start in sorted(actual_hourly.keys()):
        hours.append(
            DeliveryHour(
                start_utc=hour_start,
                start_uk=to_uk(hour_start),
                forecast_mw=forecast_index.get(hour_start),
                actual_mw=actual_hourly[hour_start],
                selected_vintage_time=selected_vintage_time,
            )
        )
    return hours
