
from urllib.parse import urlencode
import requests

# import requests_cache  # caching

import geopandas as gpd

from app.core.config import settings
from app.schemas.bbox import BBox



BAG_EXCLUDE_IDS = ['0503100000004048', '0503100000005344', '0503100000012187', '0503100000017220', 
                        '0503100000017317', '0503100000017412', '0503100000017413', '0503100000017420', 
                        '0503100000026051', '0503100000026052', '0503100000026151', '0503100000026152', 
                        '0503100000026153', '0503100000026154', '0503100000026155', '0503100000026156', 
                        '0503100000026157', '0503100000026158', '0503100000026218', '0503100000026222', 
                        '0503100000026234', '0503100000025407', '0503100000025408', '0503100000033625', 
                        '0503100000032718', '0503100000032719', '0503100000040278', '0503100000040279', 
                        '0503100000040280', '0503100000040281', '0503100000026237']


# this could happen after normalization  as well.
def filter_buildings_out(gdf_all_fetched: gpd.GeoDataFrame) -> gpd.GeoDataFrame: 

    gdf = gdf_all_fetched.copy()

    # ensure consistent type (dtype of 'id' column in int64)
    gdf["identificatie"] = gdf["identificatie"].astype(str)

    # ensure list is same type
    ids = [str(x) for x in BAG_EXCLUDE_IDS]

    # filter 
    gdf = gdf[~gdf["identificatie"].isin(ids)].copy()

    return gdf



def fetch_bag_buildings_gdf(
        bbox: BBox = BBox(west= 4.357, south = 52.006, east=4.367, north=52.012),  # Delft - AOI 
        limit: int = 1000, 
        base_url = settings.pdok_bag_buildings_base_url, 
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
    base_url : str
        OGC API Features items endpoint
    timeout : int
        Request timeout in seconds

    Returns
    -------
    geopandas.GeoDataFrame
    """

  
    params = {
        "f": "json",
        "bbox": bbox.bbox,
        "limit": 100,        
    }

    # output_path = f"{RAW_DATA_DIR}/{bbox.to_filename_path()}.tif"
    # saved_path = download_dem(session, url, output_path=output_path)

    all_features: list[dict] = []
    next_url = base_url
    next_params = params

    while next_url:
        response = requests.get(next_url, params=next_params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        features = data.get("features", [])
        all_features.extend(features)

        # After the first request, follow the server-provided next link directly
        next_url = None
        next_params = None

        for link in data.get("links", []):
            if link.get("rel") == "next" and link.get("href"):
                next_url = link["href"]
                break

    if not all_features:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")

    # Lastly exclude some features to make the AOI more challenging 
    gdf = filter_buildings_out(gdf).copy()

    return gdf
    