# A FEW THINGS: GENERIC MODULE - should be able to ingest anything
# I suggest keeping workflows/ingest_source.py generic, so the same workflow can ingest OSM, BAG, or another source without duplicating the orchestration logic.
# The workflow will call:
# 1. Fetch function.
# 2. Normalize function.
# 3. prepare_source_records().
# 4. CRUD insertion function.

from collections.abc import Callable

import geopandas as gpd
from geopandas import GeoDataFrame 
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
import osmnx as ox
from shapely.geometry import Polygon, box

from app.core.db import db
from app.core.db.db import SessionLocal

from app.models.building import OSMCanonicalBuilding, BAGCanonicalBuilding
from app.models.OLD_source_building import OSMBuildingRaw

from app.schemas.bbox import BBox

from app.services.osm_fetch import fetch_osm_buildings_from_polygon
from app.services.bag_fetch import fetch_bag_buildings_gdf

from app.services.normalize import prepare_raw_osm_buildings_gdf, normalize_osm_gdf_to_canonical
from app.services.normalize import prepare_raw_bag_buildings_gdf, normalize_bag_gdf_to_canonical

from app.services.source_record_preparation import prepare_source_records
from app.crud.source_building import upsert_source_buildings

# Callable meaning sth that can be called ! 
def ingest_source(
        fetch_function: Callable, 
        normalize_function: Callable,
        source_dataset: str,
        session: Session,
) -> int:
    """
    Execute the ingestion workflow for a source dataset.

    Workflow:
        1. Fetch original source dataset. 
        2. Normalize source-specific data.
        3. Prepare database-ready records.
        4. Persist records through CRUD.

    Returns: 
    - Number of prepared records.

    """

    # 1. Fetch original dataset
    # NOTE: the fetched function has a bbox as argument 
    fetched_gdf = fetch_function()

    # Check that it returns a gdf 
    if not isinstance(fetched_gdf, gpd.GeoDataFrame):
        raise TypeError("Fetch function must return a GeoDataFrame.")


    # 2. Normalize source-specific data.
    normalized_gdf = normalize_function(fetched_gdf)

    if not isinstance(normalized_gdf, gpd.GeoDataFrame):
        raise TypeError("Normalize function must return a GeoDataFrame.")

    # 3. Prepare database-ready records.
    # # it returns a list[dict]
    prepared_records = prepare_source_records(
        gdf = normalized_gdf, 
        source_dataset = source_dataset, 
        source_id_column = "source_record_id"
    ) 

    # 4. Persist records through CRUD.
    if not prepared_records: # equivalent to if prepared_records == []:
        return 0


    number_of_records_inserted = upsert_source_buildings(
        db = ,
        records = prepared_records)

    return number_of_records_inserted 

























# ---------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------

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

