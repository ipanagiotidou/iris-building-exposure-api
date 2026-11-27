from sqlalchemy.dialects.postgresql import insert 
from sqlalchemy.orm import Session

from app.models.source_building import BuildingSourceRecord

# Handles database operations, such as:
# - Insert source records.
# - Retrieve source records.
# - Check whether a source record already exists.
# - Update existing source records.
# - Delete source records.

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


# The CRUD function DOES NOT COMMIT THE TRANSACTION itself. The SERVICE will manage the transaction.
# This is the database operation. It doesn't know anything about GeoDataFrames yet.
# The CRUD module should not be responsible for GeoDataFrame processing. The CRUD layer should receive records already prepared for database insertion.
# Upsert function 

# IMPROVEMET: EACH BATCH SHOULD NOT CONTAIN DUBLICATES. CAUSE THE UPDATE DOESNT CHECK... 
# One important constraint: make sure each batch contains unique (source_dataset, source_record_id) pairs.
# PostgreSQL cannot update the same conflicting row twice in one INSERT ... ON CONFLICT DO UPDATE statement.
# The CRUD function should receive unique source identifiers.

def upsert_source_buildings(
        db: Session,
        records: list[dict],
        batch_size: int = 1000,
) -> int: 

    """

    Insert new source-building records or update existing ones.
    Existing records are identified by the unique constraint: (source_dataset, source_record_id).
    The building_id association is deliberately preserved.
    The caller is responsible for committing or rolling back.

    Batching: avoids sending a very large insertion statement for an entire dataset.
    Upsert: prevents duplicate source records when you fetch the same geographical area repeatedly.
    Preserving building_id: EXISTING canonical ASSOCIATIONS aren't overwritten during source ingestion.
    No commit: the service controls the transaction.
    Return value: returns the number of submitted records, not a count of newly inserted records.

    NOTES:
    - the CRUD function expects source_geom to already be compatible with that column Geometry("MULTIPOLYGON", srid=4326). Geometry prep happens in the service/ingestion module.


    """

    if not records:
        return 0

    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    processed_count = 0

    for start in range(0, len(records), batch_size): 
        batch = records[start : start + batch_size]

        # The STATEMENT: 
        # 1. Attempts to insert each source record.
        # 2. Checks the unique constraint uq_building_source_record.
        # 3. If the record already exists, updates its attributes and geometry.
        # 4. Leaves building_id untouched.

        # statement 
        stmt = insert(BuildingSourceRecord).values(batch)

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

        db.execute(stmt)

        processed_count += len(batch) 

    return processed_count 

