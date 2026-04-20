from shapely.geometry import Polygon, box

from app.core.db import SessionLocal
from app.schemas.bbox import BBox
from app.workflows.ingest_all import run_full_ingestion_workflow


def main():
    bbox = BBox(west=4.357, south=52.006, east=4.367, north=52.012)
    polygon = box(4.357, 52.006, 4.367, 52.012)  # shapely Polygon

    db = SessionLocal()
    try:
        result = run_full_ingestion_workflow(polygon = polygon, bbox = bbox, db = db)

        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()

