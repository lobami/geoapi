from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field


class InterventionOut(BaseModel):
    id: str
    type: str
    subtype: str
    status: str
    project_id: str
    region: str
    operator_id: str
    priority: str
    source: str
    quality_score: float | None = None
    date: date_type | None = None
    timestamp: str | None = None
    lat: float
    lon: float
    metrics: dict | None = None
    metadata: dict | None = Field(default=None, alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class PointIn(BaseModel):
    lat: float
    lon: float


class RadiusQuery(BaseModel):
    lat: float
    lon: float
    radius_km: float = Field(gt=0)
    start_date: date_type | None = None
    end_date: date_type | None = None
    status: str | None = None
    project_id: str | None = None
    subtype: str | None = None


class PolygonQuery(BaseModel):
    area_id: str
    start_date: date_type | None = None
    end_date: date_type | None = None
    status: str | None = None
    project_id: str | None = None
    subtype: str | None = None


class AggregateRegionRow(BaseModel):
    region: str
    count: int


class AreaOut(BaseModel):
    area_id: str
    name: str
    geometry: dict = Field(alias="geometry_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class RegionCountRow(BaseModel):
    region: str
    count: int


class NamedCountRow(BaseModel):
    key: str
    count: int


class TimelineRow(BaseModel):
    month: str
    count: int


class SummaryOut(BaseModel):
    total_interventions: int
    total_areas: int
    avg_quality_score: float | None
    highest_priority_region: str | None
    by_status: list[NamedCountRow]
    by_subtype: list[NamedCountRow]
    by_region: list[RegionCountRow]
    timeline: list[TimelineRow]


class GeoIntent(BaseModel):
    intent: Literal[
        "nearest",
        "nearest_to_place",
        "farthest_from_place",
        "within_radius",
        "within_area",
        "count_by_region",
    ]
    lat: float | None = None
    lon: float | None = None
    place: str | None = None
    radius_km: float | None = None
    area_id: str | None = None
    start_date: date_type | None = None
    end_date: date_type | None = None
    project_id: str | None = None
    status: str | None = None
    subtype: str | None = None
    region: str | None = None
    explanation: str | None = None


class NaturalLanguageRequest(BaseModel):
    question: str


class NaturalLanguageResultItem(BaseModel):
    intervention: InterventionOut | None = None
    distance_m: float | None = None
    distance_km: float | None = None


class NaturalLanguageResponse(BaseModel):
    intent: GeoIntent
    result_type: Literal["single", "collection", "aggregate", "count"]
    result: dict | list
