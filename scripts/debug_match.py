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

from app.services.match import compute_osm_bag_match_candidates


# %%
db = SessionLocal()
result = compute_osm_bag_match_candidates(db=db)
db.close()

# %%
type(result)
# %%
for r in result: 
    print(r)
# %%
