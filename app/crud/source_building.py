from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert 
from sqlalchemy.orm import Session

from app.models.source_building import BuildingSourceRecord

# SQL operations
# NOTE: Its responsibility is to INTERACT with your SOURCE building TABLES. 
# NOTE: This module achieves Database persistence.
# NOTE: The database layer shouldn't need to know how OSM or BAG data was fetched.
# Validate columns, prepare records, insert batches
# UPSERT: update or insert 

# I would avoid immediately writing an insertion function based on assumptions about your columns.
# In particular, GeoDataFrames introduce a few things we need to handle correctly:
# - Geometry conversion to PostGIS.
# - CRS consistency (likely EPSG:4326 or your chosen database CRS).
# - Null values and pandas/NumPy types.
# - Source-specific identifiers.
# - Batch insertion for performance.
# - Duplicate prevention when fetching the same area repeatedly. Implement upserts using source identifiers

# create_source_buildings()
# get_source_buildings()
# get_source_building_by_id()
# upsert_source_buildings()
# delete_source_buildings()


# The CRUD function doesn't commit the transaction itself. The service will manage the transaction.
# This is the database operation. It doesn't know anything about GeoDataFrames yet.
def upsert_source_buildings(
        db: Session,
        records: list[dict],
) -> int: 

    if not records:
        return 0

    # statement 
    stmt = insert(BuildingSourceRecord).values(records)

    # https://docs.sqlalchemy.org/en/21/dialects/postgresql.html#sqlalchemy.dialects.postgresql.Insert.on_conflict_do_update
    # NOTE: The unique constraint defined prevents duplicate source records.
    # NOTE: Existing records get updated when the same source identifier is encountered again.
    # NOTE: building_id is not modified during ingestion, so MATCHING ASSOCIATIONS AREN'T accidentally LOST.
    stmt = stmt.on_conflict_do_update(
        constraint = "uq_building_source_record",
        set_ = {
            "source_attributes": stmt.excluded.source_attributes,
            "source_geom" : stmt.excluded.source_geom, 
        }
    )

    result = db.execute(stmt)

    return len(records) 

