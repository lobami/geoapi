from sqlalchemy import func, select
from sqlalchemy.orm import Session
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID, ST_Within

from app.models.intervention import Area, Intervention
from app.services.places import get_reference_place, list_reference_places, normalize_place


def _point_geom(lon: float, lat: float):
    return ST_SetSRID(ST_MakePoint(lon, lat), 4326).cast(Intervention.geom.type)


def _point_geog(lon: float, lat: float):
    return _point_geom(lon, lat).cast(Geography)


def _distance_meters(point):
    return func.ST_Distance(Intervention.geom.cast(Geography), point)


def serialize_intervention(intervention: Intervention) -> dict:
    return {
        "id": intervention.id,
        "type": intervention.type,
        "subtype": intervention.subtype,
        "status": intervention.status,
        "project_id": intervention.project_id,
        "region": intervention.region,
        "operator_id": intervention.operator_id,
        "priority": intervention.priority,
        "source": intervention.source,
        "quality_score": intervention.quality_score,
        "date": intervention.date.isoformat() if intervention.date else None,
        "timestamp": intervention.timestamp.isoformat() if intervention.timestamp else None,
        "lat": intervention.lat,
        "lon": intervention.lon,
        "metrics": intervention.metrics,
        "metadata": intervention.metadata_json,
    }


def serialize_area(area: Area) -> dict:
    return {
        "area_id": area.area_id,
        "name": area.name,
        "geometry": area.geometry_json,
    }


def nearest_intervention(db: Session, lat: float, lon: float, filters: dict | None = None):
    filters = filters or {}
    point = _point_geog(lon, lat)
    distance_expr = _distance_meters(point)
    stmt = select(
        Intervention,
        distance_expr.label("distance_m"),
    )
    stmt = _apply_filters(stmt, filters)
    stmt = stmt.order_by(distance_expr.asc()).limit(1)
    row = db.execute(stmt).first()
    if not row:
        return None
    intervention, distance_m = row
    return {
        "intervention": serialize_intervention(intervention),
        "distance_m": float(distance_m),
        "distance_km": round(float(distance_m) / 1000, 3),
    }


def within_radius(db: Session, lat: float, lon: float, radius_km: float, filters: dict | None = None):
    filters = filters or {}
    point = _point_geog(lon, lat)
    radius_m = radius_km * 1000
    distance_expr = _distance_meters(point)
    stmt = select(
        Intervention,
        distance_expr.label("distance_m"),
    ).where(ST_DWithin(Intervention.geom.cast(Geography), point, radius_m))
    stmt = _apply_filters(stmt, filters)
    stmt = stmt.order_by(distance_expr.asc())
    rows = db.execute(stmt).all()
    return [
        {
            "intervention": serialize_intervention(intervention),
            "distance_m": float(distance_m),
            "distance_km": round(float(distance_m) / 1000, 3),
        }
        for intervention, distance_m in rows
    ]


def intervention_from_place(db: Session, place: str, *, mode: str = "nearest", filters: dict | None = None):
    filters = filters or {}
    place_key = normalize_place(place)
    if not place_key:
        return None

    reference = get_reference_place(place_key, db)
    if not reference:
        return None

    point = _point_geog(reference["lon"], reference["lat"])
    distance_expr = _distance_meters(point)
    stmt = select(Intervention, distance_expr.label("distance_m"))
    stmt = _apply_filters(stmt, filters)
    ordering = distance_expr.asc() if mode == "nearest" else distance_expr.desc()
    row = db.execute(stmt.order_by(ordering).limit(1)).first()
    if not row:
        return None

    intervention, distance_m = row
    return {
        "reference_place": reference,
        "mode": mode,
        "intervention": serialize_intervention(intervention),
        "distance_m": float(distance_m),
        "distance_km": round(float(distance_m) / 1000, 3),
    }


def reference_places(db: Session):
    return list_reference_places(db)


def within_area(db: Session, area_id: str, filters: dict | None = None):
    filters = filters or {}
    area = db.get(Area, area_id)
    if not area:
        return None
    stmt = select(Intervention).where(ST_Within(Intervention.geom, area.geom))
    stmt = _apply_filters(stmt, filters)
    items = db.execute(stmt.order_by(Intervention.date.desc(), Intervention.id.asc())).scalars().all()
    return {"area": serialize_area(area), "count": len(items), "items": [serialize_intervention(item) for item in items]}


def count_by_region(db: Session, subtype: str | None = None):
    stmt = select(Intervention.region, func.count(Intervention.id)).group_by(Intervention.region).order_by(func.count(Intervention.id).desc())
    if subtype:
        stmt = stmt.where(Intervention.subtype == subtype)
    rows = db.execute(stmt).all()
    return [{"region": region, "count": count} for region, count in rows]


def list_interventions(
    db: Session,
    *,
    limit: int = 200,
    month: int | None = None,
    year: int | None = None,
    status: str | None = None,
    project_id: str | None = None,
    subtype: str | None = None,
    region: str | None = None,
):
    stmt = select(Intervention)
    stmt = _apply_filters(
        stmt,
        {
            "month": month,
            "year": year,
            "status": status,
            "project_id": project_id,
            "subtype": subtype,
            "region": region,
        },
    )
    items = db.execute(stmt.order_by(Intervention.date.asc(), Intervention.id.asc()).limit(limit)).scalars().all()
    return [serialize_intervention(item) for item in items]


def list_areas(db: Session):
    items = db.execute(select(Area).order_by(Area.area_id.asc())).scalars().all()
    return [serialize_area(item) for item in items]


def summarize(db: Session):
    month_bucket = func.to_char(Intervention.date, "YYYY-MM")
    total_interventions = db.scalar(select(func.count(Intervention.id))) or 0
    total_areas = db.scalar(select(func.count(Area.area_id))) or 0
    avg_quality_score = db.scalar(select(func.avg(Intervention.quality_score)))

    status_rows = db.execute(
        select(Intervention.status, func.count(Intervention.id))
        .group_by(Intervention.status)
        .order_by(func.count(Intervention.id).desc())
    ).all()
    subtype_rows = db.execute(
        select(Intervention.subtype, func.count(Intervention.id))
        .group_by(Intervention.subtype)
        .order_by(func.count(Intervention.id).desc())
        .limit(6)
    ).all()
    region_rows = db.execute(
        select(Intervention.region, func.count(Intervention.id))
        .group_by(Intervention.region)
        .order_by(func.count(Intervention.id).desc())
    ).all()
    timeline_rows = db.execute(
        select(month_bucket, func.count(Intervention.id))
        .group_by(month_bucket)
        .order_by(month_bucket)
    ).all()

    highest_priority_region = db.scalar(
        select(Intervention.region)
        .where(Intervention.priority == "high")
        .group_by(Intervention.region)
        .order_by(func.count(Intervention.id).desc())
        .limit(1)
    )

    return {
        "total_interventions": int(total_interventions),
        "total_areas": int(total_areas),
        "avg_quality_score": round(float(avg_quality_score), 3) if avg_quality_score is not None else None,
        "highest_priority_region": highest_priority_region,
        "by_status": [{"key": status, "count": count} for status, count in status_rows],
        "by_subtype": [{"key": subtype, "count": count} for subtype, count in subtype_rows],
        "by_region": [{"region": region, "count": count} for region, count in region_rows],
        "timeline": [{"month": month, "count": count} for month, count in timeline_rows if month],
    }


def _apply_filters(stmt, filters: dict):
    if filters.get("start_date"):
        stmt = stmt.where(Intervention.date >= filters["start_date"])
    if filters.get("end_date"):
        stmt = stmt.where(Intervention.date <= filters["end_date"])
    if filters.get("status"):
        stmt = stmt.where(Intervention.status == filters["status"])
    if filters.get("project_id"):
        stmt = stmt.where(Intervention.project_id == filters["project_id"])
    if filters.get("subtype"):
        stmt = stmt.where(Intervention.subtype == filters["subtype"])
    if filters.get("region"):
        stmt = stmt.where(Intervention.region == filters["region"])
    if filters.get("month"):
        stmt = stmt.where(func.extract("month", Intervention.date) == filters["month"])
    if filters.get("year"):
        stmt = stmt.where(func.extract("year", Intervention.date) == filters["year"])
    return stmt
