"""Orchestration layer: fetch raw data, evaluate, calculate analytics."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from starlette.concurrency import run_in_threadpool

from app.analytics.calculator import calculate_analytics
from app.analytics.models import ForecastAnalytics
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.domain.evaluator import evaluate_day
from app.domain.models import EvaluationResult
from app.domain.timestamps import decision_cutoff_utc, delivery_window_utc

logger = logging.getLogger(__name__)

_WINDFOR_LOOKBACK_HOURS = 48
_FUELHH_PUBLISH_BUFFER_HOURS = 24

# Max days fetched from Elexon in parallel. Keeps multi-day ranges fast while
# staying polite to the upstream API (and within the threadpool budget).
_RANGE_CONCURRENCY = 8

# Per-day outcome: (day, result, analytics) on success, or (day, None, None)
# when no eligible forecast vintage exists for that day.
DayOutcome = tuple[date, EvaluationResult | None, ForecastAnalytics | None]


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


async def evaluate_date_range(
    from_date: date,
    to_date: date,
    cutoff_hour: int,
    windfor: WindForClient,
    fuelhh: FuelHHClient,
) -> list[DayOutcome]:
    """Evaluate every day in [from_date, to_date], fetching days concurrently.

    Days are evaluated in parallel (bounded by ``_RANGE_CONCURRENCY``). Results
    are returned in chronological order. A day with no eligible forecast vintage
    yields ``(day, None, None)``; any upstream (ElexonClientError) failure
    propagates and aborts the range.
    """
    semaphore = asyncio.Semaphore(_RANGE_CONCURRENCY)

    async def _one(day: date) -> DayOutcome:
        async with semaphore:
            try:
                result, analytics = await fetch_and_evaluate(day, cutoff_hour, windfor, fuelhh)
            except ValueError as exc:
                logger.info("No vintage for %s: %s", day.isoformat(), exc)
                return day, None, None
            return day, result, analytics

    days = [from_date + timedelta(days=offset) for offset in range((to_date - from_date).days + 1)]
    return await asyncio.gather(*(_one(day) for day in days))
