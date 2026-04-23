import json
import os
from datetime import datetime
from pathlib import Path

from geoalchemy2 import WKTElement

from app.db.session import SessionLocal
from app.models.intervention import Area, Intervention, ReferencePlace


_default = Path(__file__).resolve().parents[1] / "data" / "geospatial_interventions_dataset.json"
DATASET_PATH = Path(os.environ.get("DATASET_PATH", _default))


def main():
    payload = json.loads(DATASET_PATH.read_text())
    with SessionLocal() as db:
        db.query(Intervention).delete()
        db.query(Area).delete()
        db.query(ReferencePlace).delete()

        for place in payload["reference_places"]:
            db.add(
                ReferencePlace(
                    key=place["key"],
                    name=place["name"],
                    lat=place["lat"],
                    lon=place["lon"],
                    type=place["type"],
                    aliases=place.get("aliases", []),
                    geom=WKTElement(f"POINT({place['lon']} {place['lat']})", srid=4326),
                )
            )

        for item in payload["interventions"]:
            db.add(
                Intervention(
                    id=item["id"],
                    type=item["type"],
                    subtype=item["subtype"],
                    status=item["status"],
                    project_id=item["project_id"],
                    region=item["region"],
                    operator_id=item["operator_id"],
                    priority=item["priority"],
                    source=item["source"],
                    quality_score=item.get("quality_score"),
                    date=datetime.fromisoformat(item["date"]).date() if item.get("date") else None,
                    timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")) if item.get("timestamp") else None,
                    metadata_json=item.get("metadata"),
                    metrics=item.get("metrics"),
                    lat=item["coordinates"]["lat"],
                    lon=item["coordinates"]["lon"],
                    geom=WKTElement(f"POINT({item['coordinates']['lon']} {item['coordinates']['lat']})", srid=4326),
                )
            )

        for area in payload["areas"]:
            coords = area["geometry"]["coordinates"][0]
            if coords[0] != coords[-1]:
                coords = coords + [coords[0]]
            wkt_coords = ", ".join(f"{lon} {lat}" for lon, lat in coords)
            db.add(
                Area(
                    area_id=area["area_id"],
                    name=area["name"],
                    geometry_json=area["geometry"],
                    geom=WKTElement(f"POLYGON(({wkt_coords}))", srid=4326),
                )
            )

        db.commit()


if __name__ == "__main__":
    main()
