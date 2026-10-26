"""Tests for the TTL cache and client-level response caching."""

import time
from unittest.mock import patch

import httpx
import pytest
import respx

from app.clients.base import ElexonBaseClient
from app.clients.cache import TTLCache
from app.config import settings

_PATH = "/datasets/WINDFOR/stream"
_PARAMS = {"format": "json"}
_URL = f"{settings.elexon_base_url}{_PATH}"


def _make_client(cache: TTLCache) -> ElexonBaseClient:
    inner = httpx.Client(
        base_url=settings.elexon_base_url,
        timeout=httpx.Timeout(5.0),
        headers={"Accept": "application/json"},
    )
    client = ElexonBaseClient.__new__(ElexonBaseClient)
    client._client = inner
    client._cache = cache
    return client


# ---------------------------------------------------------------------------
# TTLCache unit behavior
# ---------------------------------------------------------------------------


def test_ttl_cache_stores_and_returns():
    cache: TTLCache[int] = TTLCache(ttl_seconds=60, max_entries=4)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_ttl_cache_disabled_when_ttl_zero():
    cache: TTLCache[int] = TTLCache(ttl_seconds=0, max_entries=4)
    assert cache.enabled is False
    cache.set("a", 1)
    assert cache.get("a") is None


def test_ttl_cache_expires():
    cache: TTLCache[int] = TTLCache(ttl_seconds=0.05, max_entries=4)
    cache.set("a", 1)
    time.sleep(0.08)
    assert cache.get("a") is None


def test_ttl_cache_evicts_least_recently_used():
    cache: TTLCache[int] = TTLCache(ttl_seconds=60, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # touch "a" so "b" is now least recently used
    cache.set("c", 3)  # evicts "b"
    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


# ---------------------------------------------------------------------------
# Client-level caching
# ---------------------------------------------------------------------------


@respx.mock
def test_client_caches_repeat_request():
    route = respx.get(_URL).mock(return_value=httpx.Response(200, json=[{"x": 1}]))
    client = _make_client(TTLCache(ttl_seconds=60, max_entries=4))

    first = client.get(_PATH, _PARAMS)
    second = client.get(_PATH, _PARAMS)

    assert first == second == [{"x": 1}]
    assert route.call_count == 1  # second call served from cache


@respx.mock
def test_client_distinguishes_different_params():
    route = respx.get(_URL).mock(return_value=httpx.Response(200, json=[]))
    client = _make_client(TTLCache(ttl_seconds=60, max_entries=4))

    client.get(_PATH, {"format": "json", "day": "2026-01-01"})
    client.get(_PATH, {"format": "json", "day": "2026-01-02"})

    assert route.call_count == 2  # different params => separate cache keys


@respx.mock
def test_client_param_order_does_not_affect_key():
    route = respx.get(_URL).mock(return_value=httpx.Response(200, json=[]))
    client = _make_client(TTLCache(ttl_seconds=60, max_entries=4))

    client.get(_PATH, {"a": "1", "b": "2"})
    client.get(_PATH, {"b": "2", "a": "1"})

    assert route.call_count == 1  # same params, different order => one key


@respx.mock
def test_disabled_cache_always_refetches():
    route = respx.get(_URL).mock(return_value=httpx.Response(200, json=[]))
    client = _make_client(TTLCache(ttl_seconds=0, max_entries=4))

    client.get(_PATH, _PARAMS)
    client.get(_PATH, _PARAMS)

    assert route.call_count == 2


@respx.mock
def test_errors_are_not_cached():
    respx.get(_URL).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json=[{"ok": True}]),
        ]
    )
    client = _make_client(TTLCache(ttl_seconds=60, max_entries=4))

    with patch("app.clients.base.ElexonBaseClient._sleep"):
        with pytest.raises(Exception):
            client.get(_PATH, _PARAMS)  # exhausts retries, nothing cached

        result = client.get(_PATH, _PARAMS)  # retries again, now succeeds
    assert result == [{"ok": True}]
