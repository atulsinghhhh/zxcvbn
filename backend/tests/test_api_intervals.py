"""Tests for GET /api/intervals."""

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

_DELIVERY_DATE = "2026-01-10"
_BASE_START = datetime(2026, 1, 10, 0, 0, tzinfo=UTC)
_PUBLISH_TIME = "2026-01-09T09:00:00Z"


def _make_windfor(n: int = 24) -> list[WindForRecord]:
    return [
        WindForRecord.model_validate({
            "dataset": "WINDFOR",
            "publishTime": _PUBLISH_TIME,
            "startTime": (_BASE_START + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 10000 + h * 200,
        })
        for h in range(n)
    ]


def _make_fuelhh(n_hours: int = 24) -> list[FuelHHRecord]:
    records = []
    for h in range(n_hours):
        for half in (0, 30):
            start = _BASE_START + timedelta(hours=h, minutes=half)
            records.append(FuelHHRecord.model_validate({
                "dataset": "FUELHH",
                "publishTime": (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": _DELIVERY_DATE,
                "settlementPeriod": h * 2 + (1 if half == 0 else 2),
                "fuelType": "WIND",
                "generation": 9000 + h * 150,
            }))
    return records


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _setup_mocks():
    wf = Mock(spec=WindForClient)
    fh = Mock(spec=FuelHHClient)
    wf.fetch.return_value = _make_windfor()
    fh.fetch.return_value = _make_fuelhh()
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------


def test_intervals_valid_date_200(client):
    _setup_mocks()
    resp = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 200


def test_intervals_response_schema(client):
    _setup_mocks()
    data = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}").json()
    for field in ["delivery_date", "decision_cutoff_utc", "selected_vintage_utc",
                  "total", "offset", "limit", "hours"]:
        assert field in data


def test_intervals_default_limit_and_offset(client):
    """Default limit=25, offset=0; January day has 24 hours so 24 returned."""
    _setup_mocks()
    data = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}").json()
    assert data["limit"] == 25
    assert data["offset"] == 0
    assert data["total"] == 24
    # limit=25 > total=24, so all 24 hours are returned
    assert len(data["hours"]) == 24


def test_intervals_pagination_offset(client):
    _setup_mocks()
    data = client.get(
        f"/api/intervals?delivery_date={_DELIVERY_DATE}&offset=10&limit=5"
    ).json()
    assert len(data["hours"]) == 5
    assert data["offset"] == 10
    assert data["limit"] == 5


def test_intervals_offset_beyond_total_empty(client):
    _setup_mocks()
    data = client.get(
        f"/api/intervals?delivery_date={_DELIVERY_DATE}&offset=100&limit=10"
    ).json()
    assert data["hours"] == []
    assert data["total"] == 24


def test_intervals_hour_fields_present(client):
    _setup_mocks()
    data = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}&limit=1").json()
    hour = data["hours"][0]
    for field in ["start_utc", "start_uk", "forecast_mw", "actual_mw",
                  "signed_error_mw", "abs_error_mw"]:
        assert field in hour


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


def test_intervals_missing_delivery_date_422(client):
    resp = client.get("/api/intervals")
    assert resp.status_code == 422


def test_intervals_limit_zero_422(client):
    resp = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}&limit=0")
    assert resp.status_code == 422


def test_intervals_limit_too_large_422(client):
    resp = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}&limit=51")
    assert resp.status_code == 422


def test_intervals_negative_offset_422(client):
    resp = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}&offset=-1")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# No vintage
# ---------------------------------------------------------------------------


def test_intervals_no_vintage_404(client):
    wf = Mock(spec=WindForClient)
    wf.fetch.return_value = []
    fh = Mock(spec=FuelHHClient)
    fh.fetch.return_value = _make_fuelhh()
    app.dependency_overrides[get_windfor_client] = lambda: wf
    app.dependency_overrides[get_fuelhh_client] = lambda: fh

    resp = client.get(f"/api/intervals?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 404
