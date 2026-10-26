"""Aggregate overview endpoint (defaults to January 2026 analysis period)."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.calculator import calculate_analytics
from app.api.deps import get_fuelhh_client, get_windfor_client
from app.api.schemas import DayAccuracy, MetricsSummary, OverviewResponse
from app.api.service import fetch_and_evaluate
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["overview"])

_MAX_RANGE_DAYS = 31
_DEFAULT_FROM = date(2026, 1, 1)
_DEFAULT_TO = date(2026, 1, 31)


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Aggregate accuracy overview (defaults to January 2026)",
    responses={
        422: {"description": "Invalid date range"},
        502: {"description": "Upstream Elexon API error"},
        503: {"description": "Elexon API unreachable"},
    },
)
async def get_overview(
    from_date: date = Query(_DEFAULT_FROM, description="Start of range, inclusive (YYYY-MM-DD)"),
    to_date: date = Query(_DEFAULT_TO, description="End of range, inclusive (YYYY-MM-DD)"),
    cutoff_hour: int = Query(11, ge=0, le=23, description="Decision cutoff hour in UK local time"),
    windfor: WindForClient = Depends(get_windfor_client),
    fuelhh: FuelHHClient = Depends(get_fuelhh_client),
) -> OverviewResponse:
    if from_date > to_date:
        raise HTTPException(422, detail="from_date must be on or before to_date.")
    total_days = (to_date - from_date).days + 1
    if total_days > _MAX_RANGE_DAYS:
        raise HTTPException(
            422,
            detail=f"Date range must not exceed {_MAX_RANGE_DAYS} days; got {total_days}.",
        )

    days: list[DayAccuracy] = []
    failed_dates: list[str] = []
    all_hours = []

    current = from_date
    while current <= to_date:
        try:
            result, analytics = await fetch_and_evaluate(current, cutoff_hour, windfor, fuelhh)
            days.append(DayAccuracy.from_evaluation(result, analytics))
            all_hours.extend(result.hours)
        except ValueError as exc:
            logger.info("No vintage for %s: %s", current.isoformat(), exc)
            failed_dates.append(current.isoformat())
        current += timedelta(days=1)

    days_with_data = sum(1 for d in days if d.metrics.evaluation_hours > 0)

    aggregate_metrics: MetricsSummary | None = None
    if all_hours:
        agg = calculate_analytics(all_hours)
        aggregate_metrics = MetricsSummary.from_analytics(agg)

    return OverviewResponse(
        from_date=from_date,
        to_date=to_date,
        cutoff_hour=cutoff_hour,
        total_days=total_days,
        days_with_data=days_with_data,
        failed_dates=failed_dates,
        aggregate_metrics=aggregate_metrics,
        days=days,
    )
