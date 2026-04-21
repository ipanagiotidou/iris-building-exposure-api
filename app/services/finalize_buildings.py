from sqlalchemy import text
from sqlalchemy.orm import Session


def populate_geometry_in_final_buildings_table(db: Session, rebuild: bool = False) -> int:
    """
    Populate the final canonical `buildings` table from:
    - matched BAG/OSM pairs -> keep BAG geometry
    - unmatched BAG buildings
    - unmatched OSM buildings

    Args:
    db: SQLAlchemy session
    rebuild: if True, truncate the table before inserting

    Returns the number of inserted rows.
    """

    sql = text("""
        INSERT INTO buildings (
            source_dataset,
            source_record_id,
            geometry_source,
            geom
        )
        WITH 
        accepted_matches AS (
            SELECT
                m.osm_db_id,
                m.bag_db_id
            FROM building_matches m
        ), -- simply take the matching ids
        -- bring over only those OSM ids that are not present in the matching table 
        unmatched_osm_records AS (
            SELECT
                'osm' AS source_dataset,
                o.source_record_id AS source_record_id,
                'osm' AS geometry_source,
                o.geom AS geom
            FROM osm_buildings_canonical o
            WHERE NOT EXISTS (
                SELECT 1
                FROM accepted_matches am
                WHERE am.osm_db_id = o.id
            )
        ),
        -- for now I just want to build the geometry so simply bring the geometry and ids , so all 1407 building records
        all_bag_records AS (
            SELECT
                'bag' AS source_dataset,
                b.source_record_id AS source_record_id,
                'bag' AS geometry_source,
                b.geom AS geom
            FROM bag_buildings_canonical b
        )


        SELECT source_dataset, source_record_id, geometry_source, geom
        FROM unmatched_osm_records

        UNION ALL

        SELECT source_dataset, source_record_id, geometry_source, geom
        FROM all_bag_records

    """)

    try:
        if rebuild:
            db.execute(text("TRUNCATE TABLE buildings RESTART IDENTITY"))

        result = db.execute(sql)
        db.commit()

        return result.rowcount if result.rowcount is not None else 0

    except Exception:
        db.rollback()
        raise



def populate_attributes_in_final_buildings_table(db: Session, rebuild: bool = False) -> int:
    """
    Populate the final canonical `buildings` table from:
    - matched BAG/OSM pairs -> keep BAG geometry
    - unmatched BAG buildings
    - unmatched OSM buildings

    Args:
    db: SQLAlchemy session
    rebuild: if True, truncate the table before inserting

    Returns the number of inserted rows.
    """

    sql = text("""
        INSERT INTO buildings (
            source_dataset,
            source_record_id,
            geometry_source,
            geom
        )
        WITH 
        accepted_matches AS (
            SELECT
                m.osm_db_id,
                m.bag_db_id
            FROM building_matches m
        ), -- simply take the matching ids
        -- bring over only those OSM ids that are not present in the matching table 
        unmatched_osm_records AS (
            SELECT
                'osm' AS source_dataset,
                o.source_record_id AS source_record_id,
                'osm' AS geometry_source,
                o.geom AS geom
            FROM osm_buildings_canonical o
            WHERE NOT EXISTS (
                SELECT 1
                FROM accepted_matches am
                WHERE am.osm_db_id = o.id
            )
        ),
        -- for now I just want to build the geometry so simply bring the geometry and ids , so all 1407 building records
        all_bag_records AS (
            SELECT
                'bag' AS source_dataset,
                b.source_record_id AS source_record_id,
                'bag' AS geometry_source,
                b.geom AS geom
            FROM bag_buildings_canonical b
        )


        SELECT source_dataset, source_record_id, geometry_source, geom
        FROM unmatched_osm_records

        UNION ALL

        SELECT source_dataset, source_record_id, geometry_source, geom
        FROM all_bag_records

    """)

    try:
        if rebuild:
            db.execute(text("TRUNCATE TABLE buildings RESTART IDENTITY"))

        result = db.execute(sql)
        db.commit()

        return result.rowcount if result.rowcount is not None else 0

    except Exception:
        db.rollback()
        raise