

# A FEW WORDS: 
# Source-specific layer. The goal is to make OSM and BAG produce the same kind of normalized GeoDataFrame (SAME CONTRACT), 
# so that both can use the services/prepare_source_records.py service without knowing anything about each other's source formats.

# ----------------------------------------------------------------------------------------------------
# RESPONSIBILITY: 
# 
# First, define the normalizer's output contract. The normalizers understand their source-specific structure.
# 
# Before implementing either normalizer, let's agree on what the PREPARATION SERVICE EXPECTS, based on the function we designed:
#   -  Object type	--> geopandas.GeoDataFrame
#   -  CRS	--> Defined CRS; the preparation service transforms it to EPSG:4326
#   -  Geometry column --> 	Active GeoDataFrame geometry column
#   -  Geometry type --> 	Polygon or MultiPolygon
#   -  Source identifier --> 	One column containing the original source record ID
#   -  Source identifier values	-->  Non-null and unique within the dataset
#   -  Attributes	-->  Original source attributes, excluding geometry
#   -  Geometry	--> One geometry per source record



import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon


def _normalize_osm_gdf(
        gdf: gpd.GeoDataFrame, 

) -> gpd.GeoDataFrame:

    """
    RESPONSIBILITY: create a consistent source identifier while preserving all the original OSM columns.
    - Preserve all original columns.
    - Create a consistent source record identifier.
    - Keep the existing CRS and geometry.


    receives:
    - the gdf from fetching 
    - with defined CRS
    - with a geometry column

    It should define:
    - the source ID column (source-specific) *define the same column for all sources 
    - do not remove any column (keep as it is) !

    """
    normalized_gdf = gdf.copy() 

    # UNIQUE IDENTIFIER: Their IDs are not necessarily unique across element types.
    # Combining the element type and ID gives you a source identifier that distinguishes these records.

    normalized_gdf["source_record_id"] = (
        normalized_gdf["element"].astype(str) 
        + "/" 
        + normalized_gdf["id"].astype(str)
    )


    return normalized_gdf














# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




# OSM-SPECIFIC FUNCTION
# AGGREGATION FUNCTION: NOT SO MUCH VALIDAITON
def _combine_duplicate_osm_geometries(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Combine geometries belonging to duplicate (element, id) records
    into a single MultiPolygon geometry.

    PRECONDITION: I can assume not missing & not empty values.
    """

    if gdf.empty:
        return gdf.copy()

    grouped_records = []

    # FOR EACH GROUP:  I should collect all Polygon geometries 
    # group variable should be all other columns
    for (element, record_id), group in gdf.groupby(["element", "id"], dropna=False):

        # collect all polygons from each group
        polygons = []

        for geometry in group.geometry:

            if isinstance(geometry, Polygon):
                polygons.append(geometry)

            elif isinstance(geometry, MultiPolygon):
                polygons.extend(geometry.geoms)

        # if polygons = empty [] then continue to the next group
        if not polygons:
            continue

        combined_geometry = MultiPolygon(polygons)

        # Keep the attributes from the first record.
        record = group.iloc[0].drop(labels=gdf.geometry.name).to_dict()

        record["element"] = element
        record["id"] = record_id
        record[gdf.geometry.name] = combined_geometry

        grouped_records.append(record)


    # create the geodataframe 
    result = gpd.GeoDataFrame(
        grouped_records,
        geometry=gdf.geometry.name,
        crs=gdf.crs,
    )

    return result





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
        "tags_json",

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

    # keep only the columns I want in the raw table. 
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
     
    local_epsg = 28992  # #  GeoPandas handle the full coordinate transformation: WGS84 (ellipsoid A) --> transformed to Amersfoort datum (ellipsoid Bessel 1841) --> projected  (meters)
    metric_gdf = gdf.to_crs(local_epsg)
    
    # centroid calculated in projected coordinates and stored back in 4326 
    #   because --> database, web maps & APIs expect 4326
    # NOT gdf["centroid"] = metric_gdf.geometry.centroid.to_crs(gdf.crs) 
    # gdf["centroid"] = None


    gdf["footprint_area_m2"] = None # IT WILL BE DERIVED. DO NOT CALCULATE LIKE metric_gdf.geometry.area  # IMPROVEMENT:  This should be DERIVED AT THE END 



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
    gdf["year_built"] = gdf["start_date"] # placeholder for later enrichment. Not present in OSM.

    # floorspace_m2
    gdf["floorspace_m2"] = None  #  Should be None if not present 
    

    #  TAGS:
    gdf["tags_json"] = gdf.apply(build_tags_dict, axis=1)

 
    # PROVENANCE ATTRIBUTES: building_type_source, construction_type_source, occupancy_type_source, num_storeys_source, height_m_source, roof_shape_source, year_built_source
    # ... TO DO
    gdf["building_type_source"] = "osm.building"
    gdf["construction_type_source"] = "osm.building:material" 
    gdf["occupancy_type_source"] = "osm.building:use"
    gdf["num_storeys_source"] = "osm.building:levels"
    gdf["height_m_source"] = "osm.height"
    gdf["roof_shape_source"] = "osm.roof:shape"
    gdf["year_built_source"] =  "osm.start_date"


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
        # NOT "centroid",
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

