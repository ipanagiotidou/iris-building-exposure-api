"""
This file writes to PostGIS using your ORM models.

This file coordinates:
-  write raw
-  normalize
-  write canonical


The normalization process should be separate from the database writing process, 
so that it can be easily tested and reused in different contexts 
(e.g., if we want to normalize OSM data for a different use case, 
or if we want to normalize Microsoft Building data).
"""

import pandas as pd
from geopandas import GeoDataFrame

from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape

from app.models.building import Building
from app.models.source_building import OSMBuildingRaw


def ingest_raw_osm_buildings(raw_osm_gdf: GeoDataFrame, db: Session) -> int:
    """
    Insert the prepared raw OSM rows into the Database.
    Return the number of inserted records.
    """

    inserted = 0 

    # iterrows() iterate over the rows of a DataFrame as (index, Series) pairs and insert them into the database
    # for larger datasets, it would be more efficient to use bulk insert methods, but not in the scope of this project.
    for _, row in raw_osm_gdf.iterrows():  # index, row pairs 

        # Convert geometry to WKB format for PostGIS \x01\x03\x00\... etc
        # WKB is a compact binary representation of geometry that is more efficient for storage and querying in PostGIS compared to WKT (Well-Known Text) or GeoJSON.


        record = OSMBuildingRaw(
            osm_id=str(row.get("osm_id")),
            element=row.get("element"),

            geom = from_shape(row.geometry, srid=4326), # this function converts a Shapely geometry to a WKBElement that can be stored in PostGIS. It also sets the SRID to 4326. 
            
            building = row.get("building"), 
            building_use=row.get("building:use"),
            building_levels=row.get("building:levels"),
            building_material=row.get("building:material"),
            height=row.get("height"),

            roof_shape=row.get("roof:shape"),
            roof_material=row.get("roof:material"),
            roof_levels=row.get("roof:levels"),
            roof_orientation=row.get("roof:orientation"),
            roof_height=row.get("roof:height"), 
            roof_direction=row.get("roof:direction"),

            tags_json=row.get("tags_json")  # store all original tags as JSON
        )

        db.add(record)
        inserted += 1
        
    db.commit()
    return inserted 





def ingest_canonical_buildings(canonical_gdf: GeoDataFrame, db: Session) -> int:
    """
    Insert normalized building rows into buildings.
    """
    inserted = 0

    for _, row in canonical_gdf.iterrows():
        building = Building(
            source_dataset=row["source_dataset"],
            source_record_id=row["source_record_id"],

            geom=from_shape(row["geom"], srid=4326),
            centroid=from_shape(row["centroid"], srid=4326) if row["centroid"] is not None else None,
            footprint_area_m2=row.get("footprint_area_m2"),
            floorspace_m2=row.get("floorspace_m2"),

            building_type=row.get("building_type"),
            construction_type=row.get("construction_type"),
            occupancy_type=row.get("occupancy_type"),
            num_storeys=row.get("num_storeys"),  
            

            height_m=row.get("height_m"),
            roof_shape=row.get("roof_shape"),
            year_built=row.get("year_built"),

            

            building_type_source=row.get("building_type_source"),
            construction_type_source=row.get("construction_type_source"),
            occupancy_type_source=row.get("occupancy_type_source"),
            num_storeys_source=row.get("num_storeys_source"),
            height_m_source=row.get("height_m_source"),
            roof_shape_source=row.get("roof_shape_source"),
            year_built_source=row.get("year_built_source"),

            tags_json=row.get("tags_json"),

            is_matched=row.get("is_matched", False),
            match_id=row.get("match_id"),
            match_score=row.get("match_score"),
            inference_method=row.get("inference_method"),
            confidence_score=row.get("confidence_score"),
            notes=row.get("notes")

        )

        db.add(building)
        inserted += 1

    db.commit()
    return inserted 

