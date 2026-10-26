"""Tests for GET /api/overview."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.main import app
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_windfor_for_date(delivery_date_str: str) -> list[WindForRecord]:
    from datetime import date
    d = date.fromisoformat(delivery_date_str)
    base_start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC)
    pub = base_start - timedelta(hours=15)
    return [
        WindForRecord.model_validate({
            "dataset": "WINDFOR",
            "publishTime": pub.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "startTime": (base_start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 13000 + h * 40,
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
                "generation": 12000 + h * 50,
            }))
    return records


def _mocks_for_dates(dates: list[str]):
    all_wf = []
    all_fh = []
    for d in dates:
        all_wf.extend(_make_windfor_for_date(d))
        all_fh.extend(_make_fuelhh_for_date(d))

    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)

    wf.fetch.side_effect = lambda pf, pt: [r for r in all_wf if pf <= r.publish_time <= pt]
    fh.fetch.side_effect = lambda pf, pt: [r for r in all_fh if pf <= r.start_time < pt]
    return wf, fh


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Custom range
# ---------------------------------------------------------------------------


def test_overview_custom_range_jan1_jan2(client):
    wf, fh = _mocks_for_dates(["2026-01-01", "2026-01-02"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    resp = client.get("/api/overview?from_date=2026-01-01&to_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 2
    assert len(data["days"]) == 2
    assert data["aggregate_metrics"] is not None


def test_overview_aggregate_metrics_present(client):
    wf, fh = _mocks_for_dates(["2026-01-01", "2026-01-02"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/overview?from_date=2026-01-01&to_date=2026-01-02").json()
    agg = data["aggregate_metrics"]
    assert agg["evaluation_hours"] == 48  # 2 days × 24 hours
    assert agg["mae_mw"] is not None


def test_overview_schema_fields_present(client):
    wf, fh = _mocks_for_dates(["2026-01-01"])
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/overview?from_date=2026-01-01&to_date=2026-01-01").json()
    for field in ["from_date", "to_date", "cutoff_hour", "total_days",
                  "days_with_data", "failed_dates", "aggregate_metrics", "days"]:
        assert field in data, f"Missing field: {field}"


def test_overview_all_days_fail_aggregate_none(client):
    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)
    wf.fetch.return_value = []
    fh.fetch.return_value = []

    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/overview?from_date=2026-01-01&to_date=2026-01-02").json()
    assert data["aggregate_metrics"] is None
    assert data["days"] == []
    assert len(data["failed_dates"]) == 2


def test_overview_failed_dates_not_in_days(client):
    # Only Jan 1 has a vintage. Gate mock: only return records when fetching for Jan 1's
    # cutoff window (publish_to <= 2025-12-31T11:00Z). Jan 2 and Jan 3 cutoffs are later.
    wf_jan1 = _make_windfor_for_date("2026-01-01")
    fh_jan1 = _make_fuelhh_for_date("2026-01-01")

    jan1_cutoff = datetime(2025, 12, 31, 11, 0, tzinfo=UTC)

    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)

    wf.fetch.side_effect = (
        lambda pf, pt: [r for r in wf_jan1 if pf <= r.publish_time <= pt]
        if pt <= jan1_cutoff else []
    )
    fh.fetch.side_effect = lambda pf, pt: [r for r in fh_jan1 if pf <= r.start_time < pt]

    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    data = client.get("/api/overview?from_date=2026-01-01&to_date=2026-01-03").json()
    assert len(data["days"]) == 1
    assert data["days"][0]["delivery_date"] == "2026-01-01"
    assert "2026-01-02" in data["failed_dates"]
    assert "2026-01-03" in data["failed_dates"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_overview_from_after_to_422(client):
    resp = client.get("/api/overview?from_date=2026-01-31&to_date=2026-01-01")
    assert resp.status_code == 422


def test_overview_range_too_large_422(client):
    resp = client.get("/api/overview?from_date=2026-01-01&to_date=2026-03-15")
    assert resp.status_code == 422
