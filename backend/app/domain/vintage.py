"""Forecast vintage selection — pure domain logic, no I/O."""

import logging
from datetime import datetime

from app.domain.timestamps import ensure_utc
from app.models.windfor import WindForRecord

logger = logging.getLogger(__name__)


def deduplicate_windfor(records: list[WindForRecord]) -> list[WindForRecord]:
    """Remove duplicate (publishTime, startTime) pairs deterministically.

    When duplicates exist, the last record in input order is kept.
    Duplicates are logged at WARNING level.
    """
    seen: dict[tuple[datetime, datetime], WindForRecord] = {}
    for r in records:
        key = (r.publish_time, r.start_time)
        if key in seen:
            logger.warning(
                "Duplicate WINDFOR record at publishTime=%s startTime=%s — keeping latest",
                r.publish_time.isoformat(),
                r.start_time.isoformat(),
            )
        seen[key] = r  # last occurrence wins
    return list(seen.values())


def select_vintage(
    records: list[WindForRecord],
    cutoff_utc: datetime,
) -> tuple[datetime, list[WindForRecord]]:
    """Select the latest forecast vintage published at or before *cutoff_utc*.

    This is the core anti-look-ahead-bias function: no forecast published
    after the decision cutoff is ever returned.

    Args:
        records:     All candidate WINDFOR records (may span multiple vintages).
        cutoff_utc:  UTC-aware decision cutoff datetime.

    Returns:
        (selected_publish_time, records_for_that_vintage)

    Raises:
        ValueError: If *cutoff_utc* is naive.
        ValueError: If no records have publishTime <= cutoff_utc.
    """
    cutoff_utc = ensure_utc(cutoff_utc)

    deduped = deduplicate_windfor(records)
    eligible = [r for r in deduped if r.publish_time <= cutoff_utc]

    if not eligible:
        raise ValueError(
            f"No WINDFOR forecast vintage found at or before cutoff "
            f"{cutoff_utc.isoformat()}. "
            f"Earliest available publishTime: "
            f"{min(r.publish_time for r in deduped).isoformat() if deduped else 'none'}"
        )

    latest_pt = max(r.publish_time for r in eligible)
    vintage = [r for r in eligible if r.publish_time == latest_pt]

    logger.info(
        "select_vintage: cutoff=%s → selected publishTime=%s (%d records, %d vintages available)",
        cutoff_utc.isoformat(),
        latest_pt.isoformat(),
        len(vintage),
        len({r.publish_time for r in deduped}),
    )
    return latest_pt, vintage
