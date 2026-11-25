
# INGESTION SERVICE RESPONSIBILITIES:
# - The ingestion service prepares database-ready records.

# The INGESTION SERVICE IS: Responsible for data preparation & Responsible for transaction management
# - Receives the GeoDataFrame.
# - Validates geometries.
# - Standardizes Polygon/MultiPolygon and CRS.
# - Converts geometries to GeoAlchemy-compatible values.
# - Converts rows into dictionaries.
# - Commits on success.
# - Rolls back on failure.

# GEOMETRY PREPARATION: 
# geometry preparation happens before CRUD
# Your model declares:
# Geometry("MULTIPOLYGON", srid=4326)
# Therefore, the CRUD function expects source_geom to already be compatible with that column.
# For example, your ingestion service should handle geometry conversion using GeoAlchemy2:


from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon

def 