"""Internal domain models for forecast evaluation.

These are dataclasses, not Pydantic models — they represent processed results
inside the application, not wire-format API records.
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class DeliveryHour:
    """One delivery hour with paired forecast and actual.

    forecast_mw: None if no WINDFOR record covers this hour.
    actual_mw:   None if one or both FUELHH half-hours are absent.
    Both being non-None is required for inclusion in error metrics.
    """

    start_utc: datetime          # UTC start of the hour (always UTC-aware)
    start_uk: datetime           # UK local start (for display; may be BST or GMT)
    forecast_mw: float | None    # Selected vintage forecast in MW
    actual_mw: float | None      # Average of two half-hourly actuals in MW
    selected_vintage_time: datetime  # publishTime of the chosen forecast vintage


@dataclass
class EvaluationResult:
    """Matched delivery hours for a single UK delivery date.

    Phase 2 output: contains only matched records and the metadata needed to
    reproduce the selection (delivery_date, decision_cutoff_utc,
    selected_vintage_utc).  Metric calculations (MAE, RMSE, bias, percentiles)
    belong in Phase 3 — analytics/calculator.py::calculate_analytics.
    """

    delivery_date: date
    decision_cutoff_utc: datetime    # cutoff used to select the vintage
    selected_vintage_utc: datetime   # publishTime of the selected forecast

    hours: list[DeliveryHour] = field(default_factory=list)
