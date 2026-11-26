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



# ORCHESTRATE
def prepare_source_records(
    gdf: gpd.GeoDataFrame,
    source_dataset: str,
    source_id_column: str,
) -> list[dict]:
    """
    Generic preparation of records for the persistence layer, including CRS conversion and database geometry construction.

    Convert a normalized GeoDataFrame into database-ready records.

    Expected input:
    - Unique source identifiers.
    - Polygon or MultiPolygon geometries.
    - A defined CRS.
    """

    if gdf.empty:
        return []

    if source_id_column not in gdf.columns:
        raise ValueError(f"Source ID column '{source_id_column}' not found.")

    if gdf[source_id_column].isna().any():
        raise ValueError(f"Missing source identifiers in '{source_id_column}'.")

    if gdf[source_id_column].duplicated().any():
        raise ValueError(f"Duplicate source identifiers in '{source_id_column}'.")

    if gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is missing.")

    if not source_dataset:
        raise ValueError("Source dataset cannot be empty.")

    # Transform coordinates to the database CRS.
    prepared_gdf = gdf.to_crs(epsg=4326)

    geometry_column = prepared_gdf.geometry.name

    # List of Dicts.
    records = []

    # iterate over rows.
    for _, row in prepared_gdf.iterrows():

        geometry = row[geometry_column]

        if geometry is None or geometry.is_empty:
            continue

        if isinstance(geometry, Polygon):
            geometry = MultiPolygon([geometry])

        if not isinstance(geometry, MultiPolygon):
            raise ValueError(
                f"Unsupported geometry type: {geometry.geom_type}"
            )

        # Extract attributes from a GeoDataFrame row, turn into DICTIONARY. 
        attributes = row.drop(labels=[geometry_column]).to_dict()

        # based on the SQLAlchemy Model defined in models/ ... the attributes should be JSONB type in PostgreSQL.
        # The GeoDataFrame might contain values that are not NATIVE Python JSON-compatible types.
        # There are types that can cause problems when SQLAlchemy's JSON serializer attempts to convert your dictionary into JSON.
        # That's why we need a conversion function.

        # Prepare the dictionary for JSON serialization
        attributes = _make_json_serializable(attributes)

        records.append(
            {
            "building_id": None,
            "source_dataset": source_dataset,
            "source_record_id": str(row[source_id_column]),
            "source_attributes": attributes,
            "source_geom": from_shape(geometry, srid=4326)
            }
        )

    return records

