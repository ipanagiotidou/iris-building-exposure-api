import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon


import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)



OSM_EXCLUDE_IDS = [138389513, 138389515, 254135757, 254135855, 254135957, 254135995, 254136090, 
                        254136178, 254136230, 254136280, 254136332, 254136528, 254136575, 254136590, 
                        254136636, 254136720, 254137536, 254138506, 254138572, 254138678, 254138716, 
                        254138817, 254138883, 254138918, 254139115, 254139178, 254139234, 254139291, 
                        254139302, 254139320, 254139356, 254139358, 254139406, 254139407, 254139561, 
                        254139752, 254139858, 254139870, 254139887, 254140005, 254140130, 254140224, 
                        254140366, 1336638809, 1336638817, 1336638820, 1336638833, 1336638868, 1363852029, 
                        1363852118, 1363853298, 1410525649]


# this could happen after normalization  as well.
def filter_buildings_out(gdf_all_fetched: gpd.GeoDataFrame) -> gpd.GeoDataFrame: 

    gdf = gdf_all_fetched.copy()

    # ensure consistent type (dtype of 'id' column in int64)
    gdf["id"] = gdf["id"].astype(str)

    # ensure list is same type
    ids = [str(x) for x in OSM_EXCLUDE_IDS]

    # filter 
    gdf = gdf[~gdf["id"].isin(ids)].copy()

    return gdf


def fetch_osm_buildings_from_polygon(polygon: Polygon, tags: dict = {"building": True}) -> gpd.geodataframe:

    """
    Fetch OSM features tagged as buildings within a polygon.
    Returns polygon / multipolygon features only as a GeoDataFrame. 
    
    The function:
    -  Fetches OSM features tagged as buildings within a polygon using osmnx.
    -  Performs validity checks on the geometries and logs the number of valid and invalid geometries before filtering.
    -  Filters out invalid geometries to ensure that only valid geometries are ingested into the database, which helps to avoid issues with spatial queries and analyses later on.
    -  Keeps only polygon-like building geometries (Polygon and MultiPolygon) to ensure that the data is suitable for building footprint analysis and ingestion into PostGIS.
    -  Flattens the multi-index to normal columns, so that fields like element, id, or osmid appear as normal columns in the resulting GeoDataFrame.
    -  Ensures CRS is set to 4326


    TRADE-OFF:
    Notes on tags:
        Tags are key-value pairs that specify the type of features we want to retrieve from OSM. 
        For now we do not include tags with "building:part", for simplicity of the pipeline. 
        building parts exist to indicate different components of a building, usually with different heights, roof shapes, or other attributes.

    TO CHECK:
    OSM elements: relations, ways, and nodes:

    Notes on OSM elements:
        I have to turn the relations into MultiPolygons, and the ways into Polygons when ingesting into PostGIS. 
        There is a column "type" = 'multipolygon' for all 'relation' elements (QGIS). 
        But the geometries of the 'relation' elements are still Polygons, not MultiPolygons.
        check the differeces of: 
        - osm_buildings.geometry.geom_type.value_counts()
        - osm_buildings.type.value_counts()
    
    """

    tags = {"building": True}
    gdf = ox.features.features_from_polygon(polygon, tags=tags)

    # VALIDITY CHECKS FOR GEOMETRIES:
    logger.warning(f"Valid geometries before filtering: {gdf.geometry.is_valid.sum()}")
    # is_valid returns a Boolean list with True and False values. Sum only takes into account the True values. 
    logger.warning(f"Invalid geometries before filtering: {gdf.geometry.is_valid.count() - gdf.geometry.is_valid.sum()}")
    
    # TO DO...
    # FILTER OUT INVALID GEOMETRIES:
    # In this case, there are no invalid geometries, so this step is not necessary, but in general it is a good practice to filter out invalid geometries before ingesting into the database, to avoid issues with spatial queries and analyses later on. 
    gdf = gdf[gdf.geometry.is_valid].copy()


    # KEEP ONLY POLYGON-LIKE BUILDING GEOMETRIES:
    # check the number of records and geometry types before and after filtering:
    logger.warning(f"Number of records before filtering: {len(gdf)}")
    logger.warning(f"Geometry types before filtering:\n{gdf.geometry.geom_type.value_counts(dropna=False)}")

    # Keep only polygon-like building geometries
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

    logger.warning(f"Number of records after filtering: {len(gdf)}")
    logger.warning(f"Geometry types after filtering:\n{gdf.geometry.geom_type.value_counts(dropna=False)}")

    # FLATTEN THE MULTI-INDEX TO NORMAL COLUMNS:
    # Now fields like element, id, or osmid may appear as normal columns.
    # .reset_index() function:
    # The reset_index() method allows you reset the index back to the default 0, 1, 2 etc indexes. 
    # By default this method will keep the "old" idexes in a column named "index", 
    # to avoid this, use the drop parameter.
    gdf = gdf.reset_index()

    # ENSURE CRS IS SET TO WGS84 (EPSG:4326):
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)

    # Lastly exclude some features to make the AOI more challenging 
    gdf = filter_buildings_out(gdf).copy()


    # reset index after filtering
    gdf = gdf.reset_index(drop=True)


    return gdf

    