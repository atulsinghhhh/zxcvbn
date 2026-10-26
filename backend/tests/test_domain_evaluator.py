"""Integration tests for the evaluate_day orchestrator.

evaluate_day is Phase 2: it selects the correct forecast vintage and matches
it to actuals by delivery interval.  It does NOT compute metrics — pass
result.hours to analytics.calculator.calculate_analytics for MAE/RMSE/bias.
"""

from datetime import date, datetime, timedelta

import pytest

from app.domain.evaluator import evaluate_day
from app.domain.models import EvaluationResult
from app.domain.timestamps import UTC
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

JAN2 = date(2026, 1, 2)

# Decision cutoff for Jan 2 delivery: 11:00 UK local on Jan 1 = 11:00 UTC (GMT)
JAN2_CUTOFF = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


def make_fhh(period: int, generation: float) -> FuelHHRecord:
    offset_mins = (period - 1) * 30
    start = datetime(2026, 1, 2, 0, 0, tzinfo=UTC) + timedelta(minutes=offset_mins)
    publish = start + timedelta(minutes=30)
    return FuelHHRecord.model_validate(
        {
            "dataset": "FUELHH",
            "publishTime": publish.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "settlementDate": "2026-01-02",
            "settlementPeriod": period,
            "fuelType": "WIND",
            "generation": generation,
        }
    )


def make_wf(publish_time: str, start_iso: str, generation: float) -> WindForRecord:
    return WindForRecord.model_validate(
        {
            "dataset": "WINDFOR",
            "publishTime": publish_time,
            "startTime": start_iso,
            "generation": generation,
        }
    )


def make_wf_hour(publish_time: str, hour: int, generation: float) -> WindForRecord:
    start = datetime(2026, 1, 2, hour, 0, tzinfo=UTC)
    return make_wf(publish_time, start.strftime("%Y-%m-%dT%H:%M:%SZ"), generation)


def perfect_actuals(gen: float = 14000.0) -> list[FuelHHRecord]:
    return [make_fhh(sp, gen) for sp in range(1, 49)]


def perfect_forecast(publish_time: str, gen: float = 14000.0) -> list[WindForRecord]:
    return [make_wf_hour(publish_time, h, gen) for h in range(24)]


# ---------------------------------------------------------------------------
# Basic end-to-end
# ---------------------------------------------------------------------------


def test_evaluate_day_returns_result_type():
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z"),
        perfect_actuals(),
        cutoff_utc=JAN2_CUTOFF,
    )
    assert isinstance(result, EvaluationResult)
    assert result.delivery_date == JAN2


def test_evaluate_day_24_hours_in_result():
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z"),
        perfect_actuals(),
        cutoff_utc=JAN2_CUTOFF,
    )
    assert len(result.hours) == 24


def test_evaluate_day_hours_sorted_chronologically():
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z"),
        perfect_actuals(),
        cutoff_utc=JAN2_CUTOFF,
    )
    starts = [h.start_utc for h in result.hours]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# Vintage selection — anti-look-ahead-bias guarantees
# ---------------------------------------------------------------------------


def test_evaluate_day_selects_latest_vintage_before_cutoff():
    """Three vintages: 07:30, 09:30, 11:30 — the 09:30 vintage must be chosen."""
    forecasts = (
        perfect_forecast("2026-01-01T07:30:00Z", 11000.0)
        + perfect_forecast("2026-01-01T09:30:00Z", 12000.0)  # latest ≤ cutoff
        + perfect_forecast("2026-01-01T11:30:00Z", 13000.0)  # after cutoff
    )
    result = evaluate_day(JAN2, forecasts, perfect_actuals(12000.0), cutoff_utc=JAN2_CUTOFF)
    assert result.selected_vintage_utc == datetime(2026, 1, 1, 9, 30, tzinfo=UTC)


def test_selected_vintage_never_after_cutoff():
    """Core anti-look-ahead guarantee: selected publishTime must be ≤ cutoff."""
    forecasts = (
        perfect_forecast("2026-01-01T09:30:00Z", 15000.0)  # eligible
        + perfect_forecast("2026-01-01T11:30:00Z", 14000.0)  # after cutoff — must be excluded
    )
    result = evaluate_day(JAN2, forecasts, perfect_actuals(14000.0), cutoff_utc=JAN2_CUTOFF)
    assert result.selected_vintage_utc <= result.decision_cutoff_utc
    assert result.selected_vintage_utc == datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    # Confirm the post-cutoff vintage's data never reaches the matched hours
    assert all(h.selected_vintage_time == datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
               for h in result.hours)


def test_cutoff_at_exact_publish_time_includes_that_vintage():
    """A publishTime exactly equal to the cutoff must be selected (boundary inclusive)."""
    exact_cutoff = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    forecasts = perfect_forecast("2026-01-01T09:30:00Z")
    result = evaluate_day(JAN2, forecasts, [], cutoff_utc=exact_cutoff)
    assert result.selected_vintage_utc == exact_cutoff
    assert result.selected_vintage_utc <= result.decision_cutoff_utc


def test_evaluate_day_look_ahead_bias_prevention():
    """Post-cutoff vintage must not be selected even when it would yield better accuracy."""
    # If the 11:30 vintage (perfect) were selected instead of 09:30 (off by 1000 MW),
    # all forecast_mw values would equal actual_mw.  Verify the 09:30 vintage's data
    # (off by 1000 MW) is what appears in the matched hours.
    forecasts = (
        perfect_forecast("2026-01-01T09:30:00Z", 15000.0)    # eligible, off by 1000 MW
        + perfect_forecast("2026-01-01T11:30:00Z", 14000.0)  # after cutoff — must not be used
    )
    result = evaluate_day(JAN2, forecasts, perfect_actuals(14000.0), cutoff_utc=JAN2_CUTOFF)
    assert result.selected_vintage_utc == datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    matched = [h for h in result.hours if h.forecast_mw is not None and h.actual_mw is not None]
    assert all(h.forecast_mw == pytest.approx(15000.0) for h in matched)
    assert all(h.actual_mw == pytest.approx(14000.0) for h in matched)


def test_evaluate_day_selected_vintage_stored_on_each_hour():
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z"),
        perfect_actuals(),
        cutoff_utc=JAN2_CUTOFF,
    )
    expected_pt = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    assert all(h.selected_vintage_time == expected_pt for h in result.hours)


# ---------------------------------------------------------------------------
# Multi-date forecast input — delivery window isolation
# ---------------------------------------------------------------------------


def test_evaluate_day_multi_date_forecast_only_delivery_date_matched():
    """Forecast records for other delivery dates must not appear in result hours.

    In production, a WINDFOR query for a date range returns forecasts covering
    many future delivery hours.  evaluate_day must return only the 24 hours
    for the requested delivery_date.
    """
    # Build a vintage with records for Jan 1 and Jan 2 (two days in one vintage)
    jan1_hours = [
        make_wf(
            "2026-01-01T09:30:00Z",
            datetime(2026, 1, 1, h, 0, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            13000.0,
        )
        for h in range(24)
    ]
    jan2_hours = [
        make_wf(
            "2026-01-01T09:30:00Z",
            datetime(2026, 1, 2, h, 0, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            14000.0,
        )
        for h in range(24)
    ]
    result = evaluate_day(JAN2, jan1_hours + jan2_hours, perfect_actuals(), cutoff_utc=JAN2_CUTOFF)
    assert len(result.hours) == 24
    assert all(h.start_utc.date() == date(2026, 1, 2) for h in result.hours)
    # Jan 2 forecast value is 14000; Jan 1 records must not contaminate
    assert all(
        h.forecast_mw == pytest.approx(14000.0)
        for h in result.hours
        if h.forecast_mw is not None
    )


# ---------------------------------------------------------------------------
# Missing data — verified via result.hours directly
# ---------------------------------------------------------------------------


def test_evaluate_day_missing_actuals_counted():
    """Remove SP1 and SP2 → hour 00:00 on Jan 2 has no actual."""
    actuals = [make_fhh(sp, 14000.0) for sp in range(3, 49)]
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z", 14000.0),
        actuals,
        cutoff_utc=JAN2_CUTOFF,
    )
    hour_00 = result.hours[0]
    assert hour_00.start_utc == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    assert hour_00.actual_mw is None
    assert sum(1 for h in result.hours if h.actual_mw is None) == 1
    matched = sum(1 for h in result.hours if h.forecast_mw is not None and h.actual_mw is not None)
    assert matched == 23


def test_evaluate_day_missing_forecast_hour():
    """Forecast covers only hours 1–23; hour 0 must have forecast_mw=None."""
    forecasts = [make_wf_hour("2026-01-01T09:30:00Z", h, 14000.0) for h in range(1, 24)]
    result = evaluate_day(JAN2, forecasts, perfect_actuals(14000.0), cutoff_utc=JAN2_CUTOFF)
    hour_00 = result.hours[0]
    assert hour_00.start_utc == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    assert hour_00.forecast_mw is None
    assert sum(1 for h in result.hours if h.forecast_mw is None) == 1


def test_evaluate_day_no_actuals_all_actual_mw_none():
    """Empty actual_records → every hour has actual_mw=None."""
    result = evaluate_day(
        JAN2,
        perfect_forecast("2026-01-01T09:30:00Z"),
        [],
        cutoff_utc=JAN2_CUTOFF,
    )
    assert len(result.hours) == 24
    assert all(h.actual_mw is None for h in result.hours)


# ---------------------------------------------------------------------------
# No eligible vintage
# ---------------------------------------------------------------------------


def test_evaluate_day_no_vintage_before_cutoff_raises():
    forecasts = perfect_forecast("2026-01-01T11:30:00Z")
    with pytest.raises(ValueError, match="No WINDFOR forecast vintage"):
        evaluate_day(JAN2, forecasts, perfect_actuals(), cutoff_utc=JAN2_CUTOFF)


# ---------------------------------------------------------------------------
# Default cutoff (computed from delivery date)
# ---------------------------------------------------------------------------


def test_evaluate_day_default_cutoff_is_11_utc_jan():
    """When no cutoff_utc supplied, default is 11:00 UTC on the preceding day (January)."""
    forecasts = perfect_forecast("2026-01-01T09:30:00Z")  # before 11:00
    result = evaluate_day(JAN2, forecasts, perfect_actuals())
    assert result.decision_cutoff_utc == datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# DST — delivery date on fall-back day (25 hours)
# ---------------------------------------------------------------------------


def test_evaluate_day_fall_back_25_hours():
    # 2026-10-25: window starts 2026-10-24T23:00Z, ends 2026-10-26T00:00Z (25h)
    # Cutoff: 11:00 BST on 2026-10-24 = 10:00 UTC
    delivery = date(2026, 10, 25)
    cutoff = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)

    window_start = datetime(2026, 10, 24, 23, 0, tzinfo=UTC)
    forecasts = []
    for h in range(25):
        st = window_start + timedelta(hours=h)
        forecasts.append(
            WindForRecord.model_validate(
                {
                    "dataset": "WINDFOR",
                    "publishTime": "2026-10-24T09:30:00Z",
                    "startTime": st.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "generation": 14000.0,
                }
            )
        )

    result = evaluate_day(delivery, forecasts, [], cutoff_utc=cutoff)
    assert len(result.hours) == 25
    assert all(h.actual_mw is None for h in result.hours)
