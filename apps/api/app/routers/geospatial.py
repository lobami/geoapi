from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.geospatial import (
    AggregateRegionRow,
    AreaOut,
    NaturalLanguageRequest,
    NaturalLanguageResponse,
    PointIn,
    PolygonQuery,
    RadiusQuery,
    SummaryOut,
)
from app.services.geospatial import (
    count_by_region,
    intervention_from_place,
    list_areas,
    list_interventions,
    nearest_intervention,
    reference_places,
    summarize,
    within_area,
    within_radius,
)
from app.services.nl_query import interpret_question

router = APIRouter(prefix="/geospatial", tags=["geospatial"])


@router.post("/nearest")
def nearest(query: PointIn, db: Session = Depends(get_db)):
    result = nearest_intervention(db, lat=query.lat, lon=query.lon)
    if not result:
        raise HTTPException(status_code=404, detail="No interventions found")
    return result


@router.get("/reference-places")
def places(db: Session = Depends(get_db)):
    return reference_places(db)


@router.get("/nearest-to-place")
def nearest_to_place(place: str, db: Session = Depends(get_db)):
    result = intervention_from_place(db, place=place, mode="nearest")
    if not result:
        raise HTTPException(status_code=404, detail="Reference place or interventions not found")
    return result


@router.get("/farthest-from-place")
def farthest_from_place(place: str, db: Session = Depends(get_db)):
    result = intervention_from_place(db, place=place, mode="farthest")
    if not result:
        raise HTTPException(status_code=404, detail="Reference place or interventions not found")
    return result


@router.post("/within-radius")
def in_radius(query: RadiusQuery, db: Session = Depends(get_db)):
    filters = {
        "start_date": query.start_date,
        "end_date": query.end_date,
        "status": query.status,
        "project_id": query.project_id,
        "subtype": query.subtype,
    }
    return within_radius(db, lat=query.lat, lon=query.lon, radius_km=query.radius_km, filters=filters)


@router.post("/within-area")
def in_area(query: PolygonQuery, db: Session = Depends(get_db)):
    filters = {
        "start_date": query.start_date,
        "end_date": query.end_date,
        "status": query.status,
        "project_id": query.project_id,
        "subtype": query.subtype,
    }
    result = within_area(db, area_id=query.area_id, filters=filters)
    if not result:
        raise HTTPException(status_code=404, detail="Area not found")
    return result


@router.get("/count-by-region")
def by_region(subtype: str | None = None, db: Session = Depends(get_db)):
    return count_by_region(db, subtype=subtype)


@router.get("/interventions")
def interventions(
    limit: int = 200,
    month: int | None = None,
    year: int | None = None,
    status: str | None = None,
    project_id: str | None = None,
    subtype: str | None = None,
    region: str | None = None,
    db: Session = Depends(get_db),
):
    return list_interventions(
        db,
        limit=limit,
        month=month,
        year=year,
        status=status,
        project_id=project_id,
        subtype=subtype,
        region=region,
    )


@router.get("/areas")
def areas(db: Session = Depends(get_db)):
    return list_areas(db)


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return summarize(db)


@router.post("/ask", response_model=NaturalLanguageResponse)
def ask(request: NaturalLanguageRequest, db: Session = Depends(get_db)):
    intent = interpret_question(request.question, db)

    if intent.intent == "nearest":
        result = nearest_intervention(db, lat=intent.lat or 0, lon=intent.lon or 0, filters=intent.model_dump())
        return {"intent": intent, "result_type": "single", "result": result or {}}
    if intent.intent == "nearest_to_place":
        result = intervention_from_place(db, place=intent.place or "", mode="nearest", filters=intent.model_dump())
        return {"intent": intent, "result_type": "single", "result": result or {}}
    if intent.intent == "farthest_from_place":
        result = intervention_from_place(db, place=intent.place or "", mode="farthest", filters=intent.model_dump())
        return {"intent": intent, "result_type": "single", "result": result or {}}
    if intent.intent == "within_radius":
        result = within_radius(db, lat=intent.lat or 0, lon=intent.lon or 0, radius_km=intent.radius_km or 5, filters=intent.model_dump())
        return {"intent": intent, "result_type": "collection", "result": result}
    if intent.intent == "within_area":
        result = within_area(db, area_id=intent.area_id or "zone_b", filters=intent.model_dump())
        return {"intent": intent, "result_type": "count", "result": result or {}}

    result = count_by_region(db, subtype=intent.subtype)
    return {"intent": intent, "result_type": "aggregate", "result": result}
