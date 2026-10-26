"""Client for the WINDFOR (national wind-power forecast) stream endpoint."""

import logging
from datetime import datetime

from pydantic import ValidationError

from app.clients.base import ElexonBaseClient, _utc_iso
from app.exceptions import ElexonValidationError
from app.models.windfor import WindForRecord

logger = logging.getLogger(__name__)

_PATH = "/datasets/WINDFOR/stream"


class WindForClient:
    """Retrieves national wind-power forecast vintages.

    The endpoint accepts publishDateTimeFrom/publishDateTimeTo to select
    which forecast publications are returned.  Each publication covers
    roughly 73 hourly delivery periods (~3 days ahead).
    """

    def __init__(self, http: ElexonBaseClient | None = None) -> None:
        self._http = http or ElexonBaseClient()
        self._owns_http = http is None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "WindForClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[WindForRecord]:
        """Return forecast records published in [publish_from, publish_to].

        Args:
            publish_from: Start of publishTime window (UTC, inclusive).
            publish_to:   End of publishTime window (UTC, inclusive).

        Returns:
            List of WindForRecord, may be empty if no forecasts in window.

        Raises:
            ElexonHTTPError:       HTTP error from the upstream API.
            ElexonNetworkError:    Network failure after retries.
            ElexonValidationError: Response body does not match expected schema.
        """
        params = {
            "publishDateTimeFrom": _utc_iso(publish_from),
            "publishDateTimeTo": _utc_iso(publish_to),
            "format": "json",
        }
        raw = self._http.get(_PATH, params)
        return self._parse(raw)

    def fetch_latest_vintage(
        self,
        decision_cutoff: datetime,
        publish_window_hours: int = 48,
    ) -> list[WindForRecord]:
        """Return all records from the single latest vintage at or before *decision_cutoff*.

        Searches backwards up to *publish_window_hours* to find the most
        recent published forecast.  This is the correct vintage to use for
        a day-ahead purchasing decision made at *decision_cutoff*.

        Raises:
            ValueError: If no forecast vintages are found in the search window.
        """
        from datetime import timedelta

        publish_from = decision_cutoff - timedelta(hours=publish_window_hours)
        all_records = self.fetch(publish_from, decision_cutoff)

        if not all_records:
            raise ValueError(
                f"No WINDFOR forecast found in the {publish_window_hours}h window "
                f"before {decision_cutoff.isoformat()}"
            )

        # Guard against API returning records just past the boundary
        eligible = [r for r in all_records if r.publish_time <= decision_cutoff]
        if not eligible:
            raise ValueError(
                f"No WINDFOR vintage at or before cutoff {decision_cutoff.isoformat()}"
            )

        # Pick the latest publishTime that is <= decision_cutoff
        latest_pt = max(r.publish_time for r in eligible)
        vintage = [r for r in eligible if r.publish_time == latest_pt]
        logger.info(
            "fetch_latest_vintage: cutoff=%s selected vintage=%s (%d records)",
            decision_cutoff.isoformat(),
            latest_pt.isoformat(),
            len(vintage),
        )
        return vintage

    @staticmethod
    def _parse(raw: list[dict]) -> list[WindForRecord]:  # type: ignore[type-arg]
        if not isinstance(raw, list):
            raise ElexonValidationError(
                f"Expected JSON array from WINDFOR; got {type(raw).__name__}"
            )
        records: list[WindForRecord] = []
        errors: list[str] = []
        for i, item in enumerate(raw):
            try:
                records.append(WindForRecord.model_validate(item))
            except ValidationError as exc:
                errors.append(f"record[{i}]: {exc.error_count()} error(s): {exc.errors()[0]}")

        if errors:
            summary = "; ".join(errors[:5])
            raise ElexonValidationError(
                f"WINDFOR response contained {len(errors)} invalid record(s): {summary}"
            )

        logger.debug("WINDFOR: parsed %d records", len(records))
        return records
