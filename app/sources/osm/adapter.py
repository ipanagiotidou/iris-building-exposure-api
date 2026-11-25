import logging 

import osmnx as ox
import geopandas as gpd
from shapely.geometry import box

from app.sources.base import BaseBuildingAdapter
from app.schemas.bounding_box import BoundingBox
from app.modules.geometry.validation import _validate_geometries

logger = logging.getLogger(__name__) # module's name 


class OSMBuildingAdapter(BaseBuildingAdapter):


    def fetch_buildings(
            self, 
            bbox: BoundingBox, 
            tags: dict | None = None,
    ) -> gpd.GeoDataFrame:

        """
        Fetches OSM features tagged as buildings within a polygon (bbox) & returns a GeoDataFrame. 
        
        Responsibilities/Steps:
        -  Receives bbox that turns into valid polygon. 
        -  Fetches OSM features tagged as buildings within the aforementioned polygon using osmnx.
        -  Ensures CRS is set to 4326. 
        -  Flattens the MultiIndex to normal columns (without dropping the previous index).
        -  Filters unsupported geometry types. (keeps only - Polygon and MultiPolygon)
        -  Performs validity checks & filters invalid geometries while logging.
        -  Reset the index (back to 0,1,2) dropping the previous one for e.g. (0,4,9)

        
        Args:
            bbox: Bounding box defining the area of interest.
            tags: OSM tags used to filter features. Defaults to 
                {"building": True}.

        Returns:
            GeoDataFrame containing valid building geometries
            in EPSG:4326.

            
        # --------------------------------------------------
        # ABOUT OSM
        # -------------------------------------------------- 
        
        ABOUT OSM:
        - API: It uses OVERPASS API 
        - 3 TYPES of OSM ELEMENTS: RELATIONS, WAYS, and NODES: https://wiki.openstreetmap.org/wiki/Elements
            --> NODES = DEFINES POINTS
            --> WAYS = DEFINES LINEAR FEATURES (e.g. roads, rivers) + AREA BOUNDARIES (e.g. solid polygons like buildings or forests)
            --> RELATIONS = DEFINES HOW OTHER ELEMENTS WORK TOGETHER
                    --> RELATION DOES NOT MEAN MULTI-POLYGON. IT CAN BE MANY THINGS. 
                    --> The relation's meaning is defined by its tags. A relation must have at least the type tag. 
                    --> example: A multipolygon that describes an area (whose boundary is the 'outer WAY') with holes (the 'inner WAYS').


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

        # --------------------------------------------------
        # 1. REQUEST FEATURES FROM OSM API.
        # --------------------------------------------------
            
        if tags is None: 
            tags = {"building": True}

        # Turn the given bbox into a polygon to feed the OSM API
        bbox_tuple = bbox.as_ogc_bbox_tuple
        bbox_polygon = box(*bbox_tuple)
        
        # Request OSM features with tags = {'building': True}. Returns a gdf. 
        original_gdf = ox.features.features_from_polygon(
            bbox_polygon, 
            tags=tags,
        )   

        # Usefull if I want to preserve the original OSM data.
        gdf = original_gdf.copy()

        # --------------------------------------------------
        # 2. STANDARDIZE DATA
        # --------------------------------------------------

        # Ensure the CRS is "EPSG:4326"
        gdf = gdf.to_crs("EPSG:4326")

        # Flatten the Multi-Index & preserve element and id as ordinary columns (element, id). 
        gdf = gdf.reset_index()       # It flattens the Multi-Index WITHOUT dropping the old.


        # --------------------------------------------------
        # 3. GEOMETRY PROCESSING
        # --------------------------------------------------

        gdf = _validate_geometries(gdf)       

        # --------------------------------------------------
        # 4. FINAL PREPARATION
        # --------------------------------------------------

        # Reset index after filtering 
        # NOTE: Keep the reset_index(drop=True) in this function here. Resetting the index isn't really geometry filtering or geometry validation. It's a final preparation step.
        gdf = gdf.reset_index(drop=True)       # back to the default 0, 1, 2 & drop the old indices 

        # --------------------------------------------------
        # 5. LOGGING
        # --------------------------------------------------

        logger.info(
            "OSM retrieval completed: %s buildings returned",
            len(gdf),
        )

        logger.debug("GeoDataFrame preview - First row :\n%s", gdf.head(1))

        return gdf







    