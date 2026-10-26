"""Top-level day evaluation orchestrator.

Combines timestamp logic, vintage selection, and matching into a single
callable that takes raw API records and returns an EvaluationResult.

Phase 2 responsibility ends here: the result contains matched DeliveryHour
records and the metadata needed to reproduce the selection.  Metric
calculations (MAE, RMSE, bias, percentiles) are Phase 3 work and belong in
analytics/calculator.py::calculate_analytics.

This module has no I/O dependencies — it does not call the Elexon API.
Callers are responsible for providing pre-fetched records.
"""

import logging
from datetime import date, datetime

from app.domain.matcher import fuelhh_to_hourly, match_records
from app.domain.models import EvaluationResult
from app.domain.timestamps import decision_cutoff_utc as _default_cutoff
from app.domain.vintage import select_vintage
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

logger = logging.getLogger(__name__)


def evaluate_day(
    delivery_date: date,
    forecast_records: list[WindForRecord],
    actual_records: list[FuelHHRecord],
    cutoff_utc: datetime | None = None,
    cutoff_hour: int = 11,
) -> EvaluationResult:
    """Select the correct forecast vintage and match it with actuals.

    Args:
        delivery_date:    UK calendar date being evaluated.
        forecast_records: All WINDFOR records available (may span multiple vintages
                          and delivery days; the function filters internally).
        actual_records:   FUELHH WIND records (may span multiple dates).
        cutoff_utc:       Explicit decision cutoff (UTC-aware).  If None, the
                          default is computed as cutoff_hour:00 UK local on the
                          preceding calendar day.
        cutoff_hour:      Hour of the cutoff in UK local time (default 11).

    Returns:
        EvaluationResult with delivery metadata and matched hours.
        Pass result.hours to analytics.calculator.calculate_analytics for metrics.

    Raises:
        ValueError: If no eligible forecast vintage exists at or before the cutoff.
    """
    if cutoff_utc is None:
        cutoff_utc = _default_cutoff(delivery_date, cutoff_hour)

    logger.info(
        "evaluate_day: delivery=%s cutoff=%s",
        delivery_date.isoformat(),
        cutoff_utc.isoformat(),
    )

    selected_pt, vintage = select_vintage(forecast_records, cutoff_utc)
    actual_hourly = fuelhh_to_hourly(actual_records, delivery_date)
    hours = match_records(vintage, actual_hourly, selected_pt)

    return EvaluationResult(
        delivery_date=delivery_date,
        decision_cutoff_utc=cutoff_utc,
        selected_vintage_utc=selected_pt,
        hours=hours,
    )
