"""Comprehensive tests for the analytics calculator.

All expected values are hand-calculated and annotated inline so that any
regression is immediately traceable to a formula change.

Sign convention throughout:
    signed_error = forecast − actual
    positive → over-forecast, negative → under-forecast

Common Evaluation Sample (CES) rule:
    An hour enters the CES iff forecast_mw is not None,
    actual_mw is not None, and both values are finite.
"""

import math
from datetime import UTC, datetime

import pytest

from app.analytics.calculator import _percentile, calculate_analytics
from app.domain.models import DeliveryHour

UTC = UTC
_VINTAGE = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hour(h: int, forecast: float | None, actual: float | None) -> DeliveryHour:
    start = datetime(2026, 1, 2, h, 0, tzinfo=UTC)
    return DeliveryHour(
        start_utc=start,
        start_uk=start,
        forecast_mw=forecast,
        actual_mw=actual,
        selected_vintage_time=_VINTAGE,
    )


# ---------------------------------------------------------------------------
# _percentile — linear interpolation
# ---------------------------------------------------------------------------


class TestPercentile:
    def test_single_element(self):
        assert _percentile([5.0], 0.9) == 5.0

    def test_p0_is_min(self):
        assert _percentile([1.0, 2.0, 3.0], 0.0) == pytest.approx(1.0)

    def test_p100_is_max(self):
        assert _percentile([1.0, 2.0, 3.0], 1.0) == pytest.approx(3.0)

    def test_p50_median_even(self):
        # [10, 20, 30, 40]: idx=1.5, lo=1 (20), hi=2 (30) → 20 + 0.5×10 = 25
        assert _percentile([10.0, 20.0, 30.0, 40.0], 0.5) == pytest.approx(25.0)

    def test_p90_two_elements(self):
        # [0, 100]: idx=0.9×1=0.9, lo=0 (0), hi=1 (100) → 0 + 0.9×100 = 90
        assert _percentile([0.0, 100.0], 0.9) == pytest.approx(90.0)

    def test_p90_ten_elements(self):
        # [1..10]: idx=0.9×9=8.1, lo=8 (9), hi=9 (10) → 9 + 0.1×1 = 9.1
        values = [float(i) for i in range(1, 11)]
        assert _percentile(values, 0.9) == pytest.approx(9.1)


# ---------------------------------------------------------------------------
# Empty and all-missing inputs
# ---------------------------------------------------------------------------


class TestEmptyAndAllMissing:
    def test_empty_list(self):
        r = calculate_analytics([])
        assert r.evaluation_hours == 0
        assert r.total_hours == 0
        assert r.mae_mw is None
        assert r.rmse_mw is None
        assert r.bias_mw is None
        assert r.interval_errors == ()

    def test_all_forecast_missing(self):
        hours = [hour(h, None, 14000.0) for h in range(3)]
        r = calculate_analytics(hours)
        assert r.total_hours == 3
        assert r.evaluation_hours == 0
        assert r.missing_forecast_hours == 3
        assert r.missing_actual_hours == 0
        assert r.mae_mw is None

    def test_all_actual_missing(self):
        hours = [hour(h, 14000.0, None) for h in range(3)]
        r = calculate_analytics(hours)
        assert r.evaluation_hours == 0
        assert r.missing_actual_hours == 3
        assert r.missing_forecast_hours == 0

    def test_all_both_missing(self):
        hours = [hour(h, None, None) for h in range(5)]
        r = calculate_analytics(hours)
        assert r.total_hours == 5
        assert r.evaluation_hours == 0
        # Each hour is counted once in whichever missing bucket it hits first
        assert r.missing_forecast_hours == 5
        assert r.missing_actual_hours == 0  # reached via forecast check first


# ---------------------------------------------------------------------------
# Perfect forecast — all zeros
# ---------------------------------------------------------------------------


class TestPerfectForecast:
    """forecast == actual → all errors = 0"""

    def setup_method(self):
        self.hours = [hour(h, 14000.0, 14000.0) for h in range(24)]
        self.r = calculate_analytics(self.hours)

    def test_evaluation_hours(self):
        assert self.r.evaluation_hours == 24

    def test_mae_zero(self):
        # MAE = (1/24) × Σ|0| = 0
        assert self.r.mae_mw == pytest.approx(0.0)

    def test_rmse_zero(self):
        assert self.r.rmse_mw == pytest.approx(0.0)

    def test_bias_zero(self):
        assert self.r.bias_mw == pytest.approx(0.0)

    def test_all_abs_errors_zero(self):
        assert self.r.max_abs_error_mw == pytest.approx(0.0)
        assert self.r.min_abs_error_mw == pytest.approx(0.0)
        assert self.r.p90_abs_error_mw == pytest.approx(0.0)

    def test_interval_errors_all_zero(self):
        assert len(self.r.interval_errors) == 24
        assert all(ie.signed_error_mw == 0.0 for ie in self.r.interval_errors)
        assert all(ie.abs_error_mw == 0.0 for ie in self.r.interval_errors)


# ---------------------------------------------------------------------------
# Constant over-forecast
# ---------------------------------------------------------------------------


class TestConstantOverForecast:
    """forecast = actual + 1000  (always over by 1000 MW)

    Hand-calculated:
        n = 4
        errors = [1000, 1000, 1000, 1000]
        MAE  = 4000/4 = 1000
        RMSE = sqrt(4000000/4) = sqrt(1000000) = 1000
        Bias = 4000/4 = 1000
    """

    def setup_method(self):
        self.r = calculate_analytics([hour(h, 15000.0, 14000.0) for h in range(4)])

    def test_mae(self):
        assert self.r.mae_mw == pytest.approx(1000.0)

    def test_rmse(self):
        assert self.r.rmse_mw == pytest.approx(1000.0)

    def test_bias_positive(self):
        assert self.r.bias_mw == pytest.approx(1000.0)

    def test_all_signed_errors_positive(self):
        assert all(ie.signed_error_mw == pytest.approx(1000.0) for ie in self.r.interval_errors)

    def test_max_signed_equals_min_signed(self):
        assert self.r.max_signed_error_mw == pytest.approx(1000.0)
        assert self.r.min_signed_error_mw == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Constant under-forecast
# ---------------------------------------------------------------------------


class TestConstantUnderForecast:
    """forecast = actual − 500  (always under by 500 MW)

    MAE = RMSE = 500, Bias = −500
    """

    def setup_method(self):
        self.r = calculate_analytics([hour(h, 13500.0, 14000.0) for h in range(4)])

    def test_mae(self):
        assert self.r.mae_mw == pytest.approx(500.0)

    def test_rmse(self):
        assert self.r.rmse_mw == pytest.approx(500.0)

    def test_bias_negative(self):
        assert self.r.bias_mw == pytest.approx(-500.0)

    def test_min_signed_is_negative(self):
        assert self.r.min_signed_error_mw == pytest.approx(-500.0)


# ---------------------------------------------------------------------------
# Mixed positive and negative errors
# ---------------------------------------------------------------------------


class TestMixedErrors:
    """Errors: +1000, −1000, +2000, −2000

    Hand-calculated:
        n = 4
        signed = [1000, -1000, 2000, -2000]
        abs    = [1000,  1000, 2000,  2000]

        MAE  = (1000+1000+2000+2000)/4 = 6000/4 = 1500
        RMSE = sqrt((1e6+1e6+4e6+4e6)/4) = sqrt(10e6/4) = sqrt(2500000) ≈ 1581.14
        Bias = (1000-1000+2000-2000)/4 = 0
    """

    def setup_method(self):
        self.r = calculate_analytics(
            [
                hour(0, 15000.0, 14000.0),  # +1000
                hour(1, 13000.0, 14000.0),  # -1000
                hour(2, 16000.0, 14000.0),  # +2000
                hour(3, 12000.0, 14000.0),  # -2000
            ]
        )

    def test_mae(self):
        assert self.r.mae_mw == pytest.approx(1500.0)

    def test_rmse(self):
        expected = math.sqrt(2_500_000.0)
        assert self.r.rmse_mw == pytest.approx(expected)

    def test_bias_near_zero(self):
        # Errors cancel exactly
        assert self.r.bias_mw == pytest.approx(0.0, abs=1e-9)

    def test_rmse_greater_than_mae(self):
        assert self.r.rmse_mw > self.r.mae_mw

    def test_max_abs_error(self):
        assert self.r.max_abs_error_mw == pytest.approx(2000.0)

    def test_min_abs_error(self):
        assert self.r.min_abs_error_mw == pytest.approx(1000.0)

    def test_max_signed(self):
        assert self.r.max_signed_error_mw == pytest.approx(2000.0)

    def test_min_signed(self):
        assert self.r.min_signed_error_mw == pytest.approx(-2000.0)


# ---------------------------------------------------------------------------
# Zero actual generation (valid observation)
# ---------------------------------------------------------------------------


class TestZeroActual:
    """actual = 0 MW (calm/curtailed period) — must NOT be excluded.

    error = 14000 − 0 = +14000 MW
    """

    def test_zero_actual_is_included_in_ces(self):
        r = calculate_analytics([hour(0, 14000.0, 0.0)])
        assert r.evaluation_hours == 1

    def test_zero_actual_error_is_correct(self):
        r = calculate_analytics([hour(0, 14000.0, 0.0)])
        assert r.interval_errors[0].signed_error_mw == pytest.approx(14000.0)
        assert r.interval_errors[0].abs_error_mw == pytest.approx(14000.0)

    def test_zero_forecast_and_zero_actual_zero_error(self):
        r = calculate_analytics([hour(0, 0.0, 0.0)])
        assert r.evaluation_hours == 1
        assert r.mae_mw == pytest.approx(0.0)

    def test_zero_forecast_nonzero_actual(self):
        # error = 0 − 14000 = −14000
        r = calculate_analytics([hour(0, 0.0, 14000.0)])
        assert r.interval_errors[0].signed_error_mw == pytest.approx(-14000.0)
        assert r.bias_mw == pytest.approx(-14000.0)


# ---------------------------------------------------------------------------
# Non-finite value handling
# ---------------------------------------------------------------------------


class TestNonFiniteValues:
    def test_inf_forecast_excluded(self):
        r = calculate_analytics([hour(0, float("inf"), 14000.0)])
        assert r.evaluation_hours == 0
        assert r.invalid_hours == 1
        assert r.mae_mw is None

    def test_negative_inf_actual_excluded(self):
        r = calculate_analytics([hour(0, 14000.0, float("-inf"))])
        assert r.evaluation_hours == 0
        assert r.invalid_hours == 1

    def test_nan_forecast_excluded(self):
        r = calculate_analytics([hour(0, float("nan"), 14000.0)])
        assert r.evaluation_hours == 0
        assert r.invalid_hours == 1

    def test_nan_actual_excluded(self):
        r = calculate_analytics([hour(0, 14000.0, float("nan"))])
        assert r.invalid_hours == 1

    def test_invalid_hour_not_counted_as_missing(self):
        """A non-finite hour must be counted as invalid, not missing."""
        hours = [
            hour(0, float("inf"), 14000.0),  # invalid
            hour(1, None, 14000.0),          # missing forecast
        ]
        r = calculate_analytics(hours)
        assert r.invalid_hours == 1
        assert r.missing_forecast_hours == 1
        assert r.evaluation_hours == 0

    def test_mix_of_invalid_and_valid(self):
        """Valid hours must still be evaluated even when some are invalid."""
        hours = [
            hour(0, float("nan"), 14000.0),  # invalid
            hour(1, 15000.0, 14000.0),       # CES: error = +1000
        ]
        r = calculate_analytics(hours)
        assert r.evaluation_hours == 1
        assert r.invalid_hours == 1
        assert r.mae_mw == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Partial missing — common evaluation sample
# ---------------------------------------------------------------------------


class TestPartialMissing:
    """
    6 hours:
        h0: forecast=15000, actual=14000  → CES, error=+1000
        h1: forecast=None,  actual=14000  → missing_forecast
        h2: forecast=15000, actual=None   → missing_actual
        h3: forecast=13000, actual=14000  → CES, error=−1000
        h4: forecast=inf,   actual=14000  → invalid
        h5: forecast=14000, actual=14000  → CES, error=0

    CES: [h0, h3, h5], n=3
    MAE  = (1000 + 1000 + 0) / 3 = 2000/3 ≈ 666.67
    RMSE = sqrt((1e6 + 1e6 + 0) / 3) = sqrt(2e6/3) ≈ 816.50
    Bias = (1000 − 1000 + 0) / 3 = 0
    """

    def setup_method(self):
        self.hours = [
            hour(0, 15000.0, 14000.0),
            hour(1, None, 14000.0),
            hour(2, 15000.0, None),
            hour(3, 13000.0, 14000.0),
            hour(4, float("inf"), 14000.0),
            hour(5, 14000.0, 14000.0),
        ]
        self.r = calculate_analytics(self.hours)

    def test_total_hours(self):
        assert self.r.total_hours == 6

    def test_evaluation_hours(self):
        assert self.r.evaluation_hours == 3

    def test_missing_counts(self):
        assert self.r.missing_forecast_hours == 1
        assert self.r.missing_actual_hours == 1
        assert self.r.invalid_hours == 1

    def test_mae(self):
        # (1000 + 1000 + 0) / 3
        assert self.r.mae_mw == pytest.approx(2000.0 / 3.0)

    def test_rmse(self):
        # sqrt((1e6 + 1e6 + 0) / 3)
        assert self.r.rmse_mw == pytest.approx(math.sqrt(2_000_000.0 / 3.0))

    def test_bias_zero(self):
        assert self.r.bias_mw == pytest.approx(0.0, abs=1e-9)

    def test_interval_errors_length(self):
        assert len(self.r.interval_errors) == 3


# ---------------------------------------------------------------------------
# Large outlier — RMSE affected more than MAE
# ---------------------------------------------------------------------------


class TestLargeOutlier:
    """
    Errors: 100, 100, 100, 100, 10000  (n=5, one large outlier)

    Hand-calculated:
        sum_abs = 100*4 + 10000 = 10400
        MAE  = 10400/5 = 2080
        RMSE = sqrt((100²*4 + 10000²)/5)
             = sqrt((40000 + 100000000)/5)
             = sqrt(100040000/5)
             = sqrt(20008000)
             ≈ 4473.0
        Bias = 10400/5 = 2080  (all positive)
    """

    def setup_method(self):
        self.r = calculate_analytics(
            [
                hour(0, 14100.0, 14000.0),
                hour(1, 14100.0, 14000.0),
                hour(2, 14100.0, 14000.0),
                hour(3, 14100.0, 14000.0),
                hour(4, 24000.0, 14000.0),  # outlier: +10000
            ]
        )

    def test_mae(self):
        assert self.r.mae_mw == pytest.approx(2080.0)

    def test_rmse_greater_than_mae(self):
        assert self.r.rmse_mw > self.r.mae_mw

    def test_rmse(self):
        expected = math.sqrt(20_008_000.0)
        assert self.r.rmse_mw == pytest.approx(expected, rel=1e-9)

    def test_max_abs_error_is_outlier(self):
        assert self.r.max_abs_error_mw == pytest.approx(10000.0)

    def test_min_abs_error(self):
        assert self.r.min_abs_error_mw == pytest.approx(100.0)

    def test_p90_abs_error(self):
        # sorted abs_errors = [100, 100, 100, 100, 10000]
        # idx = 0.9 × 4 = 3.6, lo=3 (100), hi=4 (10000)
        # result = 100 + 0.6 × (10000 − 100) = 100 + 0.6 × 9900 = 100 + 5940 = 6040
        assert self.r.p90_abs_error_mw == pytest.approx(6040.0)


# ---------------------------------------------------------------------------
# Interval-level error properties
# ---------------------------------------------------------------------------


class TestIntervalErrorProperties:
    def test_interval_errors_are_chronological(self):
        hours = [hour(h, 14000.0 + h * 100, 14000.0) for h in range(5)]
        r = calculate_analytics(hours)
        starts = [ie.start_utc for ie in r.interval_errors]
        assert starts == sorted(starts)

    def test_interval_error_fields_match_hours(self):
        h = hour(3, 15000.0, 14000.0)
        r = calculate_analytics([h])
        ie = r.interval_errors[0]
        assert ie.forecast_mw == pytest.approx(15000.0)
        assert ie.actual_mw == pytest.approx(14000.0)
        assert ie.signed_error_mw == pytest.approx(1000.0)
        assert ie.abs_error_mw == pytest.approx(1000.0)
        assert ie.start_utc == h.start_utc

    def test_abs_error_is_always_nonnegative(self):
        hours = [
            hour(0, 12000.0, 14000.0),   # negative signed
            hour(1, 16000.0, 14000.0),   # positive signed
        ]
        r = calculate_analytics(hours)
        assert all(ie.abs_error_mw >= 0.0 for ie in r.interval_errors)

    def test_signed_error_sign_convention(self):
        """forecast > actual → positive signed error (over-forecast)."""
        r_over = calculate_analytics([hour(0, 15000.0, 14000.0)])
        r_under = calculate_analytics([hour(0, 13000.0, 14000.0)])
        assert r_over.interval_errors[0].signed_error_mw > 0
        assert r_under.interval_errors[0].signed_error_mw < 0


# ---------------------------------------------------------------------------
# Single-hour edge cases
# ---------------------------------------------------------------------------


class TestSingleHour:
    def test_single_hour_p90_equals_the_one_value(self):
        r = calculate_analytics([hour(0, 15500.0, 14000.0)])
        # With n=1, percentile returns the single value
        assert r.p90_abs_error_mw == pytest.approx(1500.0)

    def test_single_hour_mae_rmse_bias_all_equal(self):
        r = calculate_analytics([hour(0, 15000.0, 14000.0)])
        assert r.mae_mw == pytest.approx(r.rmse_mw)
        assert r.mae_mw == pytest.approx(abs(r.bias_mw))

    def test_single_hour_max_equals_min_abs(self):
        r = calculate_analytics([hour(0, 15000.0, 14000.0)])
        assert r.max_abs_error_mw == r.min_abs_error_mw


# ---------------------------------------------------------------------------
# Sample counts consistency
# ---------------------------------------------------------------------------


class TestSampleCountConsistency:
    """total_hours must equal CES + missing_forecast + missing_actual + invalid."""

    def test_counts_sum_to_total(self):
        hours = [
            hour(0, 14000.0, 14000.0),        # CES
            hour(1, None, 14000.0),             # missing_forecast
            hour(2, 14000.0, None),             # missing_actual
            hour(3, float("nan"), 14000.0),     # invalid
            hour(4, 14000.0, 14000.0),          # CES
        ]
        r = calculate_analytics(hours)
        assert (
            r.evaluation_hours
            + r.missing_forecast_hours
            + r.missing_actual_hours
            + r.invalid_hours
            == r.total_hours
        )

    def test_result_is_frozen(self):
        r = calculate_analytics([hour(0, 14000.0, 14000.0)])
        with pytest.raises((AttributeError, TypeError)):
            r.mae_mw = 999.0  # type: ignore[misc]
