"""Paginated hourly interval endpoint for a single delivery day."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.api.schemas import HourDetail, IntervalsResponse
from app.api.service import fetch_and_evaluate
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient

router = APIRouter(tags=["intervals"])


@router.get(
    "/intervals",
    response_model=IntervalsResponse,
    summary="Paginated hourly forecast/actual intervals for a delivery date",
    responses={
        404: {"description": "No forecast vintage available at the decision cutoff"},
        502: {"description": "Upstream Elexon API error"},
        503: {"description": "Elexon API unreachable"},
    },
)
async def get_intervals(
    delivery_date: date = Query(..., description="UK delivery date (YYYY-MM-DD)"),
    cutoff_hour: int = Query(11, ge=0, le=23, description="Decision cutoff hour in UK local time"),
    offset: int = Query(0, ge=0, description="Number of hours to skip"),
    limit: int = Query(25, ge=1, le=50, description="Maximum hours to return (1–50)"),
    windfor: WindForClient = Depends(get_windfor_client),
    fuelhh: FuelHHClient = Depends(get_fuelhh_client),
) -> IntervalsResponse:
    result, analytics = await fetch_and_evaluate(delivery_date, cutoff_hour, windfor, fuelhh)

    error_index = {e.start_utc: e for e in analytics.interval_errors}
    all_hours = [
        HourDetail.from_domain(hour, error_index.get(hour.start_utc))
        for hour in result.hours
    ]

    page = all_hours[offset : offset + limit]

    return IntervalsResponse(
        delivery_date=result.delivery_date,
        decision_cutoff_utc=result.decision_cutoff_utc,
        selected_vintage_utc=result.selected_vintage_utc,
        total=len(all_hours),
        offset=offset,
        limit=limit,
        hours=page,
    )
