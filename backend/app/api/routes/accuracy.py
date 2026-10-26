"""Multi-day forecast accuracy endpoint."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.api.schemas import AccuracyResponse, DayAccuracy
from app.api.service import evaluate_date_range
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["accuracy"])

_MAX_RANGE_DAYS = 31


@router.get(
    "/accuracy",
    response_model=AccuracyResponse,
    summary="Forecast accuracy metrics over a date range",
    responses={
        422: {"description": "Invalid date range"},
        502: {"description": "Upstream Elexon API error"},
        503: {"description": "Elexon API unreachable"},
    },
)
async def get_accuracy(
    from_date: date = Query(..., description="Start of range, inclusive (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End of range, inclusive (YYYY-MM-DD)"),
    cutoff_hour: int = Query(11, ge=0, le=23, description="Decision cutoff hour in UK local time"),
    windfor: WindForClient = Depends(get_windfor_client),
    fuelhh: FuelHHClient = Depends(get_fuelhh_client),
) -> AccuracyResponse:
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

    for day, result, analytics in await evaluate_date_range(
        from_date, to_date, cutoff_hour, windfor, fuelhh
    ):
        if result is None or analytics is None:
            failed_dates.append(day.isoformat())
        else:
            days.append(DayAccuracy.from_evaluation(result, analytics))

    days_with_data = sum(1 for d in days if d.metrics.evaluation_hours > 0)

    return AccuracyResponse(
        from_date=from_date,
        to_date=to_date,
        cutoff_hour=cutoff_hour,
        total_days=total_days,
        days_with_data=days_with_data,
        failed_dates=failed_dates,
        days=days,
    )
