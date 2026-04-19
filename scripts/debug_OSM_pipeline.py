
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


from app.services.osm_fetch import fetch_osm_buildings_from_polygon
from app.services.normalize import prepare_raw_osm_buildings_gdf, normalize_osm_gdf_to_canonical
from app.services.ingest import ingest_raw_osm_buildings, ingest_canonical_buildings


####### DEBUGGING THE OSM PIPELINE #######

###### SECTION 1: Debug the Fetching OSM data function and inspect the gdf. ######

# %%
polygon = box(4.357, 52.006, 4.367, 52.012)
polygon

# %%
type(polygon)

# %%
# The function already:
# -  Keeps only polygon-like building geometries
# -  Flattens multi-index to normal columns
# -  Ensures CRS is set to 4326
# -  Checks for valid geometries and filters out invalid ones before ingesting into the database. 
osm_gdf_buildings = fetch_osm_buildings_from_polygon(polygon)

# %%
# check: should be a gdf
type(osm_gdf_buildings)

# %%
# check: range of index values, which should be a simple range from 0 to len(osm_gdf_buildings)-1 after resetting the index.
osm_gdf_buildings.index

# %%
# check: the fetching function checks that it is 4326 and not None
osm_gdf_buildings.crs

# %%
# Inspecting the fetched OSM data:
# - Check the number of records
# - Check the columns and their types
# - Check the geometry type and CRS  

osm_gdf_buildings.shape

# %%
len(osm_gdf_buildings)

# %%
# Doesn’t include counts of NaN.
osm_gdf_buildings.geometry.geom_type.value_counts()

# %%
# Includes NaN values, which means that some records do not have a 'type' field.
osm_gdf_buildings.geometry.geom_type.unique()


# %%
osm_gdf_buildings.head()

# %%
# see the columns as rows and the first 3 records as columns, to get a better overview of the data and its structure.
osm_gdf_buildings.head(3).T


# %%
# first record 
osm_gdf_buildings.iloc[0]

# %%
# first geometry 
osm_gdf_buildings.geometry.iloc[0]


###### Section 1.1: Inspect the columns of the OSM gdf and check what is useful for the DB ######

# %%
# element and id columms should be present, and not as multi-index anymore.
osm_gdf_buildings.columns.tolist()


# %%
# Any column with "building" in its name
[c for c in osm_gdf_buildings.columns if "building" in c.lower()]

# %%
# Any column with "roof" in its name
[c for c in osm_gdf_buildings.columns if "roof" in c.lower()]

# %%
# Any column with "height" in its name
[c for c in osm_gdf_buildings.columns if "height" in c.lower()]

# %%
# Make sure that these columns are present. True if present, False if not.
for col in ["building", "building:levels", "height", "roof:shape"]:
    print(col, col in osm_gdf_buildings.columns)


###### Section 1.1.1:  INSPECT THE VALUES OF SPECIFIC COLUMNS (INCLUDING NaNs):  ######

# %%
for col in ['id', 'type', 'location','level','roof:height','roof:orientation',"building", "building:use", 'building:levels', 'building:levels:underground', 'building:min_level', 'min_level', 'building:material','height', "roof:shape", "roof:material"]:
    if col in osm_gdf_buildings.columns:
        print("\n", col)
        print(osm_gdf_buildings[col].value_counts(dropna=False).head(20))


###### Section 1.2: Invalid geometries are already filtered out. ######

#%%
# Invalid geometries are already filtered out when fetched.
# Check here that all unique values are True: If invalid geometries there should be False values in the unique values. 
osm_gdf_buildings.geometry.is_valid.unique()


###### Section 1.3:  Visualize the OSM building footprints or save an HTML file locally (same folder as the script) for broswer visualization ######

# Visualize 
# %%
osm_gdf_buildings.plot(figsize=(8, 8))

# HTML visualization
# %%
# the basemap underneath is OSM raster tiles, which is a nice way to check that the building footprints are in the right place
m = osm_gdf_buildings.explore(tiles="OpenStreetMap", 
                          color="blue",
                          style_kwds={"fillOpacity": 0.2}, 
                          tooltip=["building", "building:levels", "height"])
m.save("osm_buildings.html")



###### Section 1.4:  Save the OSM building footprints locally in a supported format ######

# %%
# Save locally in GEOJSON format.
osm_gdf_buildings.to_file("output_buildings.geojson", driver="GeoJSON")




###### SECTION 2:Debug the raw-prep function separately ######
# ...







###### SECTION 3: Ingest OSM Data in the Database ######

###### SECTION 3.1: Ingest the raw OSM data into the OSMBuildingRaw table, and check that it is correctly inserted. ######
# osm_gdf_buildings IS the gdf that I fetched in section 1.

# %%
prepared_raw_osm_gdf_buildings = prepare_raw_osm_buildings_gdf(osm_gdf_buildings)

# %%
prepared_raw_osm_gdf_buildings.shape

# %%
prepared_raw_osm_gdf_buildings.head().T

# %%
# check the geometry
geom = prepared_raw_osm_gdf_buildings.iloc[0].geometry
print(type(geom))         # Python type


# %%
# # Insert the prepared raw OSM gdf into the OSMBuildingRaw table in the database, and check that it is correctly inserted.
db = SessionLocal()

raw_ingested_count = ingest_raw_osm_buildings(prepared_raw_osm_gdf_buildings, db)
print(f"Inserted raw rows: {raw_ingested_count}")

db.close()




###### SECTION 3.2: Ingest the canonical OSM data into the Building table, and check that it is correctly inserted. ######


# %%
canonical_osm_gdf_buildings = normalize_osm_gdf_to_canonical(osm_gdf_buildings)

# %%
canonical_osm_gdf_buildings.shape

# %%
canonical_osm_gdf_buildings.head().T

# %%
db = SessionLocal()

canonical_count = ingest_canonical_buildings(canonical_osm_gdf_buildings, db)
print(f"Inserted canonical rows: {canonical_count}")

db.close()


# %%
