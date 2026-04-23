from sqlalchemy import Boolean, Date, DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ReferencePlace(Base):
    __tablename__ = "reference_places"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, default="state")
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True))


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, index=True)
    subtype: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    region: Mapped[str] = mapped_column(String, index=True)
    operator_id: Mapped[str] = mapped_column(String, index=True)
    priority: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[str | None] = mapped_column(Date, nullable=True)
    timestamp: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lon: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True))


class Area(Base):
    __tablename__ = "areas"

    area_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    geometry_json: Mapped[dict] = mapped_column("geometry", JSON)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True))
