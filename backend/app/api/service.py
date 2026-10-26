"""Orchestration layer: fetch raw data, evaluate, calculate analytics."""

from __future__ import annotations

from datetime import date, timedelta

from starlette.concurrency import run_in_threadpool

from app.analytics.calculator import calculate_analytics
from app.analytics.models import ForecastAnalytics
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.domain.evaluator import evaluate_day
from app.domain.models import EvaluationResult
from app.domain.timestamps import decision_cutoff_utc, delivery_window_utc

_WINDFOR_LOOKBACK_HOURS = 48
_FUELHH_PUBLISH_BUFFER_HOURS = 24


async def fetch_and_evaluate(
    delivery_date: date,
    cutoff_hour: int,
    windfor: WindForClient,
    fuelhh: FuelHHClient,
) -> tuple[EvaluationResult, ForecastAnalytics]:
    """Fetch raw records, select the correct vintage, match with actuals, compute analytics.

    Raises:
        ValueError: No eligible forecast vintage at or before the decision cutoff.
        ElexonClientError: Any upstream HTTP/network/validation failure.
    """
    cutoff_utc = decision_cutoff_utc(delivery_date, cutoff_hour)
    window_start, window_end = delivery_window_utc(delivery_date)

    forecast_records = await run_in_threadpool(
        windfor.fetch,
        cutoff_utc - timedelta(hours=_WINDFOR_LOOKBACK_HOURS),
        cutoff_utc,
    )
    actual_records = await run_in_threadpool(
        fuelhh.fetch,
        window_start,
        window_end + timedelta(hours=_FUELHH_PUBLISH_BUFFER_HOURS),
    )

    result = evaluate_day(
        delivery_date=delivery_date,
        forecast_records=forecast_records,
        actual_records=actual_records,
        cutoff_utc=cutoff_utc,
    )
    analytics = calculate_analytics(result.hours)
    return result, analytics
