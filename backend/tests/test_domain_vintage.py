"""Tests for WINDFOR vintage deduplication and selection."""

from datetime import UTC, datetime

import pytest

from app.domain.vintage import deduplicate_windfor, select_vintage
from app.models.windfor import WindForRecord

UTC = UTC


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
# deduplicate_windfor
# ---------------------------------------------------------------------------


def test_dedup_no_duplicates_returns_all():
    records = [
        make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z"),
        make_wf("2026-01-01T09:30:00Z", "2026-01-02T01:00:00Z"),
    ]
    result = deduplicate_windfor(records)
    assert len(result) == 2


def test_dedup_keeps_last_on_duplicate():
    r1 = make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", gen=14000)
    r2 = make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", gen=14500)
    result = deduplicate_windfor([r1, r2])
    assert len(result) == 1
    assert result[0].generation == 14500


def test_dedup_different_vintages_not_merged():
    r1 = make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z")
    r2 = make_wf("2026-01-01T11:30:00Z", "2026-01-02T00:00:00Z")
    result = deduplicate_windfor([r1, r2])
    # Same startTime but different publishTime → separate keys, both kept
    assert len(result) == 2


def test_dedup_empty_input():
    assert deduplicate_windfor([]) == []


# ---------------------------------------------------------------------------
# select_vintage
# ---------------------------------------------------------------------------


def test_select_vintage_picks_latest_before_cutoff():
    cutoff = dt("2026-01-01T11:00:00Z")
    records = [
        make_wf("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z"),
        make_wf("2026-01-01T09:30:00Z", "2026-01-02T01:00:00Z"),  # ← latest ≤ cutoff
        make_wf("2026-01-01T11:30:00Z", "2026-01-02T02:00:00Z"),  # after cutoff
    ]
    selected_pt, vintage = select_vintage(records, cutoff)
    assert selected_pt == dt("2026-01-01T09:30:00Z")
    assert all(r.publish_time == dt("2026-01-01T09:30:00Z") for r in vintage)
    # The 11:30 vintage must not appear
    assert not any(r.publish_time == dt("2026-01-01T11:30:00Z") for r in vintage)


def test_select_vintage_cutoff_exactly_equals_publish_time():
    """A publishTime exactly equal to the cutoff must be selected."""
    cutoff = dt("2026-01-01T09:30:00Z")
    records = [make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z")]
    selected_pt, vintage = select_vintage(records, cutoff)
    assert selected_pt == cutoff
    assert len(vintage) == 1


def test_select_vintage_cutoff_one_second_before_publish():
    """A publishTime one second after the cutoff must NOT be selected."""
    cutoff = dt("2026-01-01T09:29:59Z")
    records = [make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z")]
    with pytest.raises(ValueError, match="No WINDFOR forecast vintage"):
        select_vintage(records, cutoff)


def test_select_vintage_no_records_raises():
    with pytest.raises(ValueError, match="No WINDFOR forecast vintage"):
        select_vintage([], dt("2026-01-01T11:00:00Z"))


def test_select_vintage_all_after_cutoff_raises():
    records = [make_wf("2026-01-01T12:00:00Z", "2026-01-02T00:00:00Z")]
    with pytest.raises(ValueError, match="No WINDFOR forecast vintage"):
        select_vintage(records, dt("2026-01-01T11:00:00Z"))


def test_select_vintage_returns_all_records_for_vintage():
    """select_vintage must return every record in the chosen vintage."""
    cutoff = dt("2026-01-01T11:00:00Z")
    # 3 records in the 09:30 vintage
    records = [
        make_wf("2026-01-01T09:30:00Z", f"2026-01-02T0{h}:00:00Z")
        for h in range(3)
    ]
    # 1 record in an older 07:30 vintage
    records.append(make_wf("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z"))

    selected_pt, vintage = select_vintage(records, cutoff)
    assert selected_pt == dt("2026-01-01T09:30:00Z")
    assert len(vintage) == 3


def test_select_vintage_deduplicates_before_selecting():
    """Duplicates in the latest vintage must be removed, not double-counted."""
    cutoff = dt("2026-01-01T11:00:00Z")
    r1 = make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", gen=14000)
    r2 = make_wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", gen=14500)  # dup
    selected_pt, vintage = select_vintage([r1, r2], cutoff)
    assert len(vintage) == 1
    assert vintage[0].generation == 14500  # last occurrence kept


def test_select_vintage_naive_cutoff_raises():
    from datetime import datetime as dt_cls
    with pytest.raises(ValueError, match="Naive datetime"):
        select_vintage([], dt_cls(2026, 1, 1, 11, 0, 0))
