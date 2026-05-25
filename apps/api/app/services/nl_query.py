import json
import re

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.geospatial import GeoIntent
from app.services.places import find_place_in_text


SYSTEM_PROMPT = """You are a geospatial query interpreter for GeoAPI, a geospatial intervention platform.
Convert natural-language questions into a structured JSON intent that drives a PostGIS query engine.

Dataset context:
- ~1000 territorial interventions distributed across all regions
- Date range: January 2025 – April 2026
- Subtypes: gavion, zanja, reforestacion, presa_filtrante, muestreo_biodiversidad, bordo, terraza, muestreo_suelo
- Statuses: planned, in_progress, completed, validated
- Projects: proj_01 through proj_07
- Regions: north, central
- Polygon areas: zone_a (northern cluster), zone_b (central polygon), zone_c (southern cluster)

Return ONLY valid JSON with exactly this shape — no extra keys, no markdown:
{
  "intent": "nearest" | "nearest_to_place" | "farthest_from_place" | "within_radius" | "within_area" | "count_by_region",
  "lat": number | null,
  "lon": number | null,
  "place": string | null,
  "radius_km": number | null,
  "area_id": "zone_a" | "zone_b" | "zone_c" | null,
  "start_date": "YYYY-MM-DD" | null,
  "end_date": "YYYY-MM-DD" | null,
  "project_id": string | null,
  "status": "planned" | "in_progress" | "completed" | "validated" | null,
  "subtype": "gavion" | "zanja" | "reforestacion" | "presa_filtrante" | "muestreo_biodiversidad" | "bordo" | "terraza" | "muestreo_suelo" | null,
  "region": "north" | "central" | null,
  "explanation": string
}

Rules:
- NEVER generate SQL or code.
- Use only the six allowed intents.
- "explanation" must be a single complete sentence in the same language as the question, describing what query will be executed and any filters applied. Be specific — mention the place, radius, area, or subtype when present.
- For date expressions like "el mes pasado", "marzo 2026", "last month", resolve to absolute YYYY-MM-DD using today's date: 2026-04-22.
- Normalize subtype and status values to their English/canonical form (e.g. "reforestación" → "reforestacion").
- place values must be lowercase with underscores (e.g. "ciudad_de_mexico", "san_luis_potosi").

Intent mapping:
- "más cerca", "cercana", "nearest", "closest" + lat/lon → nearest
- "más cerca de [state]", "nearest to [state]" → nearest_to_place with place
- "más lejano de [state]", "más lejos de [state]", "farthest from [state]" → farthest_from_place with place
- "dentro de X km", "radio de X km", "within X km", "en un radio" → within_radius (extract radius_km and lat/lon)
- "dentro de la zona", "en el polígono", "inside zone_a/b/c", "zona norte/central/cluster" → within_area with area_id
- "cuántas", "count", "por región", "how many", "distribuidas por" → count_by_region

Mexican state values: jalisco, guanajuato, ciudad_de_mexico, queretaro, chiapas, yucatan, sonora,
chihuahua, san_luis_potosi, baja_california_sur, oaxaca, veracruz, puebla, michoacan, nuevo_leon,
tamaulipas, coahuila, durango, sinaloa, zacatecas, nayarit, aguascalientes, colima, tlaxcala, hidalgo
"""


def interpret_question(question: str, db: Session | None = None) -> GeoIntent:
    if settings.fyra_api_key:
        try:
            return _fyra_intent(question)
        except Exception:
            pass
    return _heuristic_intent(question)


def _fyra_intent(question: str) -> GeoIntent:
    payload = {
        "model": settings.fyra_model,
        "temperature": 0,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.fyra_api_key}",
        "Content-Type": "application/json",
        "User-Agent": "geoapi/1.0",
    }
    with httpx.Client(timeout=25.0) as client:
        response = client.post(f"{settings.fyra_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    return GeoIntent.model_validate(json.loads(content))


def _heuristic_intent(question: str) -> GeoIntent:
    text = question.lower()
    lat, lon = _extract_coordinates(text)
    radius = _extract_radius(text)
    area_id = _extract_area_id(text)
    project_id = _extract_project_id(text)
    status = _extract_status(text)
    subtype = _extract_subtype(text)
    place = find_place_in_text(text)

    if place and ("más lejano" in text or "mas lejano" in text or "más lejos" in text or "mas lejos" in text or "farthest" in text):
        filters = _filter_description(status, subtype, project_id)
        return GeoIntent(
            intent="farthest_from_place",
            place=place,
            project_id=project_id,
            status=status,
            subtype=subtype,
            explanation=f"Buscando la intervención más lejana del estado de {place.replace('_', ' ').title()}{filters}.",
        )

    # Priority 1: Nearest neighbor queries (Spanish + English)
    if "closest" in text or "cerca" in text or "nearest" in text:
        filters = _filter_description(status, subtype, project_id)
        if place:
            return GeoIntent(
                intent="nearest_to_place",
                place=place,
                project_id=project_id,
                status=status,
                subtype=subtype,
                explanation=f"Buscando la intervención más cercana al estado de {place.replace('_', ' ').title()}{filters}.",
            )
        coord_desc = f"({lat:.4f}, {lon:.4f})" if lat is not None and lon is not None else "la coordenada indicada"
        return GeoIntent(
            intent="nearest",
            lat=lat,
            lon=lon,
            project_id=project_id,
            status=status,
            subtype=subtype,
            explanation=f"Buscando la intervención más cercana a {coord_desc}{filters}.",
        )

    # Priority 2: Radius queries
    if radius is not None or "radio" in text or "km" in text:
        r = radius or 5
        filters = _filter_description(status, subtype, project_id)
        coord_desc = f"({lat:.4f}, {lon:.4f})" if lat is not None and lon is not None else "la coordenada indicada"
        return GeoIntent(
            intent="within_radius",
            lat=lat,
            lon=lon,
            radius_km=r,
            project_id=project_id,
            status=status,
            subtype=subtype,
            explanation=f"Buscando intervenciones dentro de un radio de {r} km desde {coord_desc}{filters}.",
        )

    # Priority 3: Area/polygon queries
    if area_id or "zona" in text or "polígono" in text or "area" in text or "área" in text or "zone" in text or "inside" in text or "within" in text:
        resolved_area = area_id or "zone_b"
        filters = _filter_description(status, subtype, project_id)
        return GeoIntent(
            intent="within_area",
            area_id=resolved_area,
            project_id=project_id,
            status=status,
            subtype=subtype,
            explanation=f"Contando intervenciones dentro del polígono {resolved_area}{filters}.",
        )

    # Priority 4: Count/aggregate queries (Spanish + English)
    if "cuenta" in text or "count" in text or "cuántas" in text or "cuantos" in text or "how many" in text or "por región" in text or "por region" in text or "by region" in text:
        sub_desc = f" de tipo {subtype}" if subtype else ""
        return GeoIntent(
            intent="count_by_region",
            subtype=subtype,
            explanation=f"Contando intervenciones{sub_desc} agrupadas por región.",
        )

    # Priority 5: Reforestation specific
    if "reforestación" in text or "reforestacion" in text or "reforestation" in text:
        return GeoIntent(
            intent="count_by_region",
            subtype="reforestacion",
            explanation="Contando intervenciones de reforestación agrupadas por región.",
        )

    sub_desc = f" de tipo {subtype}" if subtype else ""
    return GeoIntent(
        intent="count_by_region",
        subtype=subtype,
        explanation=f"Contando intervenciones{sub_desc} agrupadas por región.",
    )


def _filter_description(status: str | None, subtype: str | None, project_id: str | None) -> str:
    parts = []
    if subtype:
        parts.append(f"tipo {subtype}")
    if status:
        parts.append(f"estado {status}")
    if project_id:
        parts.append(project_id)
    return f" ({', '.join(parts)})" if parts else ""


def _extract_coordinates(text: str) -> tuple[float | None, float | None]:
    # Match patterns like "20.701,-103.321" or "20.701, -103.321"
    match = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", text)
    if match:
        # Lat is first, lon is second (in dataset format)
        return float(match.group(1)), float(match.group(2))
    
    # Match patterns like "lat: 20.701, lon: -103.321"
    match = re.search(r"lat[:\s]+(-?\d+\.\d+).*lon[:\s]+(-?\d+\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    
    return None, None


def _extract_radius(text: str) -> float | None:
    # Match patterns like "5km", "5 km", "within 5km"
    match = re.search(r"(\d+(?:\.\d+)?)\s*km", text)
    if match:
        return float(match.group(1))
    
    # Match "within X kilometers"
    match = re.search(r"within\s+(\d+(?:\.\d+)?)\s*kilometers?", text)
    if match:
        return float(match.group(1))
    
    return None


def _extract_area_id(text: str) -> str | None:
    # Direct zone matches
    for area_id in ("zone_a", "zone_b", "zone_c"):
        if area_id in text:
            return area_id
    
    # Spanish area names
    if "central" in text and "polígono" in text or "poligono" in text:
        return "zone_b"
    if "north" in text or "norte" in text:
        return "zone_a"
    if "cluster" in text or "zona_c" in text:
        return "zone_c"
    
    return None


def _extract_project_id(text: str) -> str | None:
    match = re.search(r"proj_\d+", text)
    return match.group(0) if match else None


def _extract_status(text: str) -> str | None:
    # Spanish status keywords
    status_map = {
        "planeada": "planned",
        "planeado": "planned",
        "planned": "planned",
        "en progreso": "in_progress",
        "in_progress": "in_progress",
        "completada": "completed",
        "completado": "completed",
        "completed": "completed",
        "validada": "validated",
        "validado": "validated",
        "validated": "validated",
    }
    
    for keyword, status in status_map.items():
        if keyword in text:
            return status
    
    return None


def _extract_subtype(text: str) -> str | None:
    known = [
        ("gavión", "gavion"),
        ("gavion", "gavion"),
        ("zanja", "zanja"),
        ("reforestación", "reforestacion"),
        ("reforestacion", "reforestacion"),
        ("reforestation", "reforestacion"),
        ("presa filtrante", "presa_filtrante"),
        ("presa_filtrante", "presa_filtrante"),
        ("muestreo biodiversidad", "muestreo_biodiversidad"),
        ("muestreo_biodiversidad", "muestreo_biodiversidad"),
        ("biodiversity", "muestreo_biodiversidad"),
        ("bordo", "bordo"),
        ("terraza", "terraza"),
        ("terrace", "terraza"),
        ("muestreo suelo", "muestreo_suelo"),
        ("muestreo_suelo", "muestreo_suelo"),
        ("soil sample", "muestreo_suelo"),
    ]
    
    for keyword, subtype in known:
        if keyword in text:
            return subtype
    
    return None
