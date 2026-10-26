"""Tests for GET /api/forecast."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_fuelhh_client, get_windfor_client
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.exceptions import ElexonHTTPError, ElexonNetworkError
from app.main import app
from app.models.fuelhh import FuelHHRecord
from app.models.windfor import WindForRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DELIVERY_DATE = "2026-01-15"
_PUBLISH_TIME = "2026-01-14T09:00:00Z"
_BASE_START = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)


def _make_windfor_records(n: int = 24) -> list[WindForRecord]:
    """24-hour vintage for 2026-01-15, published 2026-01-14T09:00Z."""
    return [
        WindForRecord.model_validate({
            "dataset": "WINDFOR",
            "publishTime": _PUBLISH_TIME,
            "startTime": (_BASE_START + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 12000 + h * 100,
        })
        for h in range(n)
    ]


def _make_fuelhh_records(n_hours: int = 24) -> list[FuelHHRecord]:
    """48 half-hourly WIND records for 2026-01-15."""
    records = []
    for h in range(n_hours):
        for half in (0, 30):
            start = _BASE_START + timedelta(hours=h, minutes=half)
            records.append(FuelHHRecord.model_validate({
                "dataset": "FUELHH",
                "publishTime": (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": "2026-01-15",
                "settlementPeriod": h * 2 + (1 if half == 0 else 2),
                "fuelType": "WIND",
                "generation": 11000 + h * 80,
            }))
    return records


def _mock_windfor(records=None):
    m = Mock(spec=WindForClient)
    m.fetch.return_value = records if records is not None else _make_windfor_records()
    return m


def _mock_fuelhh(records=None):
    m = Mock(spec=FuelHHClient)
    m.fetch.return_value = records if records is not None else _make_fuelhh_records()
    return m


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


def test_forecast_valid_date_200(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 200


def test_forecast_response_schema(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    data = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}").json()
    assert data["delivery_date"] == _DELIVERY_DATE
    assert "decision_cutoff_utc" in data
    assert "selected_vintage_utc" in data
    assert "metrics" in data
    assert "hours" in data


def test_forecast_metrics_non_null_when_all_data_present(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    data = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}").json()
    m = data["metrics"]
    assert m["evaluation_hours"] == 24
    assert m["mae_mw"] is not None
    assert m["rmse_mw"] is not None
    assert m["bias_mw"] is not None


def test_forecast_hours_include_error_fields(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    data = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}").json()
    first_hour = data["hours"][0]
    assert "start_utc" in first_hour
    assert "forecast_mw" in first_hour
    assert "actual_mw" in first_hour
    assert "signed_error_mw" in first_hour
    assert "abs_error_mw" in first_hour


def test_forecast_missing_actuals_metrics_null(client):
    """When no actual records, evaluation_hours=0 and metrics are null."""
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh(records=[])

    data = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}").json()
    m = data["metrics"]
    assert m["evaluation_hours"] == 0
    assert m["mae_mw"] is None


def test_forecast_hours_count_matches_delivery_window(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor()
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    data = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}").json()
    # January 2026 is GMT — exactly 24 delivery hours
    assert len(data["hours"]) == 24


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


def test_forecast_missing_delivery_date_422(client):
    resp = client.get("/api/forecast")
    assert resp.status_code == 422


def test_forecast_invalid_cutoff_hour_422(client):
    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}&cutoff_hour=25")
    assert resp.status_code == 422


def test_forecast_invalid_date_format_422(client):
    resp = client.get("/api/forecast?delivery_date=not-a-date")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# No vintage found → 404
# ---------------------------------------------------------------------------


def test_forecast_no_vintage_404(client):
    app.dependency_overrides[get_windfor_client] = lambda: _mock_windfor(records=[])
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Upstream errors
# ---------------------------------------------------------------------------


def test_forecast_upstream_http_error_502(client):
    m = Mock(spec=WindForClient)
    m.fetch.side_effect = ElexonHTTPError(502, "https://example.com", "bad gateway")
    app.dependency_overrides[get_windfor_client] = lambda: m
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 502
    assert resp.json()["error"] == "upstream_error"


def test_forecast_upstream_network_error_503(client):
    m = Mock(spec=WindForClient)
    m.fetch.side_effect = ElexonNetworkError("timeout")
    app.dependency_overrides[get_windfor_client] = lambda: m
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}")
    assert resp.status_code == 503
    assert resp.json()["error"] == "upstream_unavailable"


# ---------------------------------------------------------------------------
# No stack traces in error responses
# ---------------------------------------------------------------------------


def test_forecast_error_response_no_traceback(client):
    m = Mock(spec=WindForClient)
    m.fetch.side_effect = ElexonHTTPError(500, "https://example.com", "internal")
    app.dependency_overrides[get_windfor_client] = lambda: m
    app.dependency_overrides[get_fuelhh_client] = lambda: _mock_fuelhh()

    resp = client.get(f"/api/forecast?delivery_date={_DELIVERY_DATE}")
    body = resp.text
    assert "Traceback" not in body
    assert "traceback" not in body
