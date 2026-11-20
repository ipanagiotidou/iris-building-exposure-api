
import logging 
logger = logging.getLogger(__name__) # module's name 

import geopandas as gpd

# move outside the BAG adapter
def _validate_geometries(gdf: gpd.GeoDataFrame) ->  gpd.GeoDataFrame:
    """
    Remove missing, empty and invalid geometries.
    """

    # Check geometry conditions - All 3 must be true 
    valid = (
        gdf.geometry.notna()       # 	Geometry actually exists
        & ~gdf.geometry.is_empty   #    Geometry isn't empty
        & gdf.geometry.is_valid    #    Geometry is topologically valid
    )

    # Count invalid records 
    invalid_count = (~valid).sum()

    logger.info("Total geometries: %s", len(gdf))
    logger.info("Valid geometries: %s", valid.sum())

    if invalid_count > 0:
        logger.warning(
            "Found %s missing, empty or invalid geometries",
            invalid_count,
        )

    # Keep only valid geometries 
    # Use copy cause we are creating a filtered GeoDataFrame. We intend to modify it further later. 
    validated_gdf = gdf.loc[valid].copy()

    return validated_gdf

        

# move outside the BAG adapter
def _filter_geometry_types(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Keep only Polygon and MultiPolygon geometries.
    """

    allowed_types = ["Polygon", "MultiPolygon"]

    # Identify allowed geometry types
    mask = gdf.geometry.geom_type.isin(allowed_types)

    # Count removed records
    removed_count = (~mask).sum()

    logger.info("Geometry types before filtering:\n%s",
                gdf.geometry.geom_type.value_counts())

    if removed_count > 0:
        logger.info("Removing %s unsupported geometry types", removed_count)

    # Filter GeoDataFrame
    filtered_gdf = gdf.loc[mask].copy()

    logger.info("Records remaining after filtering: %s", len(filtered_gdf))

    return filtered_gdf
