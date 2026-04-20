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
            geom,
            centroid
        )
        WITH 
        accepted_matches AS (
            SELECT
                m.osm_building_id,
                m.bag_building_id
            FROM building_matches m
        ),

        matched_rows AS (
            SELECT
                'bag' AS source_dataset,
                b.source_record_id AS source_record_id,
                'bag' AS geometry_source,
                b.geom AS geom,
                b.centroid AS centroid
            FROM accepted_matches am
            JOIN bag_buildings_canonical b
              ON b.id = am.bag_building_id
        ),

        unmatched_bag_rows AS (
            SELECT
                'bag' AS source_dataset,
                b.source_record_id AS source_record_id,
                'bag' AS geometry_source,
                b.geom AS geom,
                b.centroid AS centroid
            FROM bag_buildings_canonical b
            WHERE NOT EXISTS (
                SELECT 1
                FROM accepted_matches am
                WHERE am.bag_building_id = b.id
            )
        ),

        unmatched_osm_rows AS (
            SELECT
                'osm' AS source_dataset,
                o.source_record_id AS source_record_id,
                'osm' AS geometry_source,
                o.geom AS geom,
                o.centroid AS centroid
            FROM osm_buildings_canonical o
            WHERE NOT EXISTS (
                SELECT 1
                FROM accepted_matches am
                WHERE am.osm_building_id = o.id
            )
        )

        SELECT source_dataset, source_record_id, geometry_source, geom, centroid
        FROM matched_rows

        UNION ALL

        SELECT source_dataset, source_record_id, geometry_source, geom, centroid
        FROM unmatched_bag_rows

        UNION ALL

        SELECT source_dataset, source_record_id, geometry_source, geom, centroid
        FROM unmatched_osm_rows

        -- ON CONFLICT (source_dataset, source_record_id) DO NOTHING  ## I should have a constraint for this to work
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