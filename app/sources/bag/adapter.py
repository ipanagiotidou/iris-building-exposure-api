# URL opening 
import requests

# # CACHING
# import requests_cache  

import geopandas as gpd

from app.core.config import settings
from app.schemas.bounding_box import BoundingBox
from app.sources.base import BaseBuildingAdapter

from app.modules.geometry.validation import _validate_geometries
from app.modules.geometry.filtering import _filter_geometry_types


# LOGGING 
import logging
logger = logging.getLogger(__name__) # module's name 


class BAGBuildingAdapter(BaseBuildingAdapter):
    """
    seperation of concerns when writing this function. 

    Function's RESPONSIBILITIES:
    1) constructs the URL and sends a request
    2) retrieves data from BAG 
    3) constructs the next_url if any to handle PAGINATION 
    3)  gathers all features
    4) checks if the features are empty or full
    5) filters out invalid geometries and keeps only polygon-like geometries 
    6) 

    """


    # If I move this, remember it turns a list[dict] into GeoDataFrame
    def _to_gdf(self, features: list[dict], crs: str) -> gpd.GeoDataFrame:    
        """Raw GeoJSON features → spatial data    """
        gdf = gpd.GeoDataFrame.from_features(features, crs= crs)
        return gdf 

    def _find_next_url_page(self, data: dict) -> str | None:
        """
        Responsibility: 
        Find next page URL or return None if there isn't one. 
        """

        # OGC APIs use links to support navigation between resources. Each link describes a relationship to another resource.
        # 'rel' Relationship of the link to the current resource
        #       - 'self' means: this is the URL of the resource you are currently looking at.
        #       - 'alternate' means PDOK offers the same resource in another representation.
        # The href specifies the link's destination. HyperLink = Actual URL of the resource. 
        # If I find a relationship being 'next' and there is a hyperlink value, then break the loop --> this is the next url 
        
        for link in data.get("links", []):  # "links" is the key, the method returns [] instead of None if there is no value 
            if link.get("rel") == "next" and link.get("href"):
                next_url = link["href"]
                return next_url
        
        return None 

        


    def _fetch_features(
            self, 
            url: str, 
            params: dict, 
            timeout: int = 30,
    ) -> list[dict]:
        """
        Retrieve all the raw features from the BAG API, following pagination until there are no more pages.
        """


        all_features = []                 # Define an empty list to save the features from multiple pages 
        
        next_url = url
        next_params = params
        page = 1

        while next_url:    # break if I want to break the loop
            logger.debug("Requesting BAG page %s", page)

            response = requests.get(next_url, params=next_params, timeout = timeout)  # GET request from API 
            response.raise_for_status()                            # check if response [200] or if any error occurred and raise an HTTPError.

            data = response.json() # data is a dict that contains a FeatureCollection

            logger.debug("Response type: %s", type(data))  # data is a dict 
            logger.debug("Response keys: %s", data.keys()) # dict_keys(['type', 'timeStamp', 'links', 'features', 'numberReturned'])  

            features = data.get("features", [])   # returns [] instead of None as a Value if the Key doesn't exist in Dictionary.
            
            logger.info("Features received: %s", len(features))

            # Add the features in the Features List. The extend() method adds the specified list elements to the end of the current list.
            all_features.extend(features)  

            logger.info("BAG page %s: received %s features", page, len(features))

            
            # Paginate
            next_url = self._find_next_url_page(data)     # Next request following the server-provided next link directly. 
            next_params = None                            # The next link already contains its query parameters, thus next_params = None. 
            page += 1
                          

        return all_features 
    
    
    def fetch_buildings(
            self, 
            bbox: BoundingBox,        # bbox is mandatory because the AOI comes from the API request.
            ) -> gpd.GeoDataFrame:

        """
        MAIN PUBLIC METHOD. 

        Retrieve building footprints from the BAG API for a given area of interest and return them as a validated GeoDataFrame.

        PDOK provides the BAG through an OGC API – Features.

        OGC API is a REST-based API standard that allows applications to retrieve geographic objects (features), including:
            - Geometry (building footprints, points, polygons).
            - Attributes (building identifiers, construction year, status, etc.).
            - Spatial filtering (e.g. bounding boxes).
            - Pagination (retrieving results in multiple pages).

        Fetch all BAG pand features for a bbox from the PDOK/Kadaster OGC API
        by following pagination links, and return them as a GeoDataFrame.

        The first URL request should be:
        https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?f=json&bbox=4.355,52.000,4.380,52.020&limit=100

        In the link you can see: ogc/v2	OGC API version


        Parameters
        ----------
        bbox : str
            OGC STANDARDS: "minx,miny,maxx,maxy" in EPSG:4326
        limit : int
            PAGE SIZE requested from the API
        timeout : int
            Request timeout in seconds

        Returns
        -------
        geopandas.GeoDataFrame
        """

        logger.info("Starting BAG data retrieval")


        # 1. Prepare request parameters 
        params = {
            "bbox": bbox.as_ogc_bbox,
            "f": "json",       
        }   # params for the URL construction


        url = settings.pdok_bag_buildings_base_url   

  
        # 2. Retrieve all raw features 
        features = self._fetch_features(url = url, params = params, timeout=30)

        # 3. Handle empty response & Return an empty GeoDataFrame 
        if not features:
            logger.info("No BAG features found for this Bounding Box.")

            return gpd.GeoDataFrame(
                geometry=gpd.GeoSeries([], crs= "EPSG:4326"),
                crs="EPSG:4326",
            )

        # 4. Convert to GeoDataFrame. Make sure the CRS is "EPSG:4326"
        gdf = self._to_gdf(features, crs= "EPSG:4326")

        # 5. Validate Geometries 
        gdf = _validate_geometries(gdf)           # returns a copy() version

        # 6. Keep building footprint geometry types 
        gdf = _filter_geometry_types(gdf)         # returns a copy() version


        # 7. Prepare final result - Reset index after filtering
        gdf = gdf.reset_index(drop=True)


        logger.info(
            "BAG retrieval completed: %s buildings returned",
            len(gdf),
        )

        logger.debug("GeoDataFrame preview:\n%s", gdf.head())

        return gdf
        



