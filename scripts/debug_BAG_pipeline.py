
# %%
# *** DO NOT FORGET TO RESTART THE KERNEL IF NEEDED - AFTER EDITING THE CODE, TO MAKE SURE THAT THE CHANGES ARE REFLECTED IN THE DEBUGGING PROCESS.
# with this code, I add the root of the project to the sys.path, so that I can import from the app package.
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("cwd:", os.getcwd())
print("sys.executable:", sys.executable)
print("sys.path[0:5]:", sys.path[:5])


# %%
import geopandas as gpd
from geopandas import GeoDataFrame 
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
import osmnx as ox
from shapely.geometry import Polygon, box

from app.core import db
from app.core.db import SessionLocal

from app.models.building import Building
from app.models.source_building import OSMBuildingRaw

from app.schemas.bbox import BBox


from app.services.osm_fetch import fetch_osm_buildings_from_polygon
from app.services.bag_fetch import fetch_bag_buildings_gdf

from app.services.normalize import prepare_raw_osm_buildings_gdf, normalize_osm_gdf_to_canonical
from app.services.ingest import ingest_raw_osm_buildings, ingest_canonical_buildings



# %%
gdf = fetch_bag_buildings_gdf(bbox= BBox(west= 4.357, south = 52.006, east=4.367, north=52.012))
type(gdf) # dict 

# %%
len(gdf)

# %%
gdf.head()

# %%
for col in ['identificatie']:
    if col in gdf.columns:
        print("\n", col)
        print(gdf[col].value_counts(dropna=False).head(20))



# %%
gdf.plot(figsize=(8, 8))


# %%
gdf.to_file('bag_buildings.geojson', driver='GeoJSON')
# %%
