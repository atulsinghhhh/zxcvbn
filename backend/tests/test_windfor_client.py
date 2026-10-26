"""Tests for WindForClient against mocked HTTP responses."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import respx

from app.clients.base import ElexonBaseClient
from app.clients.cache import TTLCache
from app.clients.windfor_client import WindForClient
from app.config import settings
from app.exceptions import ElexonHTTPError, ElexonNetworkError, ElexonValidationError
from app.models.windfor import WindForRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WINDFOR_URL = f"{settings.elexon_base_url}/datasets/WINDFOR/stream"

_VALID_RECORD = {
    "dataset": "WINDFOR",
    "publishTime": "2026-01-01T09:30:00Z",
    "startTime": "2026-01-02T00:00:00Z",
    "generation": 14500,
}

_PUBLISH_FROM = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
_PUBLISH_TO = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_client(mock_transport: respx.Router) -> WindForClient:
    inner = httpx.Client(
        base_url=settings.elexon_base_url,
        timeout=httpx.Timeout(5.0),
        headers={"Accept": "application/json"},
    )
    elexon = ElexonBaseClient.__new__(ElexonBaseClient)
    elexon._client = inner
    elexon._cache = TTLCache(ttl_seconds=0, max_entries=1)  # disabled for unit tests
    return WindForClient(http=elexon)


def _make_vintage(publish_time: str, n_hours: int = 5) -> list[dict]:
    """Build a synthetic forecast vintage with n_hours records."""
    base = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    return [
        {
            "dataset": "WINDFOR",
            "publishTime": publish_time,
            "startTime": (base + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": 14000 + h * 100,
        }
        for h in range(n_hours)
    ]


# ---------------------------------------------------------------------------
# Successful retrieval
# ---------------------------------------------------------------------------


def test_fetch_returns_records(mock_transport):
    payload = _make_vintage("2026-01-01T09:30:00Z", n_hours=3)
    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=payload))

    client = make_client(mock_transport)
    records = client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert len(records) == 3
    assert all(isinstance(r, WindForRecord) for r in records)
    assert records[0].publish_time == datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    assert records[0].generation == 14000


def test_fetch_empty_result(mock_transport):
    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=[]))
    client = make_client(mock_transport)
    assert client.fetch(_PUBLISH_FROM, _PUBLISH_TO) == []


def test_request_params_are_correct(mock_transport):
    """Client must send publishDateTimeFrom/To and format=json."""
    captured: list[httpx.Request] = []

    def capture(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json=[])

    mock_transport.get(WINDFOR_URL).mock(side_effect=capture)
    client = make_client(mock_transport)
    client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    params = captured[0].url.params
    assert params["publishDateTimeFrom"] == "2026-01-01T00:00:00Z"
    assert params["publishDateTimeTo"] == "2026-01-01T12:00:00Z"
    assert params["format"] == "json"
    # fuelType must NOT be sent; WINDFOR is always wind
    assert "fuelType" not in params


# ---------------------------------------------------------------------------
# Vintage selection
# ---------------------------------------------------------------------------


def test_fetch_latest_vintage_selects_correct_vintage(mock_transport):
    """fetch_latest_vintage must select the latest publishTime <= cutoff."""
    cutoff = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)

    # Two vintages: 09:30 (before cutoff) and 11:30 (after cutoff)
    payload = _make_vintage("2026-01-01T09:30:00Z") + _make_vintage("2026-01-01T11:30:00Z")

    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=payload))
    client = make_client(mock_transport)

    vintage = client.fetch_latest_vintage(cutoff)

    # Should return only the 09:30 vintage (5 records)
    assert len(vintage) == 5
    assert all(r.publish_time == datetime(2026, 1, 1, 9, 30, tzinfo=UTC) for r in vintage)


def test_fetch_latest_vintage_exact_cutoff_is_included(mock_transport):
    """A publishTime exactly equal to the cutoff must be selected."""
    cutoff = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    payload = _make_vintage("2026-01-01T09:30:00Z")

    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=payload))
    client = make_client(mock_transport)

    vintage = client.fetch_latest_vintage(cutoff)
    assert len(vintage) == 5
    assert vintage[0].publish_time == cutoff


def test_fetch_latest_vintage_no_data_raises(mock_transport):
    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=[]))
    client = make_client(mock_transport)

    with pytest.raises(ValueError, match="No WINDFOR forecast found"):
        client.fetch_latest_vintage(datetime(2026, 1, 1, 11, 0, tzinfo=UTC))


# ---------------------------------------------------------------------------
# Malformed / invalid data
# ---------------------------------------------------------------------------


def test_malformed_record_raises_validation_error(mock_transport):
    bad = [{"dataset": "WINDFOR", "publishTime": "2026-01-01T09:30:00Z"}]
    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=bad))
    client = make_client(mock_transport)

    with pytest.raises(ElexonValidationError, match="invalid record"):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


def test_wrong_dataset_value_raises_validation_error(mock_transport):
    bad = [{**_VALID_RECORD, "dataset": "FUELHH"}]
    mock_transport.get(WINDFOR_URL).mock(return_value=httpx.Response(200, json=bad))
    client = make_client(mock_transport)

    with pytest.raises(ElexonValidationError):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


def test_non_array_response_raises_validation_error(mock_transport):
    mock_transport.get(WINDFOR_URL).mock(
        return_value=httpx.Response(200, json={"message": "ok"})
    )
    client = make_client(mock_transport)
    with pytest.raises(ElexonValidationError, match="Expected JSON array"):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


# ---------------------------------------------------------------------------
# HTTP and network failures
# ---------------------------------------------------------------------------


def test_http_400_raises_immediately(mock_transport):
    call_count = 0

    def respond_400(req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(400, text="Bad request")

    mock_transport.get(WINDFOR_URL).mock(side_effect=respond_400)
    client = make_client(mock_transport)

    with pytest.raises(ElexonHTTPError) as exc_info:
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert exc_info.value.status_code == 400
    assert call_count == 1


def test_http_503_retries_then_raises(mock_transport):
    from app.config import settings

    responses = iter(
        [httpx.Response(503, text="down")] * (1 + settings.http_max_retries)
    )
    mock_transport.get(WINDFOR_URL).mock(side_effect=lambda req: next(responses))
    client = make_client(mock_transport)

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        with pytest.raises(ElexonHTTPError) as exc_info:
            client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert exc_info.value.status_code == 503


def test_http_503_succeeds_on_second_attempt(mock_transport):
    call_count = 0

    def flaky(req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, text="transient")
        return httpx.Response(200, json=_make_vintage("2026-01-01T09:30:00Z", 1))

    mock_transport.get(WINDFOR_URL).mock(side_effect=flaky)
    client = make_client(mock_transport)

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        records = client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert len(records) == 1
    assert call_count == 2


def test_network_timeout_retries_then_raises(mock_transport):
    mock_transport.get(WINDFOR_URL).mock(side_effect=httpx.TimeoutException("timeout"))
    client = make_client(mock_transport)

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        with pytest.raises(ElexonNetworkError):
            client.fetch(_PUBLISH_FROM, _PUBLISH_TO)
