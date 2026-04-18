import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon


import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def fetch_osm_buildings_from_polygon(polygon: Polygon, tags: dict = {"building": True}):

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
    gdf = gdf.reset_index()

    # ENSURE CRS IS SET TO WGS84 (EPSG:4326):
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)

    return gdf

    