"""Tests for GET /api/accuracy."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.exceptions import ElexonHTTPError
from app.main import app
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_api_forecast)
# ---------------------------------------------------------------------------


def _make_windfor_for_date(
    delivery_date_str: str, publish_offset_hours: int = 15
) -> list[WindForRecord]:
    """Vintage published ~15h before the delivery date start."""
    from datetime import date
    d = date.fromisoformat(delivery_date_str)
    base_start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC)
    pub = base_start - timedelta(hours=publish_offset_hours)
    return [
        WindForRecord.model_validate({
            "dataset": "WINDFOR",
            "publishTime": pub.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "startTime": (base_start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 12000 + h * 50,
        })
        for h in range(24)
    ]


def _make_fuelhh_for_date(delivery_date_str: str) -> list[FuelHHRecord]:
    from datetime import date
    d = date.fromisoformat(delivery_date_str)
    base = datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC)
    records = []
    for h in range(24):
        for half in (0, 30):
            start = base + timedelta(hours=h, minutes=half)
            records.append(FuelHHRecord.model_validate({
                "dataset": "FUELHH",
                "publishTime": (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": delivery_date_str,
                "settlementPeriod": h * 2 + (1 if half == 0 else 2),
                "fuelType": "WIND",
                "generation": 11000 + h * 60,
            }))
    return records


def _make_mocks_for_dates(dates: list[str]):
    """Return (windfor_mock, fuelhh_mock) that serve per-date data keyed by publish window."""
    all_windfor: list[WindForRecord] = []
    all_fuelhh: list[FuelHHRecord] = []
    for d in dates:
        all_windfor.extend(_make_windfor_for_date(d))
        all_fuelhh.extend(_make_fuelhh_for_date(d))

    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)

    def windfor_fetch(publish_from, publish_to):
        return [r for r in all_windfor if publish_from <= r.publish_time <= publish_to]

    def fuelhh_fetch(publish_from, publish_to):
        return [r for r in all_fuelhh if publish_from <= r.start_time < publish_to]

    wf.fetch.side_effect = windfor_fetch
    fh.fetch.side_effect = fuelhh_fetch
    return wf, fh


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------


def test_accuracy_valid_range_200(client):
    wf, fh = _make_mocks_for_dates(["2026-01-01", "2026-01-02", "2026-01-03"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    resp = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-01-03")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 3
    assert len(data["days"]) == 3


def test_accuracy_response_schema(client):
    wf, fh = _make_mocks_for_dates(["2026-01-01"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-01-01").json()
    assert "from_date" in data
    assert "to_date" in data
    assert "cutoff_hour" in data
    assert "total_days" in data
    assert "days_with_data" in data
    assert "failed_dates" in data
    assert "days" in data


def test_accuracy_days_with_data_counts_correctly(client):
    wf, fh = _make_mocks_for_dates(["2026-01-01", "2026-01-02"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-01-02").json()
    assert data["days_with_data"] == 2


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


def test_accuracy_from_after_to_422(client):
    resp = client.get("/api/accuracy?from_date=2026-01-31&to_date=2026-01-01")
    assert resp.status_code == 422


def test_accuracy_range_too_large_422(client):
    resp = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-03-15")
    assert resp.status_code == 422


def test_accuracy_missing_from_date_422(client):
    resp = client.get("/api/accuracy?to_date=2026-01-31")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Partial failure: one day has no vintage
# ---------------------------------------------------------------------------


def test_accuracy_one_day_no_vintage_in_failed_dates(client):
    # Jan 1 vintage publishTime = 2025-12-31T09:00Z (15h before midnight Jan 1).
    # Jan 1 cutoff = 2025-12-31T11:00Z → vintage IS in window (publish_to = dec31 11:00).
    # Jan 2 cutoff = 2026-01-01T11:00Z → we gate mock to return empty after dec31 11:00Z,
    # so Jan 2 finds no vintage and goes to failed_dates.
    wf_jan1 = _make_windfor_for_date("2026-01-01")
    fh_jan1 = _make_fuelhh_for_date("2026-01-01")
    fh_jan2 = _make_fuelhh_for_date("2026-01-02")

    jan1_cutoff = datetime(2025, 12, 31, 11, 0, tzinfo=UTC)

    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)

    def windfor_fetch(publish_from, publish_to):
        # Only return the Jan 1 vintage when fetching for Jan 1's cutoff window
        if publish_to <= jan1_cutoff:
            return [r for r in wf_jan1 if publish_from <= r.publish_time <= publish_to]
        return []

    def fuelhh_fetch(publish_from, publish_to):
        all_fh = fh_jan1 + fh_jan2
        return [r for r in all_fh if publish_from <= r.start_time < publish_to]

    wf.fetch.side_effect = windfor_fetch
    fh.fetch.side_effect = fuelhh_fetch

    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    resp = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"]) == 1
    assert data["days"][0]["delivery_date"] == "2026-01-01"
    assert "2026-01-02" in data["failed_dates"]


# ---------------------------------------------------------------------------
# Upstream error propagates
# ---------------------------------------------------------------------------


def test_accuracy_upstream_error_502(client):
    m = Mock(spec=WindForClient)
    m.fetch.side_effect = ElexonHTTPError(500, "https://example.com", "err")
    app.dependency_overrides[get_windfor_client] = lambda: m
    app.dependency_overrides[get_fuelhh_client] = lambda: Mock(spec=FuelHHClient)

    resp = client.get("/api/accuracy?from_date=2026-01-01&to_date=2026-01-01")
    assert resp.status_code == 502
