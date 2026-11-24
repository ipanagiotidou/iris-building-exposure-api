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

from app.core.db.db import Base

from app.models.building import Building
from app.models.OLD_source_building import OSMBuildingRaw, BAGBuildingRaw

from app.services.normalize import clean_value, parse_float_maybe, normalize_height_m, normalize_num_storeys, normalize_year_built, normalize_building_type


### --------- 1. OSM.   ------------------------------------------------------------------------------

def ingest_raw_osm_buildings(raw_osm_gdf: GeoDataFrame, db: Session) -> int:
    """
    Insert the prepared raw OSM rows into the Database.
    Skip rows that already exist based on (element, osm_id).
    Return the number of inserted records.
    """

    inserted = 0 

    # GOAL: fast lookup set of all existing unique (element, osm_id) pairs already in the database.
    # FLOW: the db starts emtpy and I am building the set of keys as I go. 
    # db.query builds an SQL query, equivalent to "SELECT element, osm_id FROM osm_buildings_raw;"
    # OSMBuildingRaw.element, OSMBuildingRaw.osm_i  ... are COLUMN REFERENCES ! 
    # similar to ... “Give me only these two columns from the table”
    # .all() executes the query and returns all results. Returns list[tuple]
    # the list turns into a set 
    # str() to avoid mismatches like "123" vs 123
    existing_keys = set(
        (element, str(osm_id))
        for element, osm_id in db.query(OSMBuildingRaw.element, OSMBuildingRaw.osm_id).all()
    )


    # iterrows() iterate over the rows of a DataFrame as (index, Series) pairs and insert them into the database
    # for larger datasets, it would be more efficient to use bulk insert methods, but not in the scope of this project.
    for _, row in raw_osm_gdf.iterrows():  # index, row pairs 
        osm_id=str(row.get("osm_id"))    
        element=row.get("element")

        # Ensure uniqueness of building records
        key = (element, osm_id)
        if key in existing_keys:  # O(1) (constant time)
            continue


        # Note on the Geomtetry: 
        # Convert geometry to WKB format for PostGIS \x01\x03\x00\... etc
        # WKB is a compact binary representation of geometry that is more efficient for storage and querying in PostGIS compared to WKT (Well-Known Text) or GeoJSON.


        record = OSMBuildingRaw(
            osm_id=osm_id,
            element=element,

            geom = from_shape(row.geometry, srid=4326), # this function converts a Shapely geometry to a WKBElement that can be stored in PostGIS. It also sets the SRID to 4326. 
            
            building = clean_value(row.get("building")), 
            building_use=clean_value(row.get("building:use")),
            building_levels=clean_value(row.get("building:levels")),
            building_material=clean_value(row.get("building:material")),
            height=clean_value(row.get("height")),

            roof_shape=clean_value(row.get("roof:shape")),
            roof_material=clean_value(row.get("roof:material")),
            roof_levels=clean_value(row.get("roof:levels")),
            roof_orientation=clean_value(row.get("roof:orientation")),
            roof_height=clean_value(row.get("roof:height")), 
            roof_direction=clean_value(row.get("roof:direction")),

            tags_json=row.get("tags_json")  # store all original tags as JSON
        )

        db.add(record)
        existing_keys.add(key)
        inserted += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print("OSM commit failed:", repr(e))
        raise
    return inserted 






### --------- 2. BAG.   ------------------------------------------------------------------------------


def ingest_raw_bag_buildings(raw_bag_gdf: GeoDataFrame, db: Session) -> int:
    """
    Insert the prepared raw OSM rows into the Database.
    Return the number of inserted records.
    """

    inserted = 0 

    # Build the set of existing unique keys already in the DB
    # bag_id  should change to the original  'identificatie'
    existing_bag_ids = set(
        bag_id for (bag_id,) in db.query(BAGBuildingRaw.bag_id).all()
    )

    # iterrows() iterate over the rows of a DataFrame as (index, Series) pairs and insert them into the database
    # for larger datasets, it would be more efficient to use bulk insert methods, but not in the scope of this project.
    for _, row in raw_bag_gdf.iterrows():  # index, row pairs 

        bag_id=str(row.get("bag_id"))

        # Ensure uniqueness of building records
        if bag_id in existing_bag_ids:
            continue



        # Note on Geometry: 
        # Convert geometry to WKB format for PostGIS \x01\x03\x00\... etc
        # WKB is a compact binary representation of geometry that is more efficient for storage and querying in PostGIS compared to WKT (Well-Known Text) or GeoJSON.


        record = BAGBuildingRaw(
            bag_id=bag_id,

            geom = from_shape(row.geometry, srid=4326), # this function converts a Shapely geometry to a WKBElement that can be stored in PostGIS. It also sets the SRID to 4326. 
            
            # value 0 is for buildings with unknown use. Don't touch here. Normalize in Canonical.
            aantal_verblijfsobjecten = clean_value(row.get("aantal_verblijfsobjecten")), 
            bouwjaar=clean_value(row.get("bouwjaar")),

            # Important to call this function within the ingestion module. It turns NaN into [null] for PostGIS. 
            gebruiksdoel=clean_value(row.get("gebruiksdoel")),
            status=clean_value(row.get("status")),

        )

        db.add(record)
        existing_bag_ids.add(bag_id)
        inserted += 1
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print("OSM commit failed:", repr(e))
        raise
    return inserted 



### --------- 3. GENERALIZED .   ------------------------------------------------------------------------------



def ingest_canonical_buildings(canonical_gdf: GeoDataFrame, db: Session, model_class: Base = Building) -> int:
    """
    Insert normalized building rows into buildings.
    """
    inserted = 0

    for _, row in canonical_gdf.iterrows():
        building = model_class(
            source_dataset=row["source_dataset"],
            source_record_id=row["source_record_id"],

            geom=from_shape(row["geom"], srid=4326),
            # NOT centroid=from_shape(row["centroid"], srid=4326) if row["centroid"] is not None else None,
            footprint_area_m2=row.get("footprint_area_m2"),  # Derived
            floorspace_m2=row.get("floorspace_m2"),          # Derived

            building_type=normalize_building_type(row.get("building_type")),
            construction_type=clean_value(row.get("construction_type")),
            occupancy_type=clean_value(row.get("occupancy_type")),
            num_storeys=normalize_num_storeys(row.get("num_storeys")),  
            

            height_m=normalize_height_m(row.get("height_m")),
            roof_shape=clean_value(row.get("roof_shape")),
            year_built=normalize_year_built(row.get("year_built")),

            

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

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print("OSM commit failed:", repr(e))
        raise
    return inserted 
