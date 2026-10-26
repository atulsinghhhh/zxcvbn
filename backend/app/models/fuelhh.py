"""Pydantic models for the FUELHH (half-hourly fuel-mix actual) dataset."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FuelHHRecord(BaseModel):
    """One settlement-period actual for a single fuel type.

    Timestamps are always UTC (Z suffix in source).
    generation is in MW (integer in source, stored as float for flexibility).
    """

    dataset: Literal["FUELHH"]
    publish_time: datetime = Field(alias="publishTime")
    start_time: datetime = Field(alias="startTime")
    settlement_date: str = Field(alias="settlementDate")
    settlement_period: int = Field(alias="settlementPeriod", ge=1, le=50)
    fuel_type: str = Field(alias="fuelType")
    generation: float

    model_config = {"populate_by_name": True}

    @field_validator("publish_time", "start_time", mode="before")
    @classmethod
    def ensure_utc(cls, v: object) -> object:
        """Reject naive datetimes — all Elexon timestamps are UTC."""
        if isinstance(v, str):
            return v  # pydantic parses ISO strings with tz info
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetime received; expected UTC-aware ISO string")
        return v
