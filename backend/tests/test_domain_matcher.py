"""Tests for FUELHH deduplication, hourly aggregation, and record matching."""

from datetime import date, datetime, timedelta

import pytest

from app.domain.matcher import deduplicate_fuelhh, fuelhh_to_hourly, match_records
from app.domain.timestamps import UTC
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

JAN2 = date(2026, 1, 2)


def make_fhh(
    settlement_date: str,
    period: int,
    start_time: str,
    publish_time: str | None = None,
    generation: float = 15000.0,
) -> FuelHHRecord:
    if publish_time is None:
        # publishTime = startTime + 30min
        st = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        publish_time = (st + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return FuelHHRecord.model_validate(
        {
            "dataset": "FUELHH",
            "publishTime": publish_time,
            "startTime": start_time,
            "settlementDate": settlement_date,
            "settlementPeriod": period,
            "fuelType": "WIND",
            "generation": generation,
        }
    )


def make_wf(publish_time: str, start_time: str, gen: float = 14000.0) -> WindForRecord:
    return WindForRecord.model_validate(
        {
            "dataset": "WINDFOR",
            "publishTime": publish_time,
            "startTime": start_time,
            "generation": gen,
        }
    )


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# deduplicate_fuelhh
# ---------------------------------------------------------------------------


def test_dedup_fuelhh_no_duplicates():
    records = [
        make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z"),
        make_fhh("2026-01-02", 2, "2026-01-02T00:30:00Z"),
    ]
    result = deduplicate_fuelhh(records)
    assert len(result) == 2


def test_dedup_fuelhh_keeps_latest_publish_time():
    old = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z",
                   publish_time="2026-01-02T00:30:00Z", generation=15000)
    new = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z",
                   publish_time="2026-01-02T01:00:00Z", generation=15500)
    result = deduplicate_fuelhh([old, new])
    assert len(result) == 1
    assert result[0].generation == 15500


def test_dedup_fuelhh_keeps_latest_publish_time_reverse_order():
    old = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z",
                   publish_time="2026-01-02T00:30:00Z", generation=15000)
    new = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z",
                   publish_time="2026-01-02T01:00:00Z", generation=15500)
    # Even if old arrives after new in list, publishTime governs
    result = deduplicate_fuelhh([new, old])
    assert result[0].generation == 15500


def test_dedup_fuelhh_different_dates_not_merged():
    r1 = make_fhh("2026-01-01", 48, "2026-01-01T23:30:00Z")
    r2 = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z")
    result = deduplicate_fuelhh([r1, r2])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# fuelhh_to_hourly — January (24-hour day, GMT)
# ---------------------------------------------------------------------------


def _jan2_full_day() -> list[FuelHHRecord]:
    """48 half-hourly records covering the full Jan 2 settlement day."""
    records = []
    for sp in range(1, 49):
        offset_mins = (sp - 1) * 30
        start = datetime(2026, 1, 2, 0, 0, tzinfo=UTC) + timedelta(minutes=offset_mins)
        records.append(
            make_fhh(
                "2026-01-02",
                sp,
                start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                generation=15000.0 + sp,
            )
        )
    return records


def test_fuelhh_to_hourly_full_day_produces_24_hours():
    result = fuelhh_to_hourly(_jan2_full_day(), JAN2)
    assert len(result) == 24


def test_fuelhh_to_hourly_correct_average():
    # SP1=15001 (00:00), SP2=15002 (00:30) → hour 00:00 average = 15001.5
    result = fuelhh_to_hourly(_jan2_full_day(), JAN2)
    start_utc = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    assert result[start_utc] == pytest.approx(15001.5)


def test_fuelhh_to_hourly_all_non_none():
    result = fuelhh_to_hourly(_jan2_full_day(), JAN2)
    assert all(v is not None for v in result.values())


def test_fuelhh_to_hourly_missing_first_half():
    """Remove SP1 (00:00 half-hour); hour 00:00 actual should be None."""
    records = [r for r in _jan2_full_day() if r.settlement_period != 1]
    result = fuelhh_to_hourly(records, JAN2)
    assert result[datetime(2026, 1, 2, 0, 0, tzinfo=UTC)] is None


def test_fuelhh_to_hourly_missing_second_half():
    """Remove SP2 (00:30 half-hour); hour 00:00 actual should be None."""
    records = [r for r in _jan2_full_day() if r.settlement_period != 2]
    result = fuelhh_to_hourly(records, JAN2)
    assert result[datetime(2026, 1, 2, 0, 0, tzinfo=UTC)] is None


def test_fuelhh_to_hourly_records_from_other_days_excluded():
    jan1_record = make_fhh("2026-01-01", 48, "2026-01-01T23:30:00Z")
    result = fuelhh_to_hourly([jan1_record] + _jan2_full_day(), JAN2)
    # Jan 1 T23:30 is outside the Jan 2 window; still 24 hours
    assert len(result) == 24


def test_fuelhh_to_hourly_empty_input_all_none():
    result = fuelhh_to_hourly([], JAN2)
    assert len(result) == 24
    assert all(v is None for v in result.values())


def test_fuelhh_to_hourly_handles_duplicate_periods():
    """Duplicate settlement period — latest publishTime governs."""
    records = _jan2_full_day()
    # Add a corrected SP1 with later publishTime and different generation
    records.append(
        make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z",
                 publish_time="2026-01-02T02:00:00Z", generation=99999.0)
    )
    result = fuelhh_to_hourly(records, JAN2)
    # SP1 corrected to 99999, SP2=15002 → avg = (99999+15002)/2
    expected = (99999.0 + 15002.0) / 2.0
    assert result[datetime(2026, 1, 2, 0, 0, tzinfo=UTC)] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# fuelhh_to_hourly — DST transition days
# ---------------------------------------------------------------------------


def test_fuelhh_to_hourly_spring_forward_23h():
    # 2026-03-29: clocks spring forward; delivery window = 23 hours
    result = fuelhh_to_hourly([], date(2026, 3, 29))
    assert len(result) == 23


def test_fuelhh_to_hourly_fall_back_25h():
    # 2026-10-25: clocks fall back; delivery window = 25 hours
    result = fuelhh_to_hourly([], date(2026, 10, 25))
    assert len(result) == 25


# ---------------------------------------------------------------------------
# match_records
# ---------------------------------------------------------------------------


def test_match_records_all_matched():
    vintage_pt = dt("2026-01-01T09:30:00Z")
    vintage = [make_wf("2026-01-01T09:30:00Z", f"2026-01-02T{h:02d}:00:00Z", 14000 + h * 100)
               for h in range(24)]
    actual_hourly = {
        datetime(2026, 1, 2, h, 0, tzinfo=UTC): 14050.0 + h * 100
        for h in range(24)
    }
    hours = match_records(vintage, actual_hourly, vintage_pt)
    assert len(hours) == 24
    assert all(h.forecast_mw is not None for h in hours)
    assert all(h.actual_mw is not None for h in hours)
    assert all(h.selected_vintage_time == vintage_pt for h in hours)


def test_match_records_sorted_chronologically():
    vintage_pt = dt("2026-01-01T09:30:00Z")
    vintage = [make_wf("2026-01-01T09:30:00Z", f"2026-01-02T{h:02d}:00:00Z")
               for h in range(5)]
    actual_hourly = {datetime(2026, 1, 2, h, 0, tzinfo=UTC): 15000.0 for h in range(5)}
    hours = match_records(vintage, actual_hourly, vintage_pt)
    starts = [h.start_utc for h in hours]
    assert starts == sorted(starts)


def test_match_records_forecast_none_for_uncovered_hour():
    """Hour in delivery window but not covered by selected vintage → forecast None."""
    vintage_pt = dt("2026-01-01T09:30:00Z")
    # Vintage covers only hour 0 and 1; hour 2 has actual but no forecast
    vintage = [make_wf("2026-01-01T09:30:00Z", f"2026-01-02T0{h}:00:00Z") for h in [0, 1]]
    actual_hourly = {datetime(2026, 1, 2, h, 0, tzinfo=UTC): 15000.0 for h in range(3)}
    hours = match_records(vintage, actual_hourly, vintage_pt)
    assert hours[2].forecast_mw is None
    assert hours[2].actual_mw == 15000.0


def test_match_records_actual_none_propagated():
    vintage_pt = dt("2026-01-01T09:30:00Z")
    vintage = [make_wf("2026-01-01T09:30:00Z", "2026-01-02T01:00:00Z")]
    actual_hourly = {datetime(2026, 1, 2, 1, 0, tzinfo=UTC): None}
    hours = match_records(vintage, actual_hourly, vintage_pt)
    assert hours[0].actual_mw is None
    assert hours[0].forecast_mw is not None


def test_match_records_start_uk_converted():
    """start_uk must reflect UK local time (GMT in January)."""
    vintage_pt = dt("2026-01-01T09:30:00Z")
    vintage = [make_wf("2026-01-01T09:30:00Z", "2026-01-02T11:00:00Z")]
    actual_hourly = {datetime(2026, 1, 2, 11, 0, tzinfo=UTC): 15000.0}
    hours = match_records(vintage, actual_hourly, vintage_pt)
    assert hours[0].start_uk.hour == 11  # GMT = UTC in January


def test_match_records_delivery_hours_are_source_of_truth():
    """Hours present only in the forecast (outside delivery window) are ignored."""
    vintage_pt = dt("2026-01-01T09:30:00Z")
    # Forecast covers Jan 1 and Jan 2; only Jan 2 is in actual_hourly
    vintage = [
        make_wf("2026-01-01T09:30:00Z", "2026-01-01T23:00:00Z"),  # not in window
        make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z"),  # in window
    ]
    actual_hourly = {datetime(2026, 1, 2, 0, 0, tzinfo=UTC): 15000.0}
    hours = match_records(vintage, actual_hourly, vintage_pt)
    assert len(hours) == 1
    assert hours[0].start_utc == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# fuelhh_to_hourly — fuel type guard
# ---------------------------------------------------------------------------


def _make_non_wind_fhh(fuel_type: str) -> FuelHHRecord:
    return FuelHHRecord.model_validate(
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-02T00:30:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "settlementDate": "2026-01-02",
            "settlementPeriod": 1,
            "fuelType": fuel_type,
            "generation": 5000.0,
        }
    )


def test_fuelhh_to_hourly_rejects_non_wind_record():
    """A single non-WIND record in an otherwise empty list must raise ValueError."""
    with pytest.raises(ValueError, match="WIND"):
        fuelhh_to_hourly([_make_non_wind_fhh("CCGT")], JAN2)


def test_fuelhh_to_hourly_rejects_mixed_fuel_types():
    """WIND records mixed with non-WIND records must raise ValueError."""
    wind = make_fhh("2026-01-02", 1, "2026-01-02T00:00:00Z")
    ccgt = _make_non_wind_fhh("CCGT")
    with pytest.raises(ValueError, match="WIND"):
        fuelhh_to_hourly([wind, ccgt], JAN2)


def test_fuelhh_to_hourly_rejects_multiple_non_wind_types():
    """Error message must name all unexpected fuel types."""
    with pytest.raises(ValueError, match="WIND"):
        fuelhh_to_hourly(
            [_make_non_wind_fhh("CCGT"), _make_non_wind_fhh("NUCLEAR")], JAN2
        )


def test_fuelhh_to_hourly_accepts_wind_only():
    """Pure WIND input must not raise."""
    records = _jan2_full_day()
    result = fuelhh_to_hourly(records, JAN2)
    assert len(result) == 24


def test_fuelhh_to_hourly_accepts_empty_list():
    """Empty input is valid (no fuel type to check); all hours are None."""
    result = fuelhh_to_hourly([], JAN2)
    assert all(v is None for v in result.values())
