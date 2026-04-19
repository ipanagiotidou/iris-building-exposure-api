
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


# I could move this function to a utils file, but for now I will keep it here. 
def utm_epsg_from_lonlat(lon: float, lat: float) -> int:
    zone = floor((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone
    return 32700 + zone

# I could move this function to a utils file, but for now I will keep it here. 
def estimate_local_utm_epsg(gdf):
    centroid = gdf.unary_union.centroid
    lon, lat = centroid.x, centroid.y
    return utm_epsg_from_lonlat(lon, lat)


# BUG: 
#   I was getting a lot of NaN values inside PostGIS (SHOULD BE [null]), 
#   I noticed it within the 'gebruiksdoel' column 
# SOLUTION: 
#   Call this function within ingestion module. 
def clean_value(value: Any) -> Any:
    """
    Convert Pandas missing values (NaN)/ empty strings to Python None.
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
        value = value.strip()
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


def parse_int_maybe(value: Any) -> int:
    """
    Parse values like '3', '3.0' into int.
    Returns 0 for records without storey information.
    """
    value = clean_value(value) # returns None or the actual value (excluding empty strings and NaN)

    # could be missing: 
    if value is None:
        return 0

    try:
        return int(float(value))
    except Exception:
        return 0



### --------- 1. OSM.   ------------------------------------------------------------------------------


### --------- 1.1. OSM. - raw  ------------------------------------------------------------------------------

def prepare_raw_osm_buildings_gdf(fetched_osm_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Prepare the fetched OSM GeoDataFrame for raw-table insertion.
    This is still source-like, not canonical.

    fetched OSM gdf
    → prepare_raw_osm_gdf(...)
    → ingest_raw_osm_gdf(...)
    → osm_buildings_raw table
    """

    # By copying the gdf I avoid modifying it outside the function. 
    # This way I keep the original gdf intact, the original columns, the CRS, etc. 
    raw_osm_gdf = fetched_osm_gdf.copy()

    # Normalize source id
    # IMPORTANT NOTE: no casting here. I want to keep the original OSM ID format, which can be numeric or alphanumeric (e.g., "way/12345", "relation/67890").
    # GENERAL NOTE: in the raw layer just store source data “as-is”.
    if "osmid" in raw_osm_gdf.columns:
        raw_osm_gdf["osm_id"] = raw_osm_gdf["osmid"]
    elif "id" in raw_osm_gdf.columns:
        # after flattening the multi-index to normal columns (inside fetching function), 
        # the id column appears as "id" in the gdf, so I need to check for it as well.
        raw_osm_gdf["osm_id"] = raw_osm_gdf["id"]
    else:
        # after flattenin the multi-index inside fetching function, 
        # the index is reset to a simple range (in fetching function) from 0 to len(raw_osm_gdf)-1, 
        # so I can use it as osm_id, but I need to convert it to string to match the OSMBuildingRaw model.
        raw_osm_gdf["osm_id"] = raw_osm_gdf.index.astype(str)


    # Build tags JSON-like dict from the row
    # apply function: 
    # - applies a function along an axis of the DataFrame (e.g., rows or columns).
    # - axis=1 means that the function is applied to EACH ROW (as a SERIES).
    raw_osm_gdf["tags_json"] = raw_osm_gdf.apply(build_tags_dict, axis=1)

    # After constructing the Tags JSON ... 
    # Keep only fields I want in raw storage
    # 15 columns
    raw_cols = [
        # identity
        "osm_id",       # this should be like this (normalized before as "osm_id") 
        "element",

        # building tags
        "building",
        "building:use",
        "building:levels",
        "building:material",
        "height",

        # roof tags
        "roof:shape",
        "roof:material",
        "roof:levels",
        "roof:orientation",
        "roof:height",
        "roof:direction",

        # full tags
        "tags_json"

        # geometry 
        "geometry",

        ]


    # Common in ETL pipelines to ensure a CONSISTENT SCHEMA for the raw data, 
    # even if some columns are missing in the source data.
    # Ensure that the DataFrame has all the expected columns, 
    # even if some of them are missing in the source data.
    # the code below: 
    #   - creates a new column 
    #   - pandas broadcasts None to all rows
    #   - dtype becomes object # NOTE: NOT IDEAL FOR NUMERIC FIELDS, but for simplicity I will keep all fields as strings in the raw table, and only cast them to numeric in the normalization step.
    for col in raw_cols:
        if col not in raw_osm_gdf.columns:
            raw_osm_gdf[col] = None

    # keep only the columns I want in the raw table, and in the order I want.
    prepared_raw_osm_gdf = raw_osm_gdf[raw_cols].copy()

    return prepared_raw_osm_gdf



### --------- 1.2 OSM. - normalized  ------------------------------------------------------------------------------


def normalize_osm_gdf_to_canonical(fetched_osm_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Convert fetched OSM buildings into the canonical building schema.

    fetched OSM gdf
    → normalize_osm_to_canonical(...)
    → ingest_canonical_buildings_gdf(...)
    → buildings table
    """

    gdf = fetched_osm_gdf.copy()

    # keep only buildings that are truly buildings. reject (bridge, roof, collapsed, wall, etc.)
    gdf = gdf[~gdf["building"].isin(REJECT_BUILDING_VALUES)].copy()  # keep everything NOT in the reject list (~negates the condition)


    # IDENTITY ATTRIBUTES:
    # Set the source dataset column to "osm" for all records. 
    gdf["source_dataset"] = "osm"

    # Normalize the source record id - Similar to the prepare_raw_osm_buildings_gdf function, but ... more.
    # NOTE: cast to str in the canonical layer because I want a consistent, stable, system-wide identifier!
    if "osmid" in gdf.columns:
        gdf["source_record_id"] = gdf["osmid"].astype(str)
    elif "id" in gdf.columns:
        # after flattening the multi-index to normal columns (inside fetching function), 
        # the id column appears as "id" in the gdf, so I need to check for it as well.
        gdf["source_record_id"] = gdf["id"].astype(str)
    else:
        # after flattenin the multi-index inside fetching function, 
        # the index is reset to a simple range (in fetching function) from 0 to len(raw_osm_gdf)-1, 
        # so I can use it as osm_id, but I need to convert it to string to match the OSMBuildingRaw model.
        gdf["source_record_id"] = gdf.index.astype(str).astype(str)


    # GEOMETRY & GEOMETRY-DERIVED ATTRIBUTES : geometry, centroid, footprint_area_m2, floorspace_m2 (if building:levels is available)
    # - plane Geometry is handled in the ingestion step.

    # Estimate UTM zone for accurate area and distance calculations.
    # UTM is great when:
    # - your data is in a relatively compact area
    # - the dataset stays mostly inside one UTM zone
     
    local_epsg = estimate_local_utm_epsg(gdf)
    metric_gdf = gdf.to_crs(local_epsg)
    
    # centroid calculated in projected coordinates and stored back in 4326 
    #   because --> database, web maps & APIs expect 4326
    # gdf["centroid"] = metric_gdf.geometry.centroid.to_crs(gdf.crs) # was giving issues
    gdf["centroid"] = None
    
    gdf["footprint_area_m2"] = metric_gdf.geometry.area



    # PARSE MAIN RAW ATTRIBUTES TO CONSTRUCT THE CANONICAL ATTRIBUTES.
    
    # MAIN ATTRIBUTES: building_type, construction_type, occupancy_type, num_storeys, height_m, roof_shape, year_built
    
    # building_type from building tag (should be available since I fetched with building tag)
    gdf["building_type"] = gdf["building"].apply(clean_value) # returns the value or None. 

    
    # construction_type from building:material tag (not ideal, but it's what I have in OSM)
    if "building:material" in gdf.columns:
        gdf["construction_type"] = gdf["building:material"].apply(clean_value) # returns the value or None. 
    else:
        gdf["construction_type"] = None

    # occupancy_type from building:use tag
    if "building:use" in gdf.columns:
        gdf["occupancy_type"] = gdf["building:use"].apply(clean_value) # returns the value or None. 
    else:
        gdf["occupancy_type"] = None


    # num_storeys from building:levels tag
    # NOTE: I will try to convert building:levels to numeric, but if it fails I will keep it as None.
    # NOTE: I had some values like 3.5 for example. I will try to parse them as floats first, and then convert to int if possible.
    if "building:levels" in gdf.columns:
        gdf["num_storeys"] = gdf["building:levels"].apply(parse_int_maybe)
    else:
        gdf["num_storeys"] = None

    # TODO: IS IT IN METERS? 
    # height_m from height tag
    # NOTE: I will try to parse height values like '12', '12.5', '12 m' into float, but if it fails I will keep it as None.
    if "height" in gdf.columns:
        gdf["height_m"] = gdf["height"].apply(parse_float_maybe)
    else:
        gdf["height_m"] = None


    # roof_shape from roof:shape tag
    if "roof:shape" in gdf.columns:
        gdf["roof_shape"] = gdf["roof:shape"].apply(clean_value) # returns the value or None. 
    else:
        gdf["roof_shape"] = None

    # year_built 
    gdf["year_built"] = None # placeholder for later enrichment. Not present in OSM.

    # floorspace_m2
    gdf["floorspace_m2"] = None  #  Should be None if not present 
    

    #  TAGS:
    gdf["tags_json"] = gdf.apply(build_tags_dict, axis=1)

 
    # PROVENANCE ATTRIBUTES: building_type_source, construction_type_source, occupancy_type_source, num_storeys_source, height_m_source, roof_shape_source, year_built_source
    # ... TO DO
    gdf["building_type_source"] = None
    gdf["construction_type_source"] = None 
    gdf["occupancy_type_source"] = None
    gdf["num_storeys_source"] = None
    gdf["height_m_source"] = None
    gdf["roof_shape_source"] = None
    gdf["year_built_source"] = None

    # LATER PIPELINE FIELDS: is_matched, match_id, match_score, inference_method, confidence_score, notes
    gdf["is_matched"] = False
    gdf["match_id"] = None
    gdf["match_score"] = None
    gdf["inference_method"] = None      
    gdf["confidence_score"] = None
    gdf["notes"] = None

    canonical_cols = [

        # Identity
        "source_dataset",
        "source_record_id",


        # Core attributes 
        "building_type",
        "construction_type",
        "occupancy_type",
        "num_storeys",
        "height_m",
        "roof_shape",
        "year_built",

        # Provenance - Source - Origin
        "building_type_source",
        "construction_type_source",
        "occupancy_type_source",
        "num_storeys_source",
        "height_m_source",
        "roof_shape_source",
        "year_built_source",

        # tags
        "tags_json",

        # Geometry & geometry-derived
        "footprint_area_m2",
        "floorspace_m2",
        "centroid",
        "geometry",

        # Later pipeline fields
        "is_matched",
        "match_id",
        "match_score",
        "inference_method",
        "confidence_score",
        "notes"

        ]


    final_gdf = gdf[canonical_cols].copy()

    # rename geometry into geom for PostGIS
    final_gdf = final_gdf.rename(
        columns={
            "geometry": "geom",
        }
    )
    final_gdf = final_gdf.set_geometry("geom")

    return final_gdf









### --------- 2. BAG.   ------------------------------------------------------------------------------


### --------- 2.1. BAG. - raw  ------------------------------------------------------------------------------


def prepare_raw_bag_buildings_gdf(fetched_bag_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Prepare the fetched BAG GeoDataFrame for raw-table insertion.
    This is still source-like, not canonical.

    In “raw" table it is expected to : 
        - convert NaN → None 
    Reason:
        - When I have missing values in BAG → in Postgres should appear as  NULL, NOT  "NaN".



    fetched BAG gdf
    → prepare_raw_bag_gdf(...)
    → ingest_raw_bag_gdf(...)
    → bag_buildings_raw table
    """

    # By copying the gdf I avoid modifying it outside the function. 
    # This way I keep the original gdf intact, the original columns, the CRS, etc. 
    raw_bag_gdf = fetched_bag_gdf.copy()


    # Normalize source id
    # IMPORTANT NOTE: no casting here. I want to keep the original BAG ID format, which can anything.
    # GENERAL NOTE: in the raw layer just store source data “as-is”.
    if "identificatie" in raw_bag_gdf.columns:
        raw_bag_gdf["bag_id"] = raw_bag_gdf["identificatie"]
    else:
        # the index is reset to a simple range (in fetching function) from 0 to len(raw_osm_gdf)-1, 
        # so I can use it as bag_id, but I need to convert it to ... to match the BAGBuildingRaw model data type.
        raw_bag_gdf["bag_id"] = raw_bag_gdf.index  # .astype(str)


    # Normalize 
    # missing values in BAG should appear as  NULL, NOT  "NaN", in Postgres.
    raw_bag_gdf["gebruiksdoel"] = raw_bag_gdf["gebruiksdoel"].apply(clean_value)


    # Keep only fields I want in raw storage
    # 15 columns
    raw_cols = [
        # identity
        "bag_id",       # this should be like this (normalized before as "osm_id") 

        # building information
        "aantal_verblijfsobjecten",
        "bouwjaar",
        "gebruiksdoel",
        "status",

        # geometry 
        "geometry",

        ]


    # Common in ETL pipelines to ensure a CONSISTENT SCHEMA for the raw data, 
    # even if some columns are missing in the source data ensure that the DataFrame has all the expected columns, 
    # the code below: 
    #   - creates a new column 
    #   - pandas broadcasts None to all rows
    #   - dtype becomes object # NOTE: NOT IDEAL FOR NUMERIC FIELDS, but for simplicity I will keep all fields as strings in the raw table, and only cast them to numeric in the normalization step.
    for col in raw_cols:
        if col not in raw_bag_gdf.columns:
            raw_bag_gdf[col] = None

    # keep only the columns I want in the raw table, and in the order I want.
    prepared_raw_bag_gdf = raw_bag_gdf[raw_cols].copy()

    return prepared_raw_bag_gdf



### --------- 2.2 BAG. - normalized  ------------------------------------------------------------------------------



def normalize_bag_gdf_to_canonical(fetched_bag_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Convert fetched BAG buildings into the canonical building schema.

    fetched BAG gdf
    → normalize_bag_to_canonical(...)
    → ingest_canonical_buildings_gdf(...)
    → buildings table
    """

    gdf = fetched_bag_gdf.copy()

    # NOTE: 
    #   - NOT THE RIGHT MOMENT TO EXCLUDE buildings based on status  (demolished, etc.) --> After Matching Geometry Algorithm
    #   *** DO NOT IMPLEMENT HERE: gdf = gdf[~gdf["building"].isin(REJECT_BUILDING_VALUES)].copy()


    # IDENTITY ATTRIBUTES:
    # Set the source dataset column to "bag" for all records. 
    gdf["source_dataset"] = "bag"

    # Normalize the source record id - Similar to the prepare_raw_osm_buildings_gdf function, but ... more.
    # NOTE: cast to str in the canonical layer because I want a consistent, stable, system-wide identifier!
    if "identificatie" in gdf.columns:
        gdf["source_record_id"] = gdf["identificatie"].astype(str)

    else:
        # after flattenin the multi-index inside fetching function, 
        # the index is reset to a simple range (in fetching function) from 0 to len(raw_osm_gdf)-1, 
        # so I can use it as osm_id, but I need to convert it to string to match the BAGBuildingRaw model.
        gdf["source_record_id"] = gdf.index.astype(str).astype(str)



    # GEOMETRY & GEOMETRY-DERIVED ATTRIBUTES : geometry, centroid, footprint_area_m2, floorspace_m2 (if building:levels is available)
    # - plane Geometry is handled in the ingestion step.

    # Estimate UTM zone for accurate area and distance calculations.
    # UTM is great when:
    # - your data is in a relatively compact area
    # - the dataset stays mostly inside one UTM zone
     
    local_epsg = estimate_local_utm_epsg(gdf)
    metric_gdf = gdf.to_crs(local_epsg)
    
    # centroid calculated in projected coordinates and stored back in 4326, because --> database, web maps & APIs expect 4326
    # gdf["centroid"] = metric_gdf.geometry.centroid.to_crs(gdf.crs) # was giving issues --> FIX LATER (I NEED IT FOR THE MATCHING GEOMETRY RESOLUTION)
    gdf["centroid"] = None
    
    gdf["footprint_area_m2"] = metric_gdf.geometry.area



    # PARSE MAIN RAW ATTRIBUTES TO CONSTRUCT THE CANONICAL ATTRIBUTES.
    
    # MAIN ATTRIBUTES: building_type, construction_type, occupancy_type, num_storeys, height_m, roof_shape, year_built
    
    gdf["building_type"] = None  # not present in BAG dataset 
    gdf["construction_type"] = None # not present in BAG dataset
        # occupancy_type from gebruiksdoel tag
    if "gebruiksdoel" in gdf.columns:
        gdf["occupancy_type"] = gdf["gebruiksdoel"].apply(clean_value) # returns the value or None.  (might still contain cast back into NaNs after this)
    else:
        gdf["occupancy_type"] = None


    gdf["num_storeys"] = None  # not present in BAG dataset 
    gdf["height_m"] = None     # not present in BAG dataset  
    gdf["roof_shape"] = None   # not present in BAG dataset  

    # year_built from bouwjaar   
    # IMPORTANT NOTE AND IMPROVE: similar to the number of storeys ... (OSM) returns 0 when there is no information. 
    gdf["year_built"] = gdf["gebruiksdoel"].apply(parse_int_maybe)  

    # floorspace_m2
    gdf["floorspace_m2"] = None # should be None if not present. 
    

    #  TAGS:
    gdf["tags_json"] = None # No tags for BAG 

 
    # PROVENANCE ATTRIBUTES: building_type_source, construction_type_source, occupancy_type_source, num_storeys_source, height_m_source, roof_shape_source, year_built_source
    # ... TO DO
    gdf["building_type_source"] = None
    gdf["construction_type_source"] = None 
    gdf["occupancy_type_source"] = None
    gdf["num_storeys_source"] = None
    gdf["height_m_source"] = None
    gdf["roof_shape_source"] = None
    gdf["year_built_source"] = None

    # LATER PIPELINE FIELDS: is_matched, match_id, match_score, inference_method, confidence_score, notes
    gdf["is_matched"] = False
    gdf["match_id"] = None
    gdf["match_score"] = None
    gdf["inference_method"] = None      
    gdf["confidence_score"] = None
    gdf["notes"] = None

    canonical_cols = [

        # Identity
        "source_dataset",
        "source_record_id",


        # Core attributes 
        "building_type",
        "construction_type",
        "occupancy_type",
        "num_storeys",
        "height_m",
        "roof_shape",
        "year_built",

        # Provenance - Source - Origin
        "building_type_source",
        "construction_type_source",
        "occupancy_type_source",
        "num_storeys_source",
        "height_m_source",
        "roof_shape_source",
        "year_built_source",

        # tags
        "tags_json",

        # Geometry & geometry-derived
        "footprint_area_m2",
        "floorspace_m2",
        "centroid",
        "geometry",

        # Later pipeline fields
        "is_matched",
        "match_id",
        "match_score",
        "inference_method",
        "confidence_score",
        "notes"

        ]


    final_gdf = gdf[canonical_cols].copy()
    
    # rename geometry into geom for PostGIS
    final_gdf = final_gdf.rename(
        columns={
            "geometry": "geom",
        }
    )
    final_gdf = final_gdf.set_geometry("geom")

    return final_gdf
