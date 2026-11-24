
import logging 
logger = logging.getLogger(__name__) # module's name 

import geopandas as gpd

# move outside the BAG adapter
def _validate_geometries(gdf: gpd.GeoDataFrame) ->  gpd.GeoDataFrame:
    """
    Repair geometries and remove missing, empty and invalid geometries.
    """

    # Create an independent copy that I intend to modify later.  Original gdf remains unchanged.
    copied_gdf = gdf.copy()

    valid_top_before = copied_gdf.geometry.is_valid    # Geometry is TOPOLOGICALLY valid. Return a SERIES of dtype('bool') with value True for geometries that are valid.
    logger.info("Total geometries: %s", len(copied_gdf))
    logger.info("Valid geometries before repair: %s", valid_top_before.sum())

    # Repair Geometries 
    # NOTE: Can return MultiPolygon or GeometryCollection (Polygon, Linestring, ...).
    # NOTE: I filter by geometry types. The filter should come before this step.
    copied_gdf.geometry = copied_gdf.geometry.make_valid()

    valid_top_after = copied_gdf.geometry.is_valid  
    logger.info("Valid geometries after  repair: %s", valid_top_after.sum())

    # Check geometry conditions - All 3 must be true to be valid.
    # The functions return True/False.
    valid = (
        copied_gdf.geometry.notna()       #    Geometry actually exists (not-missing).
        & ~copied_gdf.geometry.is_empty   #    Geometry isn't empty  E.g. There can be a Polygon that is Empty... coming from the intersection of two polygons that do not overlap. No need to keep it. 
        & copied_gdf.geometry.is_valid    #    Geometry is topologically valid
    )

    # Count invalid records - sums all False records.
    invalid_count = (~valid).sum()

    if invalid_count > 0: logger.warning("Found %s missing, empty or invalid geometries", invalid_count)

    # Filter out Invalid geometries and Keep only the Valid ones.
    validated_gdf = copied_gdf.loc[valid].copy()

    return validated_gdf

        
