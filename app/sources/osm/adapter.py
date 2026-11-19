import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon

import logging 
logger = logging.getLogger(__name__) # module's name 

from app.sources.base import BaseBuildingAdapter
from app.schemas.bounding_box import BoundingBox


class OSMBuildingAdapter(BaseBuildingAdapter):

    def fetch_buildings(self, bbox: BoundingBox, tags: dict = {"building": True}) -> gpd.GeoDataFrame:

        """
        The function: Fetches OSM features tagged as buildings within a polygon & returns polygon / multipolygon features as a GeoDataFrame. 
        
        Responsibilities:
        -  Receives BBOX that turns into valid polygon 
        -  Fetches OSM features tagged as buildings within a polygon using osmnx.
        -  Performs validity checks & filters invalid geometries while logging.
        -  Keeps only polygon-like building geometries (Polygon and MultiPolygon).
        -  Flattens the multi-index to normal columns, so that fields like element, id, or osmid appear as normal columns.
        -  Ensures CRS is set to 4326. 


        ABOUT OSM:
        - API: It uses OVERPASS API 
        - 3 TYPES of OSM ELEMENTS: RELATIONS, WAYS, and NODES: https://wiki.openstreetmap.org/wiki/Elements
            --> NODES = DEFINES POINTS
            --> WAYS = DEFINES LINEAR FEATURES (e.g. roads, rivers) + AREA BOUNDARIES (e.g. solid polygons like buildings or forests)
            --> RELATIONS = DEFINES HOW OTHER ELEMENTS WORK TOGETHER
                    --> RELATION DOES NOT MEAN MULTI-POLYGON. IT CAN BE MANY THINGS. 
                    --> The relation's meaning is defined by its tags. A relation must have at least the type tag. 
                    --> example: A multipolygon that describes an area (whose boundary is the 'outer WAY') with holes (the 'inner WAYS').

            ACTION REGARDING RELATIONS: 
            --> ??? Turn 'relations' into 'MultiPolygons', and  'ways' into 'Polygons' when ingesting into PostGIS. 
            --> There is a column "type" = 'multipolygon' for all 'relation' elements (QGIS). 
            --> But the geometries of the 'relation' elements are still Polygons, not MultiPolygons.
            check the differeces of: 
            - osm_buildings.geometry.geom_type.value_counts()
            - osm_buildings.type.value_counts()

        - TAGS: 
            Notes on tags:
                All types of data elements (nodes, ways and relations) can have tags. Tags describe the meaning. 
                Tags are key-value pairs that specify the type of features we want to retrieve from OSM. 
                For now we do not include tags with "building:part", for simplicity of the pipeline. 
                Building parts exist to indicate different components of a building, usually with different heights, roof shapes, or other attributes.
            TRADE-OFF: Keep "building", but not "building:part".

            
        - IMPORTANT FOR ID ATTRIBUTE:
            - 'ID' is used for identifying THE ELEMENT. 
                --> Element types have their own ID space, so there could be a NODE with id=100 and a WAY with id=100, which are unlikely to be related or geographically near to each other.

        """

        # turn the given bbox into a polygon to feed the osm api
        bbox_tuple = bbox.as_ogc_bbox_tuple
        bbox_polygon = box(*bbox_tuple)
        
        # Request OSM features with tags = {'building': True}. It returns a gdf. 
        gdf = ox.features.features_from_polygon(bbox_polygon, tags=tags)

        # OSM uses multi-index indices. The 'element' + 'id' column. This probably means that this double index is what characterizes uniquely the building. 


        # # VALIDITY CHECKS FOR GEOMETRIES:
        # logger.warning(f"Valid geometries: {gdf.geometry.is_valid.sum()}")
        # # is_valid returns a Boolean list with True and False values. Sum only takes into account the True values. 
        # logger.warning(f"Invalid geometries before filtering: {gdf.geometry.is_valid.count() - gdf.geometry.is_valid.sum()}")
        
        # # TO DO...
        # # FILTER OUT INVALID GEOMETRIES:
        # # In this case, there are no invalid geometries, so this step is not necessary, but in general it is a good practice to filter out invalid geometries before ingesting into the database, to avoid issues with spatial queries and analyses later on. 
        # gdf = gdf[gdf.geometry.is_valid].copy()


        # # KEEP ONLY POLYGON-LIKE BUILDING GEOMETRIES:
        # # check the number of records and geometry types before and after filtering:
        # logger.warning(f"Number of records before filtering: {len(gdf)}")
        # logger.warning(f"Geometry types before filtering:\n{gdf.geometry.geom_type.value_counts(dropna=False)}")

        # # Keep only polygon-like building geometries
        # gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

        # logger.warning(f"Number of records after filtering: {len(gdf)}")
        # logger.warning(f"Geometry types after filtering:\n{gdf.geometry.geom_type.value_counts(dropna=False)}")

        # # FLATTEN THE MULTI-INDEX TO NORMAL COLUMNS:
        # # Now fields like element, id, or osmid may appear as normal columns.
        # # .reset_index() function:
        # # The reset_index() method allows you reset the index back to the default 0, 1, 2 etc indexes. 
        # # By default this method will keep the "old" idexes in a column named "index", 
        # # to avoid this, use the drop parameter.
        # gdf = gdf.reset_index()

        # # ENSURE CRS IS SET TO WGS84 (EPSG:4326):
        # if gdf.crs is None:
        #     gdf = gdf.set_crs(4326)

        # # Lastly exclude some features to make the AOI more challenging 
        # gdf = filter_buildings_out(gdf).copy()


        # # reset index after filtering
        # gdf = gdf.reset_index(drop=True)


        return gdf

    