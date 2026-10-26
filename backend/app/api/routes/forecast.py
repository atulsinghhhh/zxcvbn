"""Single-day forecast endpoint."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.api.schemas import ForecastResponse, HourDetail
from app.api.service import fetch_and_evaluate
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient

router = APIRouter(tags=["forecast"])


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Retrieve the selected forecast vintage for a delivery date",
    responses={
        404: {"description": "No forecast vintage available at the decision cutoff"},
        502: {"description": "Upstream Elexon API error"},
        503: {"description": "Elexon API unreachable"},
    },
)
async def get_forecast(
    delivery_date: date = Query(..., description="UK delivery date (YYYY-MM-DD)"),
    cutoff_hour: int = Query(
        11, ge=0, le=23, description="Decision cutoff hour in UK local time (0-23)"
    ),
    windfor: WindForClient = Depends(get_windfor_client),
    fuelhh: FuelHHClient = Depends(get_fuelhh_client),
) -> ForecastResponse:
    result, analytics = await fetch_and_evaluate(delivery_date, cutoff_hour, windfor, fuelhh)

    # Index interval errors by start_utc for O(1) lookup
    error_index = {e.start_utc: e for e in analytics.interval_errors}

    hours = [
        HourDetail.from_domain(hour, error_index.get(hour.start_utc))
        for hour in result.hours
    ]

    from app.api.schemas import MetricsSummary

    return ForecastResponse(
        delivery_date=result.delivery_date,
        decision_cutoff_utc=result.decision_cutoff_utc,
        selected_vintage_utc=result.selected_vintage_utc,
        metrics=MetricsSummary.from_analytics(analytics),
        hours=hours,
    )
