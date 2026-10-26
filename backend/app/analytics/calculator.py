"""Forecast accuracy analytics calculator.

Entry point: calculate_analytics(hours) → ForecastAnalytics

COMMON EVALUATION SAMPLE (CES)
-------------------------------
A delivery hour enters the CES if and only if:
    1. forecast_mw is not None
    2. actual_mw is not None
    3. math.isfinite(forecast_mw) is True
    4. math.isfinite(actual_mw)   is True

Condition 3 & 4 guard against programming errors (e.g. a division producing
inf) and any unexpected non-finite values from upstream parsing.

Zero actual_mw is a valid observation (wind generation can be zero during
calm periods or curtailment) and is never excluded or treated as missing.

All metrics — MAE, RMSE, bias, percentiles, extremes — are computed over
exactly this CES so they share a common denominator and are comparable.

SIGN CONVENTION
---------------
    signed_error = forecast_mw − actual_mw

    Positive → over-forecast (predicted more generation than occurred)
    Negative → under-forecast (predicted less generation than occurred)

METRIC FORMULAS  (n = |CES|)
----------------------------
    MAE   = (1/n) × Σ |signed_error_i|
    RMSE  = sqrt( (1/n) × Σ signed_error_i² )
    Bias  = (1/n) × Σ signed_error_i

PERCENTILE METHOD
-----------------
Linear interpolation between adjacent order statistics.
For a sorted list v of length n, the p-quantile (0 ≤ p ≤ 1) is:
    idx  = p × (n − 1)
    lo   = floor(idx)
    hi   = min(lo + 1, n − 1)
    result = v[lo] + (idx − lo) × (v[hi] − v[lo])

This matches numpy.percentile / np.quantile with interpolation='linear'.
"""

import logging
import math

from app.analytics.models import ForecastAnalytics, IntervalError
from app.domain.models import DeliveryHour

logger = logging.getLogger(__name__)


def calculate_analytics(hours: list[DeliveryHour]) -> ForecastAnalytics:
    """Compute forecast accuracy analytics over *hours*.

    Args:
        hours: Delivery hours produced by match_records().  May be empty.
                forecast_mw and actual_mw may individually be None.

    Returns:
        ForecastAnalytics.  All metrics are None when the CES is empty.

    Notes:
        - Missing observations are never imputed as zero.
        - Non-finite values (nan, ±inf) are excluded from the CES and counted
          as invalid_hours.
        - The function is pure and has no I/O side effects.
    """
    total = len(hours)
    missing_forecast = 0
    missing_actual = 0
    invalid = 0
    ces: list[tuple[DeliveryHour, float, float]] = []  # (hour, forecast, actual)

    for h in hours:
        f = h.forecast_mw
        a = h.actual_mw

        if f is None:
            missing_forecast += 1
            continue
        if a is None:
            missing_actual += 1
            continue
        if not math.isfinite(f) or not math.isfinite(a):
            invalid += 1
            logger.warning(
                "Non-finite value excluded from CES: start_utc=%s forecast=%s actual=%s",
                h.start_utc.isoformat(),
                f,
                a,
            )
            continue
        ces.append((h, f, a))

    n = len(ces)

    if n == 0:
        return ForecastAnalytics(
            total_hours=total,
            evaluation_hours=0,
            missing_forecast_hours=missing_forecast,
            missing_actual_hours=missing_actual,
            invalid_hours=invalid,
            interval_errors=(),
            mae_mw=None,
            rmse_mw=None,
            bias_mw=None,
            max_abs_error_mw=None,
            min_abs_error_mw=None,
            p90_abs_error_mw=None,
            max_signed_error_mw=None,
            min_signed_error_mw=None,
        )

    # Build per-interval errors
    interval_errors: list[IntervalError] = []
    signed_errors: list[float] = []
    abs_errors: list[float] = []

    for h, f, a in ces:
        signed = f - a
        abse = abs(signed)
        signed_errors.append(signed)
        abs_errors.append(abse)
        interval_errors.append(
            IntervalError(
                start_utc=h.start_utc,
                start_uk=h.start_uk,
                forecast_mw=f,
                actual_mw=a,
                signed_error_mw=signed,
                abs_error_mw=abse,
            )
        )

    # Aggregated metrics
    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(e * e for e in signed_errors) / n)
    bias = sum(signed_errors) / n

    # Distribution of absolute errors
    sorted_abs = sorted(abs_errors)
    max_abs = sorted_abs[-1]
    min_abs = sorted_abs[0]
    p90_abs = _percentile(sorted_abs, 0.90)

    # Signed extremes
    max_signed = max(signed_errors)
    min_signed = min(signed_errors)

    return ForecastAnalytics(
        total_hours=total,
        evaluation_hours=n,
        missing_forecast_hours=missing_forecast,
        missing_actual_hours=missing_actual,
        invalid_hours=invalid,
        interval_errors=tuple(interval_errors),
        mae_mw=mae,
        rmse_mw=rmse,
        bias_mw=bias,
        max_abs_error_mw=max_abs,
        min_abs_error_mw=min_abs,
        p90_abs_error_mw=p90_abs,
        max_signed_error_mw=max_signed,
        min_signed_error_mw=min_signed,
    )


def _percentile(sorted_values: list[float], p: float) -> float:
    """p-quantile via linear interpolation between adjacent order statistics.

    Args:
        sorted_values: Non-empty list, already sorted ascending.
        p:             Probability in [0, 1].
    """
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_values[lo] + (idx - lo) * (sorted_values[hi] - sorted_values[lo])
