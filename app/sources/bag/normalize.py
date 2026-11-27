

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
     
    local_epsg = 28992  #  GeoPandas handle the full coordinate transformation: WGS84 (ellipsoid A) --> transformed to Amersfoort datum (ellipsoid Bessel 1841) --> projected  (meters)
    metric_gdf = gdf.to_crs(local_epsg)
    
    # # centroid calculated in projected coordinates and stored back in 4326, because --> database, web maps & APIs expect 4326
    # NOT gdf["centroid"] = metric_gdf.geometry.centroid.to_crs(gdf.crs) 
    # # gdf["centroid"] = None  # fallback
    
    gdf["footprint_area_m2"] = None # IT WILL BE DERIVED. DO NOT CALCULATE LIKE metric_gdf.geometry.area


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
    gdf["year_built"] = gdf["bouwjaar"].apply(parse_int_maybe)  

    # floorspace_m2
    gdf["floorspace_m2"] = None # should be None if not present. 
    

    #  TAGS:
    gdf["tags_json"] = None # No tags for BAG 

 
    # PROVENANCE ATTRIBUTES: building_type_source, construction_type_source, occupancy_type_source, num_storeys_source, height_m_source, roof_shape_source, year_built_source
    # ... TO DO
    gdf["building_type_source"] = None
    gdf["construction_type_source"] = None
    gdf["occupancy_type_source"] = "bag.gebruiksdoel"
    gdf["num_storeys_source"] = None
    gdf["height_m_source"] = None
    gdf["roof_shape_source"] = None
    gdf["year_built_source"] = "bag.bouwjaar"

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
        # "centroid",
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
