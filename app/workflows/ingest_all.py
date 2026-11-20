
# %%
import geopandas as gpd
from geopandas import GeoDataFrame 
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
import osmnx as ox
from shapely.geometry import Polygon, box

from app.core.db import db
from app.core.db.db import SessionLocal

from app.models.building import OSMCanonicalBuilding, BAGCanonicalBuilding
from app.models.source_building import OSMBuildingRaw

from app.schemas.bbox import BBox

from app.services.osm_fetch import fetch_osm_buildings_from_polygon
from app.services.bag_fetch import fetch_bag_buildings_gdf

from app.services.normalize import prepare_raw_osm_buildings_gdf, normalize_osm_gdf_to_canonical
from app.services.normalize import prepare_raw_bag_buildings_gdf, normalize_bag_gdf_to_canonical

from app.services.ingest import ingest_raw_osm_buildings, ingest_raw_bag_buildings
from app.services.ingest import ingest_canonical_buildings


### -----  OSM ------------------------------------------------------
def run_osm_ingestion_workflow(polygon: Polygon = box(4.357, 52.006, 4.367, 52.012), db: Session = None) -> dict:

    # Fetch OSM
    fetched_gdf = fetch_osm_buildings_from_polygon(polygon= polygon)

    # Prepare the data for RAW Ingestion
    raw_gdf = prepare_raw_osm_buildings_gdf(fetched_gdf)
    raw_inserted_count = ingest_raw_osm_buildings(raw_gdf, db)

    # Normalize the data for the Canonical Ingestion
    canonical_gdf = normalize_osm_gdf_to_canonical(fetched_gdf)
    canonical_inserted_count = ingest_canonical_buildings(canonical_gdf, db, OSMCanonicalBuilding)

    return {
        "fetched": len(fetched_gdf),
        "raw_inserted": raw_inserted_count,
        "canonical_inserted": canonical_inserted_count,
    }


### -----  BAG ------------------------------------------------------
def run_bag_ingestion_workflow(bbox: BBox = BBox(west= 4.357, south = 52.006, east=4.367, north=52.012), db: Session = None) -> dict: 


    # Fetch BAG
    fetched_gdf = fetch_bag_buildings_gdf(bbox)

    # Prepare the data for RAW Ingestion
    raw_gdf = prepare_raw_bag_buildings_gdf(fetched_gdf)
    raw_inserted_count = ingest_raw_bag_buildings(raw_gdf, db)

    # Normalize the data for the Canonical Ingestion
    canonical_gdf = normalize_bag_gdf_to_canonical(fetched_gdf)
    canonical_inserted_count = ingest_canonical_buildings(canonical_gdf, db, BAGCanonicalBuilding)

    return {
        "fetched": len(fetched_gdf),
        "raw_inserted": raw_inserted_count,
        "canonical_inserted": canonical_inserted_count,
    }


# Ingest All (OSM + BAG)
def run_full_ingestion_workflow(polygon: Polygon = box(4.357, 52.006, 4.367, 52.012), bbox: BBox = BBox(west= 4.357, south = 52.006, east=4.367, north=52.012), db: Session = None) -> dict:
    osm_result = run_osm_ingestion_workflow(polygon, db)
    bag_result = run_bag_ingestion_workflow(bbox, db)

    return {
        "osm": osm_result,
        "bag": bag_result,
    }

