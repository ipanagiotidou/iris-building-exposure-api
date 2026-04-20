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

from app.models.building import BAGCanonicalBuilding

from app.schemas.bbox import BBox

from app.services.bag_fetch import fetch_bag_buildings_gdf

from app.services.normalize import prepare_raw_bag_buildings_gdf, normalize_bag_gdf_to_canonical
from app.services.ingest import ingest_raw_bag_buildings, ingest_canonical_buildings



####### DEBUGGING THE BAG PIPELINE #######

###### SECTION 1: Debug the Fetching BAG data function and inspect the gdf_fetched. ######


# %%
# Downloads Delft automatically 
gdf_fetched = fetch_bag_buildings_gdf(bbox= BBox(west= 4.357, south = 52.006, east=4.367, north=52.012))
type(gdf_fetched) # geodataframe 


# %%
# check: range of index values, which should be a simple range from 0 to len(osm_gdf_buildings)-1 after resetting the index.
# if it set correctly it should show the Range: RangeIndex(start=0, stop=1407, step=1)
gdf_fetched.index   

# %%
# check: the fetching function checks that it is 4326 and not None
gdf_fetched.crs

# %%
# Inspecting the fetched OSM data:
# - Check the number of records
# - Check the columns and their types
# - Check the geometry type and CRS  

gdf_fetched.shape

# %%
len(gdf_fetched)

# %%
gdf_fetched.head()

# %%
# see the columns as rows and the first 3 records as columns, to get a better overview of the data and its structure.
gdf_fetched.head(3).T

# %%
# Doesn’t include counts of NaN.
gdf_fetched.geometry.geom_type.value_counts()

# %%
# Includes NaN values, which means that some records do not have a 'type' field.
gdf_fetched.geometry.geom_type.unique()

# %%
# first record 
gdf_fetched.iloc[0]

# %%
# first geometry 
gdf_fetched.geometry.iloc[0]



###### Section 1.1: Inspect the columns of the OSM gdf and check what is useful for the DB ######


# %%
# element and id columms should be present, and not as multi-index anymore.
gdf_fetched.columns.tolist()

###### Section 1.1.1:  INSPECT THE VALUES OF SPECIFIC COLUMNS (INCLUDING NaNs):  ######

# %%
gdf_fetched["gebruiksdoel"].head(10)

# %%
# I see NaNs in PostGIS from this column. WHEN missing in BAG → NULL in Postgres NOT  "NaN"
# In pandas, string-like columns often still have:
#       - dtype object
#       - missing values as numpy.nan
# So the column is not “all strings”; it is “mixed Python objects, mostly strings plus NaN”.
gdf_fetched["gebruiksdoel"].dtype

# %%
# 259 missing values 
gdf_fetched["gebruiksdoel"].isna().sum()


# %%
for col in ['"verblijfsobject"', 'aantal_verblijfsobjecten', 'bouwjaar', 
            'gebruiksdoel', 'geconstateerd', 'identificatie', 'status']:
    if col in gdf_fetched.columns:
        print("\n", col)
        print(gdf_fetched[col].value_counts(dropna=False).head(20))



###### Section 1.2: Invalid geometries are already filtered out. ######

#%%
# Invalid geometries are already filtered out when fetched.
# Check here that all unique values are True: If invalid geometries there should be False values in the unique values. 
gdf_fetched.geometry.is_valid.unique()


###### Section 1.3:  Visualize the OSM building footprints or save an HTML file locally (same folder as the script) for broswer visualization ######


# %%
gdf_fetched.plot(figsize=(8, 8))


# HTML visualization
# %%
# the basemap underneath is OSM raster tiles, which is a nice way to check that the building footprints are in the right place
m = gdf_fetched.explore(tiles="OpenStreetMap", 
                          color="blue",
                          style_kwds={"fillOpacity": 0.2}, 
                          tooltip=['"verblijfsobject"', 'aantal_verblijfsobjecten', 'bouwjaar', 
                                   'gebruiksdoel', 'geconstateerd', 'identificatie', 'status'])
m.save("bag_buildings.html")



###### Section 1.4:  Save the BAG building footprints locally in a supported format ######


# %%
gdf_fetched.to_file('bag_buildings.geojson', driver='GeoJSON')
# %%






###### SECTION 2:Debug the raw-prep function separately ######
# ...







###### SECTION 3: Ingest BAG Data in the Database ######

###### SECTION 3.1: Ingest the raw BAG data into the BAGBuildingRaw table, and check that it is correctly inserted. ######


# %%
prepared_raw_bag_gdf_buildings = prepare_raw_bag_buildings_gdf(gdf_fetched)

# %%
# If the column dtype is: StringDtype(na_value=nan) 
# then pandas is still managing missing values for that column. 
prepared_raw_bag_gdf_buildings["gebruiksdoel"].dtype

# %%
# 259 missing values 
prepared_raw_bag_gdf_buildings["gebruiksdoel"].isna().sum()

# %%
prepared_raw_bag_gdf_buildings.shape

# %%
prepared_raw_bag_gdf_buildings.head(5)

# %%
prepared_raw_bag_gdf_buildings.head().T

# %%
# check the geometry
geom = prepared_raw_bag_gdf_buildings.iloc[0].geometry
print(type(geom))         # Python type


# %%
# # Insert the prepared raw BAG gdf into the OSMBuildingRaw table in the database, and check that it is correctly inserted.
db = SessionLocal()

raw_ingested_count = ingest_raw_bag_buildings(prepared_raw_bag_gdf_buildings, db)
print(f"Inserted raw rows: {raw_ingested_count}")

db.close()




###### SECTION 3.2: Ingest the canonical BAG data into the Building table, and check that it is correctly inserted. ######


# %%
canonical_bag_gdf_buildings = normalize_bag_gdf_to_canonical(gdf_fetched)

# %%
canonical_bag_gdf_buildings.shape

# %%
canonical_bag_gdf_buildings.head().T

# %%
db = SessionLocal()

canonical_count = ingest_canonical_buildings(canonical_bag_gdf_buildings, db, BAGCanonicalBuilding)
print(f"Inserted canonical rows: {canonical_count}")

db.close()


# %%
