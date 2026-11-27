import logging 
import pandas as pd
import geopandas as gpd

from app.sources.osm.normalize import _combine_duplicate_osm_geometries

logger = logging.getLogger(__name__) # module's name 


# Responsibility: 
def _inspect_geometries(gdf: gpd.GeoDataFrame) -> dict:
    """
    Inspect geometry conditions and return statistics.
    """

    geom = gdf.geometry  

    # Boolean
    existing_mask = geom.notna()  
    empty_mask = geom.is_empty 
    valid_mask = geom.is_valid

    # All 3 must be true to be valid.
    truly_valid_mask = existing_mask & ~empty_mask & valid_mask
    truly_invalid_mask = existing_mask & ~empty_mask & ~valid_mask

    # Count valid/invalid records
    truly_valid_count = truly_valid_mask.sum()
    truly_invalid_count = truly_invalid_mask.sum()
    
    # Missing values & Empty Geometries 
    stats = {
        "total records": len(gdf),
        "missing": int((~existing_mask).sum()),
        "empty": int(empty_mask.sum()),
        "valid": int(truly_valid_count),
        "invalid": int(truly_invalid_count), 
        "geometry_type": geom.geom_type.value_counts().to_dict(), 
    }


    if stats["invalid"] > 0: 
        logger.warning("Found %s invalid geometries", stats["invalid"] )

    logger.info("Geometry Inspection: %s", stats)

    return stats



# Responsibility: repair  
def _repair_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Repair topologically invalid geometries. 
    PRECONDITION: assume every input geometry is present and non-empty.
    """

    # Create an independent copy that I intend to modify later.  Original gdf remains unchanged.
    copied_gdf = gdf.copy()

    # Boolean
    valid_mask = copied_gdf.geometry.is_valid
    invalid_mask = ~valid_mask

    # Count valid/invalid records
    invalid_count = invalid_mask.sum()

    if invalid_count == 0: 
        logger.info("No geometries require repair.")
        return copied_gdf

    logger.info("Repairing %s invalid geometries.", invalid_count)

    # Repair
    # Repair only Invalid Geometries in the original dataframe
    # SYNTAX: DataFrame.loc[row_labels, column_labels] 
    # RESULT: For the rows where invalid_mask is True, replace the geometry column with the repaired geometries. Maintains their corresponding index values.
    # RULE: When you want to modify the ORIGINAL DataFrame, use .loc[rows, columns]
    copied_gdf.loc[invalid_mask, "geometry"] = (copied_gdf.loc[invalid_mask].geometry.make_valid())

    return copied_gdf


# Responsibility: explode   
def _explode_geometry_collection(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Explode only GeometryCollection geometries.
    """

    copied_gdf = gdf.copy()

    # Identify GeometryCollection geometries
    geom_collection_mask = copied_gdf.geometry.geom_type == "GeometryCollection"
    geom_collection_count = geom_collection_mask.sum()

    if geom_collection_count == 0:
        logger.info("No GeometryCollections found.")
        return copied_gdf

    # Explode only records with geometry type == GeometryCollections 
    exploded_geom_gdf = copied_gdf.loc[geom_collection_mask].explode(index_parts=False)

    # Preserve all unchanged records
    unchanged_geom_gdf = gdf.loc[~geom_collection_mask].copy() # Copy after preserving the original records. 

    # Combine all records back into one gdf
    result_gdf = gpd.GeoDataFrame(
        pd.concat([unchanged_geom_gdf, exploded_geom_gdf]),
        geometry=copied_gdf.geometry.name,
        crs=copied_gdf.crs,
        )

    return result_gdf


# Responsibility:
def _filter_geometry_types(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Keep only Polygon and MultiPolygon geometries.
    """
    
    # Create an independent copy that I intend to modify later.  Original gdf remains unchanged.
    copied_gdf = gdf.copy()

    allowed_types = ["Polygon", "MultiPolygon"]

    # Identify allowed geometry types
    geometry_types = copied_gdf.geometry.geom_type
    mask = geometry_types.isin(allowed_types)

    # Count removed records
    removed_count = (~mask).sum()

    logger.info("Geometry types before filtering:\n%s", geometry_types.value_counts())

    if removed_count > 0:
        logger.info("Removing %s unsupported geometry types", removed_count)

    # Filter and create an independent copy
    filtered_gdf = gdf.loc[mask].copy()

    logger.info("Records before filtering: %s", len(gdf))
    logger.info("Records after  filtering: %s", len(filtered_gdf))

    return filtered_gdf


# Responsibility:
def _remove_missing_and_empty_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    """
    Remove records (rows) with missing or empty geometries. 
    """

    # Boolean Mask
    missing_or_empty = gdf.geometry.isna() | gdf.geometry.is_empty

    filtered_gdf = gdf.loc[~missing_or_empty].copy()

    logger.info("Removed %s rows with missing or empty geometries.", missing_or_empty.sum())

    return filtered_gdf



# Responsibility: ORCHESTRATION FUNCTION
# Orchestrates the previous functions and returns the cleaned GeoDataFrame.
# The last function becomes your main entry point, which your source adapters can call.
def _validate_geometries(gdf: gpd.GeoDataFrame) ->  gpd.GeoDataFrame:
    """
    Repair invalid geometries, remove missing and empty geometries, and retain valid polygonal building footprints.

    """

    logger.info("Starting geometry validation.")

    # Create an independent copy that I intend to modify later.  Original gdf remains unchanged.
    copied_gdf = gdf.copy()

    # 1. Inspect Original gdf 
    _inspect_geometries(copied_gdf)

    # 2. Remove missing & empty geometries 
    # PRECONDITION: From now on, we can assume that every input geometry is present and non-empty.
    filtered_gdf = _remove_missing_and_empty_geometries(copied_gdf)

    # 3. Repair invalid geometries 
    repaired_gdf = _repair_geometries(filtered_gdf) 

    # 4. Explode GeometryCollections  
    exploded_gdf = _explode_geometry_collection(repaired_gdf)

    # 5. Retain Polygon and Multi-Polygon
    polygon_like_gdf = _filter_geometry_types(exploded_gdf)

    # EXTRA STEP: GeometryCollection is exploded into multiple polygon rows, we need to combine those polygon components back into one MultiPolygon before inserting.
    # TO BE DONE. 
    # [...]
    # group records by (element, id) and combine their geometries into a single MultiPolygo
    combined_geom_gdf = _combine_duplicate_osm_geometries(polygon_like_gdf)

    # 6. Inpect final geometries
    _inspect_geometries(combined_geom_gdf)

    logger.info("Geometry validation complete: %s/%s records retained.", len(polygon_like_gdf), len(gdf))

    return polygon_like_gdf


