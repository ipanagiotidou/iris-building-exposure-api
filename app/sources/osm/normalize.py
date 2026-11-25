import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon


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
    