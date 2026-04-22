from sqlalchemy import text
from sqlalchemy.orm import Session


def populate_final_geometry(db: Session) -> int:
    """
    Populate the final canonical `buildings` table from:
    - matched BAG/OSM pairs -> keep BAG geometry
    - unmatched OSM buildings

    Args:
    db: SQLAlchemy session
    rebuild: if True, truncate the table before inserting

    Returns the number of inserted rows.
    """

    sql = text("""
        TRUNCATE table buildings;

        INSERT INTO buildings (
            source_dataset,
            source_record_id,
            geometry_source,
            match_id,
            geom
        )

        WITH all_accepted_matches AS (
            SELECT
                m.osm_db_id,
                m.bag_db_id
            FROM building_matches m
        ),

        best_matches AS (
            SELECT
                m.osm_db_id,
                m.bag_db_id
            FROM building_matches m
            WHERE m.rn = 1
        ),

        unmatched_osm_records AS (
            SELECT
                'osm' AS source_dataset,
                o.source_record_id AS source_record_id,
                'osm' AS geometry_source,
                NULL::integer AS match_id,
                o.geom AS geom
            FROM osm_buildings_canonical o
            WHERE NOT EXISTS (
                SELECT 1
                FROM all_accepted_matches am
                WHERE am.osm_db_id = o.id
            )
        ),

        -- all bag records -- bring the geometry -- and bring the match_id --> from best
        all_bag_records AS (
            SELECT
                'bag' AS source_dataset,
                b.source_record_id AS source_record_id,
                'bag' AS geometry_source,
                bm.osm_db_id AS match_id,
                b.geom AS geom
            FROM bag_buildings_canonical b
            LEFT JOIN best_matches bm
            ON bm.bag_db_id = b.id
        )


        SELECT source_dataset, source_record_id, geometry_source, match_id, geom
        FROM unmatched_osm_records

        UNION ALL

        SELECT source_dataset, source_record_id, geometry_source, match_id, geom
        FROM all_bag_records

    """)

    try:
        # if rebuild:
        #     db.execute(text("TRUNCATE TABLE buildings RESTART IDENTITY"))

        result = db.execute(sql)
        db.commit()

        return result.rowcount if result.rowcount is not None else 0

    except Exception:
        db.rollback()
        raise



def resolve_attributes(db: Session) -> int:
    """
    Populate the final canonical `buildings` table from OSM and BAG DATASETS with 3 cases:
    1. matched BAG-OSM using the top-ranked OSM per BAG
    2. unmatched BAG using BAG only 
    3. unmatched OSM using OSM only


    Args:
    db: SQLAlchemy session

    Returns the number of inserted rows.

    # NOTES ON THE FUNCTION:
    -  COALESCE function returns the first non-NULL expression. If all arguments are NULL it will return Null.

    RESOLVE ATTRIBUTES - PRIORITY DATASET:
    --> year_built - present in BAG 
    --> roof_shape - present in OSM
    --> num_storeys - OSM 
    --> height_m - OSM
    --> occupancy_type - BAG 
    --> construction_type - OSM

    """

    sql = text("""
        UPDATE buildings f
        SET
            -- 1) BAG
            year_built = COALESCE(src.b_year_built, src.o_year_built),
            year_built_source = CASE
                WHEN src.b_year_built IS NOT NULL THEN 'bag'
                WHEN src.o_year_built IS NOT NULL THEN 'osm'
                ELSE NULL
            END,

            -- 1) OSM
            roof_shape = COALESCE(src.o_roof_shape, src.b_roof_shape),
            roof_shape_source = CASE
                WHEN src.o_roof_shape IS NOT NULL THEN 'osm'
                WHEN src.b_roof_shape IS NOT NULL THEN 'bag'
                ELSE NULL
            END,

            -- 1) OSM
            num_storeys = COALESCE(src.o_num_storeys, src.b_num_storeys),
            num_storeys_source = CASE
                WHEN src.o_num_storeys IS NOT NULL THEN 'osm'
                WHEN src.b_num_storeys IS NOT NULL THEN 'bag'
                ELSE NULL
            END,

            -- 1) OSM
            height_m = COALESCE(src.o_height_m, src.b_height_m),
            height_m_source = CASE
                WHEN src.o_height_m IS NOT NULL THEN 'osm'
                WHEN src.b_height_m IS NOT NULL THEN 'bag'
                ELSE NULL
            END,

            -- 1) OSM
            building_type = COALESCE(src.o_building_type, src.b_building_type),
            building_type_source = CASE
                WHEN src.o_building_type IS NOT NULL THEN 'osm'
                WHEN src.b_building_type IS NOT NULL THEN 'bag'
                ELSE NULL
            END,

            -- 1) BAG
            occupancy_type = COALESCE(src.b_occupancy_type, src.o_occupancy_type),
            occupancy_type_source = CASE
                WHEN src.b_occupancy_type IS NOT NULL THEN 'bag'
                WHEN src.o_occupancy_type IS NOT NULL THEN 'osm'
                ELSE NULL
            END,

            -- 1) OSM
            construction_type = COALESCE(src.o_construction_type, src.b_construction_type),
            construction_type_source = CASE
                WHEN src.o_construction_type IS NOT NULL THEN 'osm'
                WHEN src.b_construction_type IS NOT NULL THEN 'bag'
                ELSE NULL
            END

        FROM (
            SELECT
                f2.id AS building_id,

                b.year_built AS b_year_built,
                o.year_built AS o_year_built,

                b.roof_shape AS b_roof_shape,
                o.roof_shape AS o_roof_shape,

                b.num_storeys AS b_num_storeys,
                o.num_storeys AS o_num_storeys,

                b.height_m AS b_height_m,
                o.height_m AS o_height_m,

                b.building_type AS b_building_type,
                o.building_type AS o_building_type,

                b.occupancy_type AS b_occupancy_type,
                o.occupancy_type AS o_occupancy_type,

                b.construction_type AS b_construction_type,
                o.construction_type AS o_construction_type

            FROM buildings f2
            LEFT JOIN bag_buildings_canonical b
                ON f2.source_dataset = 'bag' AND f2.source_record_id = b.source_record_id
                
            LEFT JOIN osm_buildings_canonical o 
                ON ( f2.source_dataset = 'bag' AND f2.match_id IS NOT NULL AND f2.match_id::INTEGER = o.id)
                OR ( f2.source_dataset = 'osm' AND f2.source_record_id = o.source_record_id)
        ) AS src
        WHERE f.id = src.building_id;


    """)

    try:

        result = db.execute(sql)
        db.commit()

        return result.rowcount if result.rowcount is not None else 0

    except Exception:
        db.rollback()
        raise