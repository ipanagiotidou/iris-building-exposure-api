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

from app.modules.geometry.validation import _validate_geometries, _filter_geometry_types



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

        # 1. turn the given bbox into a polygon to feed the OSM API
        bbox_tuple = bbox.as_ogc_bbox_tuple
        bbox_polygon = box(*bbox_tuple)
        
        # 2. Request OSM features with tags = {'building': True}. Returns a gdf. 
        gdf = ox.features.features_from_polygon(bbox_polygon, tags=tags)   # gdf comes with MultiIndex (element, id) 

        # 3. Ensure the CRS is "EPSG:4326"
        gdf = gdf.to_crs(4326)

        # 4. Flatten the Multi-Index & preserve element and id as ordinary columns (element, id)
        gdf = gdf.reset_index()       # It flattens the Multi-Index WITHOUT dropping the old.

        # 5. Validate Geometries 
        gdf = _validate_geometries(gdf)        # returns a copy() version

        # 6. Keep building footprint geometry types 
        gdf = _filter_geometry_types(gdf)     # returns a copy() version

        # 7. Prepare final result - Reset index after filtering 
        gdf = gdf.reset_index(drop=True)       # back to the default 0, 1, 2 & drop the old indices 
 

        logger.info(
            "OSM retrieval completed: %s buildings returned",
            len(gdf),
        )

        logger.debug("GeoDataFrame preview:\n%s", gdf.head())

        return gdf







    