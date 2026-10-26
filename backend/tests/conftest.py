"""Shared pytest fixtures for WindSight backend tests."""

import httpx
import pytest
import respx

from app.clients.base import ElexonBaseClient
from app.config import settings


@pytest.fixture
def mock_transport():
    """Start a respx mock router that intercepts all httpx requests."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def base_client(mock_transport):
    """ElexonBaseClient wired to the respx mock transport."""
    # Override timeout to zero for tests (respx is instant)
    client = httpx.Client(
        base_url=settings.elexon_base_url,
        timeout=httpx.Timeout(5.0),
        headers={"Accept": "application/json"},
    )
    # Patch the internal _client so our mocked transport is used
    elexon = ElexonBaseClient.__new__(ElexonBaseClient)
    elexon._client = client
    yield elexon
    client.close()
