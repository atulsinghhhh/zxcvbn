"""Tests for timestamp normalization and decision-cutoff calculation."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.timestamps import (
    UTC,
    decision_cutoff_utc,
    delivery_window_utc,
    ensure_utc,
    to_uk,
    uk_midnight_utc,
)

# ---------------------------------------------------------------------------
# ensure_utc
# ---------------------------------------------------------------------------


def test_ensure_utc_rejects_naive():
    with pytest.raises(ValueError, match="Naive datetime"):
        ensure_utc(datetime(2026, 1, 2, 11, 0, 0))


def test_ensure_utc_passthrough_utc():
    dt = datetime(2026, 1, 2, 11, 0, tzinfo=UTC)
    assert ensure_utc(dt) == dt


def test_ensure_utc_converts_bst_to_utc():
    bst = ZoneInfo("Europe/London")
    dt_bst = datetime(2026, 7, 2, 12, 0, tzinfo=bst)
    result = ensure_utc(dt_bst)
    assert result == datetime(2026, 7, 2, 11, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# to_uk
# ---------------------------------------------------------------------------


def test_to_uk_winter_no_offset():
    dt_utc = datetime(2026, 1, 2, 11, 0, tzinfo=UTC)
    result = to_uk(dt_utc)
    assert result.hour == 11
    assert result.utcoffset() == timedelta(0)  # GMT


def test_to_uk_summer_applies_bst():
    dt_utc = datetime(2026, 7, 2, 11, 0, tzinfo=UTC)
    result = to_uk(dt_utc)
    assert result.hour == 12                         # 11 UTC = 12 BST
    assert result.utcoffset() == timedelta(hours=1)  # BST


def test_to_uk_rejects_naive():
    with pytest.raises(ValueError, match="Naive datetime"):
        to_uk(datetime(2026, 1, 2, 11, 0))


# ---------------------------------------------------------------------------
# uk_midnight_utc
# ---------------------------------------------------------------------------


def test_uk_midnight_january_is_utc():
    result = uk_midnight_utc(date(2026, 1, 2))
    assert result == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)


def test_uk_midnight_july_is_utc_minus_one():
    # 2026-07-02 00:00 BST = 2026-07-01 23:00 UTC
    result = uk_midnight_utc(date(2026, 7, 2))
    assert result == datetime(2026, 7, 1, 23, 0, tzinfo=UTC)


def test_uk_midnight_dst_spring_forward():
    # 2026-03-29: spring forward at 01:00 GMT → 02:00 BST
    # Midnight on 2026-03-29 is still GMT (transition happens at 01:00)
    result = uk_midnight_utc(date(2026, 3, 29))
    assert result == datetime(2026, 3, 29, 0, 0, tzinfo=UTC)


def test_uk_midnight_dst_fall_back():
    # 2026-10-25: fall back at 02:00 BST → 01:00 GMT
    # Midnight on 2026-10-25 is in BST (transition happens at 02:00)
    result = uk_midnight_utc(date(2026, 10, 25))
    assert result == datetime(2026, 10, 24, 23, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# decision_cutoff_utc
# ---------------------------------------------------------------------------


def test_cutoff_january_gmt():
    # Delivery 2026-01-02, cutoff = 11:00 UK on 2026-01-01 = 11:00 UTC
    result = decision_cutoff_utc(date(2026, 1, 2))
    assert result == datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


def test_cutoff_july_bst():
    # Delivery 2026-07-02, cutoff = 11:00 UK on 2026-07-01 (BST) = 10:00 UTC
    result = decision_cutoff_utc(date(2026, 7, 2))
    assert result == datetime(2026, 7, 1, 10, 0, tzinfo=UTC)


def test_cutoff_custom_hour():
    result = decision_cutoff_utc(date(2026, 1, 3), cutoff_hour=9)
    assert result == datetime(2026, 1, 2, 9, 0, tzinfo=UTC)


def test_cutoff_invalid_hour_raises():
    with pytest.raises(ValueError, match="cutoff_hour"):
        decision_cutoff_utc(date(2026, 1, 2), cutoff_hour=24)


def test_cutoff_hour_zero():
    result = decision_cutoff_utc(date(2026, 1, 2), cutoff_hour=0)
    assert result == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def test_cutoff_dst_boundary_spring():
    # Day before spring forward: 2026-03-28 (still GMT)
    # Delivery 2026-03-29, cutoff = 11:00 UK on 2026-03-28 = 11:00 UTC
    result = decision_cutoff_utc(date(2026, 3, 29))
    assert result == datetime(2026, 3, 28, 11, 0, tzinfo=UTC)


def test_cutoff_dst_boundary_fall_back():
    # Day before fall-back: 2026-10-24 (BST)
    # Delivery 2026-10-25, cutoff = 11:00 UK on 2026-10-24 (BST) = 10:00 UTC
    result = decision_cutoff_utc(date(2026, 10, 25))
    assert result == datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# delivery_window_utc
# ---------------------------------------------------------------------------


def test_delivery_window_january_is_24h():
    start, end = delivery_window_utc(date(2026, 1, 2))
    assert start == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 3, 0, 0, tzinfo=UTC)
    assert (end - start).total_seconds() == 24 * 3600


def test_delivery_window_spring_forward_is_23h():
    # 2026-03-29: clocks go forward; only 23 hours in the day
    start, end = delivery_window_utc(date(2026, 3, 29))
    assert (end - start).total_seconds() == 23 * 3600


def test_delivery_window_fall_back_is_25h():
    # 2026-10-25: clocks go back; 25 hours in the day
    start, end = delivery_window_utc(date(2026, 10, 25))
    assert (end - start).total_seconds() == 25 * 3600
