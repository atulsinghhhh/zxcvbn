"""Client for the FUELHH (half-hourly fuel-mix actuals) stream endpoint."""

import logging
from datetime import datetime

from pydantic import ValidationError

from app.clients.base import ElexonBaseClient, _utc_iso
from app.exceptions import ElexonValidationError
from app.models.fuelhh import FuelHHRecord

logger = logging.getLogger(__name__)

_PATH = "/datasets/FUELHH/stream"


class FuelHHClient:
    """Retrieves half-hourly national wind-generation actuals.

    Filters to fuelType=WIND; the API supports other fuel types but this
    application only requires wind.
    """

    def __init__(self, http: ElexonBaseClient | None = None) -> None:
        self._http = http or ElexonBaseClient()
        self._owns_http = http is None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "FuelHHClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[FuelHHRecord]:
        """Return WIND actuals published in [publish_from, publish_to].

        Args:
            publish_from: Start of publishTime window (UTC, inclusive).
            publish_to:   End of publishTime window (UTC, inclusive).

        Returns:
            List of FuelHHRecord, may be empty if no data in the window.

        Raises:
            ElexonHTTPError:       HTTP error from the upstream API.
            ElexonNetworkError:    Network failure after retries.
            ElexonValidationError: Response body does not match expected schema.
        """
        params = {
            "publishDateTimeFrom": _utc_iso(publish_from),
            "publishDateTimeTo": _utc_iso(publish_to),
            "fuelType": "WIND",
            "format": "json",
        }
        raw = self._http.get(_PATH, params)
        return self._parse(raw)

    @staticmethod
    def _parse(raw: list[dict]) -> list[FuelHHRecord]:  # type: ignore[type-arg]
        if not isinstance(raw, list):
            raise ElexonValidationError(
                f"Expected JSON array from FUELHH; got {type(raw).__name__}"
            )
        records: list[FuelHHRecord] = []
        errors: list[str] = []
        for i, item in enumerate(raw):
            try:
                records.append(FuelHHRecord.model_validate(item))
            except ValidationError as exc:
                errors.append(f"record[{i}]: {exc.error_count()} error(s): {exc.errors()[0]}")

        if errors:
            summary = "; ".join(errors[:5])
            raise ElexonValidationError(
                f"FUELHH response contained {len(errors)} invalid record(s): {summary}"
            )

        logger.debug("FUELHH: parsed %d records", len(records))
        return records
