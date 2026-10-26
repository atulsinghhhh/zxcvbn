"""Pydantic response schemas for the WindSight API."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.analytics.models import ForecastAnalytics, IntervalError
    from app.domain.models import DeliveryHour, EvaluationResult


class ErrorResponse(BaseModel):
    error: str
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class HourDetail(BaseModel):
    start_utc: datetime
    start_uk: datetime
    forecast_mw: float | None
    actual_mw: float | None
    signed_error_mw: float | None = Field(None)
    abs_error_mw: float | None = Field(None)

    @classmethod
    def from_domain(cls, hour: DeliveryHour, error: IntervalError | None = None) -> HourDetail:
        return cls(
            start_utc=hour.start_utc,
            start_uk=hour.start_uk,
            forecast_mw=hour.forecast_mw,
            actual_mw=hour.actual_mw,
            signed_error_mw=error.signed_error_mw if error else None,
            abs_error_mw=error.abs_error_mw if error else None,
        )


class MetricsSummary(BaseModel):
    total_hours: int
    evaluation_hours: int
    missing_forecast_hours: int
    missing_actual_hours: int
    invalid_hours: int
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    max_abs_error_mw: float | None = None
    min_abs_error_mw: float | None = None
    p90_abs_error_mw: float | None = None
    max_signed_error_mw: float | None = None
    min_signed_error_mw: float | None = None

    @classmethod
    def from_analytics(cls, a: ForecastAnalytics) -> MetricsSummary:
        return cls(
            total_hours=a.total_hours,
            evaluation_hours=a.evaluation_hours,
            missing_forecast_hours=a.missing_forecast_hours,
            missing_actual_hours=a.missing_actual_hours,
            invalid_hours=a.invalid_hours,
            mae_mw=a.mae_mw,
            rmse_mw=a.rmse_mw,
            bias_mw=a.bias_mw,
            max_abs_error_mw=a.max_abs_error_mw,
            min_abs_error_mw=a.min_abs_error_mw,
            p90_abs_error_mw=a.p90_abs_error_mw,
            max_signed_error_mw=a.max_signed_error_mw,
            min_signed_error_mw=a.min_signed_error_mw,
        )


class ForecastResponse(BaseModel):
    delivery_date: date
    decision_cutoff_utc: datetime
    selected_vintage_utc: datetime
    metrics: MetricsSummary
    hours: list[HourDetail]


class DayAccuracy(BaseModel):
    delivery_date: date
    decision_cutoff_utc: datetime
    selected_vintage_utc: datetime
    metrics: MetricsSummary

    @classmethod
    def from_evaluation(
        cls, result: EvaluationResult, analytics: ForecastAnalytics
    ) -> DayAccuracy:
        return cls(
            delivery_date=result.delivery_date,
            decision_cutoff_utc=result.decision_cutoff_utc,
            selected_vintage_utc=result.selected_vintage_utc,
            metrics=MetricsSummary.from_analytics(analytics),
        )


class AccuracyResponse(BaseModel):
    from_date: date
    to_date: date
    cutoff_hour: int
    total_days: int
    days_with_data: int
    failed_dates: list[str] = Field(
        default_factory=list,
        description="Dates skipped due to missing forecast vintage.",
    )
    days: list[DayAccuracy]


class OverviewResponse(BaseModel):
    from_date: date
    to_date: date
    cutoff_hour: int
    total_days: int
    days_with_data: int
    failed_dates: list[str] = Field(default_factory=list)
    aggregate_metrics: MetricsSummary | None = None
    days: list[DayAccuracy]


class IntervalsResponse(BaseModel):
    delivery_date: date
    decision_cutoff_utc: datetime
    selected_vintage_utc: datetime
    total: int
    offset: int
    limit: int
    hours: list[HourDetail]
