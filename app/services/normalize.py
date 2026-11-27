# The normalization functions will convert both GeoDataFrames into this common structure.


import math
from math import floor

from typing import Any

import geopandas as gpd
import pandas as pd


# values from Paper https://www.nature.com/articles/s41597-025-06132-z 
# shed could also be included 
REJECT_BUILDING_VALUES = {
    "no",
    "none",
    "No",
    "bridge",
    "pier",
    "road",
    "dam",
    "ruins",
    "ruin",
    "construction",
    "roof",
    "collapsed",
    "foundation",
    "wall",
}


# TODO ... 
# SOS: AFTER MATCHING GEOMETRIES !!!! CAUSE OTHERWISE IT WILL BRING  GEOMETRY FROM OSM.
REJECT_BAG_BUILDING_BASED_ON_STATUS = {
    "...",
    "... ",
}


# # I could move this function to a utils file, but for now I will keep it here. 
# def utm_epsg_from_lonlat(lon: float, lat: float) -> int:
#     zone = floor((lon + 180) / 6) + 1
#     if lat >= 0:
#         return 32600 + zone
#     return 32700 + zone


# # I could move this function to a utils file, but for now I will keep it here. 
# def estimate_local_utm_epsg(gdf):
#     centroid = gdf.unary_union.centroid
#     lon, lat = centroid.x, centroid.y
#     return utm_epsg_from_lonlat(lon, lat)


# BUG: 
#   I was getting a lot of NaN values inside PostGIS (SHOULD BE [null]), 
#   I noticed it within the 'gebruiksdoel' column 
# SOLUTION: 
#   Call this function within ingestion module. 
def clean_value(value: Any) -> Any:
    """
    Convert Pandas missing values (NaN)/ empty strings to Python None.
    Normalize values:
    - NaN → None
    - strip whitespace
    - lowercase strings
    """
    if value is None:
        return None
    
    # try, except for lists, dicts
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, str):
        value = value.strip() # .lower()      # lower(). --> can break things BE CAREFUL.
        if value == "":
            return None
    return value



def build_tags_dict(row: pd.Series) -> dict[str, Any]:
    """
    Keep all (1) non-null (2) non-geometry values as a source tags dict.
    """
    tags: dict[str, Any] = {}
    for key, value in row.items():
        if key == "geometry":
            continue
        cleaned = clean_value(value)
        if cleaned is not None:
            tags[key] = cleaned
    return tags

# For height : 2 <= height_m <= 300
def parse_float_maybe(value: Any) -> float | None:
    """
    Parse values like '12', '12.5', '12 m' into float.
    """
    value = clean_value(value)
    if value is None:
        return None

    try:
        s = str(value).lower().replace("m", "").strip()
        return float(s)
    except Exception:
        return None


# For number of storeys and year_built : 
# - number of storeys : 1 <= num_storeys <= 250
def parse_int_maybe(value: Any) -> int | None:
    """
    Parse values like '3', '3.0' into int.
    Returns 0 for records without storey information.
    """
    value = clean_value(value) # returns None or the actual value (excluding empty strings and NaN)

    # could be missing: 
    if value is None:
        return None

    try:
        parsed = int(float(str(value)))
        return parsed
    except Exception:
        return None


def normalize_height_m(value: Any) -> float | None:
    h = parse_float_maybe(value)
    if h is None:
        return None
    if h < 2 or h > 500:
        return None
    return h


def normalize_num_storeys(value: Any) -> int | None:
    n = parse_int_maybe(value)
    if n is None:
        return None
    if n < 1 or n > 250:
        return None
    return n


def normalize_year_built(value: Any) -> int | None:
    y = parse_int_maybe(value)
    if y is None:
        return None
    if y < 1000 or y > 2026:
        return None
    return y


def normalize_building_type(value):
    value = clean_value(value)

    if value == "yes":
        return None  # or "unknown"

    return value






