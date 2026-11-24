import logging 
import geopandas as gpd

logger = logging.getLogger(__name__) # module's name 

# move outside the BAG adapter
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
    mask = copied_gdf.geometry.geom_type.isin(allowed_types)

    # Count removed records
    removed_count = (~mask).sum()
    logger.info("Geometry types before filtering:\n%s", copied_gdf.geometry.geom_type.value_counts())
    if removed_count > 0: logger.info("Removing %s unsupported geometry types", removed_count)

    # Filter and create an independent copy
    filtered_gdf = copied_gdf.loc[mask].copy()

    logger.info("Records before filtering: %s", len(gdf))
    logger.info("Records after  filtering: %s", len(filtered_gdf))

    return filtered_gdf
