"""Analytics output models for forecast accuracy evaluation.

These are read-only dataclasses consumed by the API layer and tests.
They contain no business logic; all computation lives in calculator.py.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IntervalError:
    """Error for a single delivery hour in the common evaluation sample.

    Only hours that satisfy ALL of the following enter the sample:
        - forecast_mw is not None
        - actual_mw is not None
        - both values are finite (not nan, not ±inf)

    Sign convention — signed_error_mw = forecast_mw − actual_mw:
        Positive  → over-forecast  (we predicted more wind than was generated)
        Negative  → under-forecast (we predicted less wind than was generated)
        Zero      → perfect for this interval

    Zero actual_mw (genuine wind lull) is valid and not excluded.
    """

    start_utc: datetime
    start_uk: datetime
    forecast_mw: float      # guaranteed finite and non-None
    actual_mw: float        # guaranteed finite and non-None (may be 0.0)
    signed_error_mw: float  # forecast_mw − actual_mw
    abs_error_mw: float     # |signed_error_mw|


@dataclass(frozen=True)
class ForecastAnalytics:
    """Complete analytics output for a set of delivery hours.

    All aggregated metrics (mae_mw, rmse_mw, …) are computed over exactly
    the same set of hours — the *common evaluation sample* (CES) — so
    comparisons between metrics are always meaningful.

    ---
    METRIC FORMULAS  (n = evaluation_hours, errors = signed errors in CES)
    ---
    MAE   = (1/n) × Σ |forecast_i − actual_i|
    RMSE  = sqrt( (1/n) × Σ (forecast_i − actual_i)² )
    Bias  = (1/n) × Σ (forecast_i − actual_i)

    RMSE ≥ MAE always; they are equal when all errors have the same magnitude.
    RMSE penalises large individual errors more than MAE.
    Bias cancels when positive and negative errors are symmetric.

    Percentile uses linear interpolation between order statistics
    (equivalent to numpy's default 'linear' method).

    ---
    WHAT THESE METRICS DO NOT REPRESENT
    ---
    These are statistical accuracy metrics in MW.  They do not represent:
        - procurement cost
        - quantity of electricity to purchase
        - financial exposure or trading P&L
    """

    # --- Evaluation sample composition ---
    total_hours: int            # hours in the delivery window (matched + missing + invalid)
    evaluation_hours: int       # hours in the CES (both values finite and non-None)
    missing_forecast_hours: int # hours where forecast_mw is None
    missing_actual_hours: int   # hours where actual_mw is None
    invalid_hours: int          # hours excluded due to non-finite value(s)

    # --- Interval-level results (CES only, chronological) ---
    interval_errors: tuple[IntervalError, ...]

    # --- Aggregated metrics (None when evaluation_hours == 0) ---
    mae_mw: float | None        # Mean Absolute Error (MW) — always ≥ 0
    rmse_mw: float | None       # Root Mean Square Error (MW) — always ≥ 0
    bias_mw: float | None       # Mean signed error (MW); +ve = over-forecast

    # --- Absolute-error distribution (None when evaluation_hours == 0) ---
    max_abs_error_mw: float | None  # largest single-hour absolute error
    min_abs_error_mw: float | None  # smallest single-hour absolute error
    p90_abs_error_mw: float | None  # 90th-percentile absolute error

    # --- Signed-error extremes (None when evaluation_hours == 0) ---
    max_signed_error_mw: float | None  # most positive (worst over-forecast hour)
    min_signed_error_mw: float | None  # most negative (worst under-forecast hour)
