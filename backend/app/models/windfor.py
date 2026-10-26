"""Pydantic models for the WINDFOR (national wind-power forecast) dataset."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WindForRecord(BaseModel):
    """One hourly forecast point from a single published vintage.

    publishTime: when this forecast was published (UTC).
    startTime:   start of the delivery hour being forecast (UTC).
    generation:  forecast national wind generation in MW.

    Note: startTime granularity is 1 hour (not 30 min); each vintage covers
    roughly 73 consecutive hours (~3 days ahead).
    """

    dataset: Literal["WINDFOR"]
    publish_time: datetime = Field(alias="publishTime")
    start_time: datetime = Field(alias="startTime")
    generation: float

    model_config = {"populate_by_name": True}

    @field_validator("publish_time", "start_time", mode="before")
    @classmethod
    def ensure_utc(cls, v: object) -> object:
        if isinstance(v, str):
            return v
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetime received; expected UTC-aware ISO string")
        return v
