"""Domain exceptions for the WindSight backend."""


class ElexonClientError(Exception):
    """Base for all Elexon API client errors."""


class ElexonHTTPError(ElexonClientError):
    """Non-retryable HTTP error (4xx or persistent 5xx)."""

    def __init__(self, status_code: int, url: str, body: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} from {url!r}: {body[:200]}")


class ElexonNetworkError(ElexonClientError):
    """Network-level failure (timeout, connection refused, etc.)."""


class ElexonValidationError(ElexonClientError):
    """Response body does not match expected schema."""
