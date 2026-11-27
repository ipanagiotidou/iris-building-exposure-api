# This module It is the bridge between your source-specific normalization layer (Adapter+Normalization) and your PostgreSQL persistence layer.
# It receives a normalized GeoDataFrame and the metadata identifying its source, performs the generic preparation required by your database model, 
# and returns records in the exact structure expected by your SourceData model.
# This module constructs the records . - Construct database-ready records
# this service should not insert anything into PostgreSQL. It should return prepared records. 
# A separate repository/persistence component should handle insertion, transactions, and database operations.
# Record construction	Build a list of dictionaries matching the fields expected by your SourceData model.

# SHARED PREP MODULE - IT IS GENERIC DATA PREP
# # Perform operations common to all sources: CRS conversion, geometry serialization, JSON-compatible attributes, and database record construction.
# The shared preparation service should work without importing anything from those source adapters.
# The function is an application SERVICE because it PREPARES DATA FOR THE PERSISTENE LAYER. It is not a CRUD function, and it is not a SOURCE ADAPTER.
# One final distinction: your source normalizers should own source-specific geometry aggregation, while this service should only perform generic preparation.


import math 
import geopandas as gpd
import pandas as pd
import numpy as np 

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, MultiPolygon

from .serialization import _normalize_python_to_json_compatible

# Python serialization layer that converts data from Python, pandas and NumPy into PostgreSQL JSONB
# This func solves an important problem when moving data from GeoPandas into PostgreSQL.
# Responsibility: converting PYTHON, PANDAS, and NUMPY values -->  into values that can be stored as JSON.
# SEE HERE: https://app.notion.com/p/Python-40d347b22d3b801eaf0ffbc678268dac?source=copy_link#423347b22d3b800fbda5dad76d2e0b66



# RESPONSIBILITY: ORCHESTRATE FUNC
# RESPONSIBILITY: take a normalized GeoDataFrame and produce dictionaries that can be used to construct BuildingSourceRecord objects.
def prepare_source_records(
    gdf: gpd.GeoDataFrame,
    source_dataset: str,
    source_id_column: str = "source_record_id",  # I can remove this argument if I introduce a "source_id_column" in the source-specific normalize.py
) -> list[dict]:
    """

    Generic preparation of records for the persistence layer, including CRS conversion and database geometry construction.
    Convert a NORMALIZED (it comes normalized from the sources/) GeoDataFrame into DATABASE-READY records (BuildingSourceRecord model).

    Expected input:
    - gdf: normalized GeoDataFrame, produced by a source-specific normalizer.
    - Unique source identifiers:
    -   source_dataset: identifies the dataset, e.g. "OSM" or "BAG".
    -   source_id_column: the column containing the original source record identifiers.

    A few things:
    - Based on the models/source_building.py we know that the DB expects these attributes:
        - building_id --> this can be Null in the beginning cause it's the connection FK between the source table <--> canonical table. Not established yet.
        - source_dataset --> string
        - source_record_id --> string
        - source_attributes --> JSON-compatible 
        - source_geom --> PostGIS-compatible geometry, MULTIPOLYGON, EPSG:4326

    Responsibilities:
    Step	Responsibility
    1	Validate the input GeoDataFrame
    2	Validate the source dataset identifier
    3	Validate the source ID column
    4	Check for missing or duplicate source IDs
    5	Check that the GeoDataFrame has a CRS
    6	Transform geometries to EPSG:4326
    7	Validate and prepare geometries as MultiPolygon
    8	Separate geometry from attributes
    9	Convert attributes using _normalize_python_to_json_compatible()
    10	Construct database-ready dictionaries
    
    """

    # Validate: if the input GDF is emtpy 
    if gdf.empty:
        return []
    
    # Validate: if the "source_id_column" is in the columns,
    if source_id_column not in gdf.columns:
        raise ValueError(f"Source ID column '{source_id_column}' not found.")

    # Validate: check if there is any missing values in the Source ID column
    # any() function returns True if any item in an iterable are true
    if gdf[source_id_column].isna().any():
        raise ValueError(f"Missing source identifiers in '{source_id_column}'.")

    # Validate: if there are duplicates in the Source ID column
    if gdf[source_id_column].duplicated().any():
        raise ValueError(f"Duplicate source identifiers in '{source_id_column}'.")

    # Validate: CRS is set 
    if gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is missing.")

    # Validate: that the source is given
    if not source_dataset:
        raise ValueError("Source dataset cannot be empty.")

    # Transform coordinates to the database CRS. (defined in the models/source_building.py)
    prepared_gdf = gdf.to_crs(epsg=4326)

    geometry_column = prepared_gdf.geometry.name

    # List of Dicts.
    records = []

    # iterate over rows and prepare each record as a dict with keys as defined in the models/source_building.py and values what's in the given normalized gdf.
    # _ = I don't care about the index
    for _, row in prepared_gdf.iterrows():

        # ---------------------------------------
        # GEOMETRY - prepare
        # 
        # NOTE: DIFFERENCE BETWEEN GEOMETRY & ATTRIBUTES
        #       NOTE: SQLAlchemy already knows how to handle a Python dict when the column is declared as JSONB. 
        #       NOTE: But it doesn't automatically know how to handle a Shapely geometry when the column is declared as PostGIS Geometry.
        #
        # NOTE: the input geometry is coming from a GeoDataFrame using Shapely library geometries (Polygon, MultiPolygon)
        # NOTE: prepare a geometry value that SQLAlchemy/GeoAlchemy2 can insert into the DB column.
        # TODO: from_shape(geometry, srid=4326)	Convert the Shapely geometry into a GeoAlchemy2 geometry value. 
        # NOTE: from_shape() converts that Shapely object into a GeoAlchemy2 ***WKBElement***, carrying the SRID information.
        # NOTE: from_shape() is similar to serialization in the sense that it converts a Python object into a representation that can be stored in the database. 
        # NOTE: But geometry and attributes use different mechanisms because PostgreSQL stores them as different data types.
        # NOTE: For the attributes, the story is different than the geometry
        # NOTE: The database column is JSONB. PostgreSQL understands JSON data, and SQLAlchemy knows how to serialize a Python dictionary into JSON for that column.
        # NOTE: For the attributes, SQLAlchemy then handles JSON serialization when inserting the dictionary into JSONB.
        # NOTE: from_shape() converts Shapely geometry into a spatial representation understood by GeoAlchemy2 and PostGIS.
        # --------------------------------------- 

        
        geometry = row[geometry_column]  # isolates the geometry of this row 

        # skip this record if geometry is empty or None (even tho I have excluded these already! )
        # Even tho I define the geometry column in DB to be Nullable.
        if geometry is None or geometry.is_empty:
            continue

        # prepare geometries as MultiPolygon
        # if the geometry is polygon turn into MultiPolygon
        if isinstance(geometry, Polygon):
            geometry = MultiPolygon([geometry])

        # check if it is in the end a MultiPolygon
        if not isinstance(geometry, MultiPolygon):
            raise ValueError(
                f"Unsupported geometry type: {geometry.geom_type}"
            )

        # Converts Shapely geometry object into a GeoAlchemy2 ***WKBElement***
        geoalchemy2_geometry_value = from_shape(geometry, srid=4326)


        # ---------------------------------------
        # ATTRIBUTES - prepare
        # --------------------------------------- 
        
        # Extract attributes from a GeoDataFrame row --> turn into DICTIONARY. 
        attributes = row.drop(labels=[geometry_column]).to_dict()

        # based on the SQLAlchemy Model defined in models/ ... the attributes should be JSONB type in PostgreSQL.
        # The GeoDataFrame might contain values that are not NATIVE Python JSON-compatible types.
        # There are types that can cause problems when SQLAlchemy's JSON serializer attempts to convert your dictionary into JSON.
        # That's why we need a conversion function.

        # Convert attributes using _normalize_python_to_json_compatible(). The func accepts any type of data as input. 
        # For a dictionary, this func turns all keys into strings, and normalizes the values depending on what data type it is.
        # Returns a dictionary 
        # DB will store the attributes in a JSONB format, that's why I need the serialization
        attributes = _normalize_python_to_json_compatible(attributes)

        # Let's talk about the serialization of geometry 

        records.append(
            {
            "building_id": None,
            "source_dataset": source_dataset,
            "source_record_id": str(row[source_id_column]),
            "source_attributes": attributes,
            "source_geom": geoalchemy2_geometry_value
            }
        )

    return records

