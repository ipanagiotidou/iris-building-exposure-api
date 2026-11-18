# URL opening 
from urllib.parse import urlencode
import requests

# # CACHING
# import requests_cache  

import geopandas as gpd

from app.core.config import settings
from app.schemas.bbox import BBox
from app.sources.base import BaseBuildingAdapter


# LOGGING - ability to control the verbosity 
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)



bbox = BBox(west=4.32, south=23.0, east=34.5, north=45)
print(bbox)
print(bbox.bbox)



class BAGBuildingAdapter(BaseBuildingAdapter):
    pass



def fetch_bag_buildings_gdf(
        bbox: BBox,        #   bbox is mandatory because the AOI comes from the API request.
        limit: int = 100,  # limit and timeout are technical parameters, not necessarily things the end user needs to control.
        timeout: int = 30,   
        ) -> gpd.geodataframe:

    """
    Fetch all BAG pand features for a bbox from the PDOK/Kadaster OGC API
    by following pagination links, and return them as a GeoDataFrame.

    The first URL request should be:
    https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?f=json&bbox=4.355,52.000,4.380,52.020&limit=100


    Parameters
    ----------
    bbox : str
        "minx,miny,maxx,maxy" in EPSG:4326
    limit : int
        Page size requested from the API
    timeout : int
        Request timeout in seconds

    Returns
    -------
    geopandas.GeoDataFrame
    """


    # output_path = f"{RAW_DATA_DIR}/{bbox.to_filename_path()}.tif"
    # saved_path = download_dem(session, url, output_path=output_path)

    all_features: list[dict] = []

    # this is how it should be given inside requests.get() method
    params = {
        "f": "json",
        "bbox": bbox.bbox,
        "limit": limit,        
    }

    # Initialize the first request URL 
    next_url = settings.pdok_bag_buildings_base_url
    next_params = params


    while next_url:
        response = requests.get(next_url, params=next_params, timeout=timeout)  # GET request from API 
        response.raise_for_status()                                             # check if any error occurred during the request. If so, it raises an HTTPError.

        print("response: ", response)


        data = response.json()
        print("data:", data)


    #     features = data.get("features", [])
    #     all_features.extend(features)

    #     # After the first request, follow the server-provided next link directly
    #     next_url = None
    #     next_params = None

    #     for link in data.get("links", []):
    #         if link.get("rel") == "next" and link.get("href"):
    #             next_url = link["href"]
    #             break
    
    # # if empty return an empty gdf
    # if not all_features:
    #     return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # # Create the GeoDataFrame 
    # # ENSURE CRS IS SET TO WGS84 (EPSG:4326):
    # gdf = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")

    # # VALIDITY CHECKS FOR GEOMETRIES:
    # logger.warning(f"Valid geometries before filtering: {gdf.geometry.is_valid.sum()}")
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


    # # reset index after filtering
    # gdf = gdf.reset_index(drop=True)


    return 1 # gdf
    



    