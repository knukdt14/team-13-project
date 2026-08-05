"""지도 집계 응답 계약."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegionCount(BaseModel):
    code: str
    name: str
    count: int = Field(ge=0)


class RegionSummaryResponse(BaseModel):
    matched: int = Field(ge=0)
    max: int = Field(ge=0)
    nationwide: int = Field(ge=0)
    regions: list[RegionCount] = Field(default_factory=list)


class GeoJsonResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict] = Field(default_factory=list)
