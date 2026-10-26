"""Tests for FuelHHClient against mocked HTTP responses."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from app.clients.base import ElexonBaseClient
from app.clients.fuelhh_client import FuelHHClient
from app.config import settings
from app.exceptions import ElexonHTTPError, ElexonNetworkError, ElexonValidationError
from app.models.fuelhh import FuelHHRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FUELHH_URL = f"{settings.elexon_base_url}/datasets/FUELHH/stream"

_VALID_RECORD = {
    "dataset": "FUELHH",
    "publishTime": "2026-01-02T08:30:00Z",
    "startTime": "2026-01-02T08:00:00Z",
    "settlementDate": "2026-01-02",
    "settlementPeriod": 17,
    "fuelType": "WIND",
    "generation": 15590,
}

_PUBLISH_FROM = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
_PUBLISH_TO = datetime(2026, 1, 2, 9, 0, tzinfo=UTC)


def make_client(mock_transport: respx.Router) -> FuelHHClient:
    """Build a FuelHHClient whose HTTP calls are intercepted by respx."""
    inner = httpx.Client(
        base_url=settings.elexon_base_url,
        timeout=httpx.Timeout(5.0),
        headers={"Accept": "application/json"},
    )
    elexon = ElexonBaseClient.__new__(ElexonBaseClient)
    elexon._client = inner
    client = FuelHHClient(http=elexon)
    return client


# ---------------------------------------------------------------------------
# Successful retrieval
# ---------------------------------------------------------------------------


def test_fetch_returns_records(mock_transport):
    extra = {**_VALID_RECORD, "settlementPeriod": 18, "publishTime": "2026-01-02T09:00:00Z"}
    payload = [_VALID_RECORD, extra]
    mock_transport.get(FUELHH_URL).mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = make_client(mock_transport)
    records = client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert len(records) == 2
    assert all(isinstance(r, FuelHHRecord) for r in records)
    assert records[0].generation == 15590
    assert records[0].publish_time == datetime(2026, 1, 2, 8, 30, tzinfo=UTC)
    assert records[0].start_time == datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    assert records[0].fuel_type == "WIND"


def test_fetch_empty_result(mock_transport):
    mock_transport.get(FUELHH_URL).mock(
        return_value=httpx.Response(200, json=[])
    )
    client = make_client(mock_transport)
    records = client.fetch(_PUBLISH_FROM, _PUBLISH_TO)
    assert records == []


def test_request_includes_wind_filter(mock_transport):
    """Client must always send fuelType=WIND to the API."""
    captured: list[httpx.Request] = []

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=[])

    mock_transport.get(FUELHH_URL).mock(side_effect=capture_and_respond)
    client = make_client(mock_transport)
    client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert len(captured) == 1
    assert captured[0].url.params.get("fuelType") == "WIND"
    assert captured[0].url.params.get("format") == "json"


def test_request_timestamps_are_utc_z_format(mock_transport):
    captured: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=[])

    mock_transport.get(FUELHH_URL).mock(side_effect=capture)
    client = make_client(mock_transport)
    client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    params = captured[0].url.params
    assert params["publishDateTimeFrom"] == "2026-01-02T08:00:00Z"
    assert params["publishDateTimeTo"] == "2026-01-02T09:00:00Z"


# ---------------------------------------------------------------------------
# Malformed / invalid data
# ---------------------------------------------------------------------------


def test_malformed_record_raises_validation_error(mock_transport):
    """A record with a missing required field must raise ElexonValidationError."""
    bad_payload = [{"dataset": "FUELHH", "publishTime": "2026-01-02T08:30:00Z"}]
    mock_transport.get(FUELHH_URL).mock(
        return_value=httpx.Response(200, json=bad_payload)
    )
    client = make_client(mock_transport)
    with pytest.raises(ElexonValidationError, match="invalid record"):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


def test_wrong_dataset_field_raises_validation_error(mock_transport):
    """A record with dataset != 'FUELHH' must fail validation."""
    bad = {**_VALID_RECORD, "dataset": "SOLAR"}
    mock_transport.get(FUELHH_URL).mock(
        return_value=httpx.Response(200, json=[bad])
    )
    client = make_client(mock_transport)
    with pytest.raises(ElexonValidationError):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


def test_non_array_response_raises_validation_error(mock_transport):
    mock_transport.get(FUELHH_URL).mock(
        return_value=httpx.Response(200, json={"error": "unexpected"})
    )
    client = make_client(mock_transport)
    with pytest.raises(ElexonValidationError, match="Expected JSON array"):
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)


# ---------------------------------------------------------------------------
# HTTP failures
# ---------------------------------------------------------------------------


def test_http_404_raises_immediately(mock_transport):
    """4xx errors must raise ElexonHTTPError without retrying."""
    call_count = 0

    def respond_404(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, text="Not found")

    mock_transport.get(FUELHH_URL).mock(side_effect=respond_404)
    client = make_client(mock_transport)
    with pytest.raises(ElexonHTTPError) as exc_info:
        client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert exc_info.value.status_code == 404
    assert call_count == 1  # no retries


def test_http_503_retries_then_raises(mock_transport):
    """Transient 5xx must be retried up to max_retries times."""
    from unittest.mock import patch

    from app.config import settings

    responses = iter(
        [httpx.Response(503, text="Service Unavailable")] * (1 + settings.http_max_retries)
    )

    mock_transport.get(FUELHH_URL).mock(side_effect=lambda req: next(responses))
    client = make_client(mock_transport)

    # Patch sleep to avoid actual delay in tests
    with patch("app.clients.base.ElexonBaseClient._sleep"):
        with pytest.raises(ElexonHTTPError) as exc_info:
            client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert exc_info.value.status_code == 503


def test_http_503_succeeds_on_retry(mock_transport):
    """A 503 followed by a 200 must succeed."""
    from unittest.mock import patch

    call_count = 0

    def flaky(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, text="retry me")
        return httpx.Response(200, json=[_VALID_RECORD])

    mock_transport.get(FUELHH_URL).mock(side_effect=flaky)
    client = make_client(mock_transport)

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        records = client.fetch(_PUBLISH_FROM, _PUBLISH_TO)

    assert len(records) == 1
    assert call_count == 2


def test_network_error_retries_then_raises(mock_transport):
    """Connection errors must be retried and eventually raise ElexonNetworkError."""
    from unittest.mock import patch

    mock_transport.get(FUELHH_URL).mock(side_effect=httpx.ConnectError("refused"))
    client = make_client(mock_transport)

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        with pytest.raises(ElexonNetworkError):
            client.fetch(_PUBLISH_FROM, _PUBLISH_TO)
