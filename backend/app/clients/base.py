"""Shared HTTP client with timeout and bounded retry logic."""

import logging
from datetime import UTC, datetime

import httpx

from app.config import settings
from app.exceptions import ElexonHTTPError, ElexonNetworkError

logger = logging.getLogger(__name__)

# HTTP status codes that warrant a retry (server-side transient failures).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _utc_iso(dt: datetime) -> str:
    """Format a UTC datetime as an ISO 8601 string with Z suffix."""
    if dt.tzinfo is None:
        raise ValueError(f"Naive datetime passed to API client: {dt!r}")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonBaseClient:
    """Thin synchronous HTTP wrapper around the Elexon BMRS stream API.

    Retries are applied only to transient (5xx / 429) failures and network
    errors.  4xx responses raise immediately as non-retryable.
    """

    def __init__(self) -> None:
        timeout = httpx.Timeout(settings.http_timeout_seconds)
        self._client = httpx.Client(
            base_url=settings.elexon_base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ElexonBaseClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, path: str, params: dict[str, str]) -> list[dict]:  # type: ignore[type-arg]
        """GET *path* with *params*, returning the parsed JSON array.

        Raises:
            ElexonHTTPError:       non-retryable HTTP error (4xx or exhausted retries).
            ElexonNetworkError:    network-level failure after exhausted retries.
        """
        return self._get_with_retry(path, params)

    def _get_with_retry(self, path: str, params: dict[str, str]) -> list[dict]:  # type: ignore[type-arg]
        attempt = 0
        wait = settings.http_retry_wait_seconds
        max_attempts = 1 + settings.http_max_retries

        while attempt < max_attempts:
            attempt += 1
            try:
                response = self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                if attempt >= max_attempts:
                    raise ElexonNetworkError(
                        f"Network error after {attempt} attempt(s): {exc}"
                    ) from exc
                logger.warning("Network error on attempt %d/%d: %s", attempt, max_attempts, exc)
                self._sleep(wait)
                wait *= 2
                continue

            if response.status_code == 200:
                return response.json()  # type: ignore[no-any-return]

            if response.status_code in _RETRYABLE_STATUS and attempt < max_attempts:
                logger.warning(
                    "HTTP %d on attempt %d/%d; retrying in %.1fs",
                    response.status_code,
                    attempt,
                    max_attempts,
                    wait,
                )
                self._sleep(wait)
                wait *= 2
                continue

            # 4xx or exhausted retries → non-retryable
            raise ElexonHTTPError(
                status_code=response.status_code,
                url=str(response.url),
                body=response.text,
            )

        # Unreachable, but satisfies type checker
        raise ElexonNetworkError("Exceeded retry budget")  # pragma: no cover

    @staticmethod
    def _sleep(seconds: float) -> None:
        import time
        time.sleep(seconds)
