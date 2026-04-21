

# %%
import geopandas as gpd
from geopandas import GeoDataFrame 
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
import osmnx as ox
from shapely.geometry import Polygon, box

from app.core import db
from app.core.db import SessionLocal

from app.services.match import match_osm_bag_buildings_with_postgis


def run_match_osm_bag(db: Session):

    num_matched_buildings = match_osm_bag_buildings_with_postgis(db=db)

    return {"number of matched buildings ALL ": num_matched_buildings}
