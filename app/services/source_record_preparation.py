
# SHARED PREP MODULE - IT IS GENERIC
# # Perform operations common to all sources: CRS conversion, geometry serialization, JSON-compatible attributes, and database record construction.
# The shared preparation service should work without importing anything from those source adapters.



from datetime import date, datetime

import geopandas as gpd
import pandas as pd

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, MultiPolygon


def _make_json_serializable(value):
    """Convert pandas and NumPy values into JSON-compatible values."""

    if isinstance(value, dict):
        return {
            str(key): _make_json_serializable(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_make_json_serializable(item) for item in value]

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if hasattr(value, "item") and callable(value.item):
        value = value.item()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if pd.isna(value):
        return None

    return value


def prepare_source_records(
    gdf: gpd.GeoDataFrame,
    source_dataset: str,
    source_id_column: str,
) -> list[dict]:
    """
    Convert a normalized GeoDataFrame into database-ready records.

    Expected input:
    - Unique source identifiers.
    - Polygon or MultiPolygon geometries.
    - A defined CRS.
    """

    if gdf.empty:
        return []

    if source_id_column not in gdf.columns:
        raise ValueError(
            f"Source ID column '{source_id_column}' not found."
        )

    if gdf[source_id_column].isna().any():
        raise ValueError(
            f"Missing source identifiers in '{source_id_column}'."
        )

    if gdf[source_id_column].duplicated().any():
        raise ValueError(
            f"Duplicate source identifiers in '{source_id_column}'."
        )

    if gdf.crs is None:
        raise ValueError("GeoDataFrame CRS is missing.")

    if not source_dataset:
        raise ValueError("Source dataset cannot be empty.")

    # Transform coordinates to the database CRS.
    prepared_gdf = gdf.to_crs(epsg=4326)

    geometry_column = prepared_gdf.geometry.name

    records = []

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

        attributes = row.drop(
            labels=[geometry_column]
        ).to_dict()

        attributes = _make_json_serializable(attributes)

        records.append({
            "building_id": None,
            "source_dataset": source_dataset,
            "source_record_id": str(row[source_id_column]),
            "source_attributes": attributes,
            "source_geom": from_shape(geometry, srid=4326),
        })

    return records

