
""" 
MATCHING STRATEGY: 2-STEP LOGIC
    1) generate CANDIDATE PAIRS (compare buildings that spatially intersect or are close enough)
    2) compute METRICS (IoU, centroid distance, Intersection Area)

"""


from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.building_match import BuildingMatch


# PostGIS: both matches and candidates 
def match_osm_bag_buildings_with_postgis(db: Session) -> int:

    # INDEX FOR BETTER PERFRORMANCE.

    # PRODUCES ONE ROW PER MATCHING PAIR (o, b)
    # this means multiple candidate matches per OSM building
    # IMPORTANT NOTE: INNER JOIN --> if an OSM building has no intersecting BAG it will not appear at all
    # I SHOULD CHOOSE A FULL JOIN TO HAVE ALL MATHCED + UNMATHCED (FROM BOTH DATASETS)
    # DETECT THE UNMATCHED BASED ON THE NULL ON POSTGIS UNIQUE IDS PROBABLY - one the "other dataset" --> See SQL training with Baraa 
    

    """
    SQL: 
        - WITH clause defines a temporary result that can be used within a query

    """
    sql = text("""
        TRUNCATE table building_matches;
        INSERT INTO building_matches (
            bag_db_id,
            osm_db_id,
            osm_coverage_ratio,
            match_iou,
            centroid_distance_m,
            intersection_area_m2,
            match_method,
            match_confidence,
            rn
        )
        WITH candidates AS (
            SELECT
                o.id AS osm_db_id,
                b.id AS bag_db_id,
                ST_Transform(o.geom, 28992) AS o_geom_28992,
                ST_Transform(b.geom, 28992) AS b_geom_28992                

            FROM osm_buildings_canonical o
            JOIN bag_buildings_canonical b
            ON ST_Intersects(o.geom, b.geom)
        ),
        scored1 AS (
            SELECT
                osm_db_id,
                bag_db_id,
                ST_Area(ST_Intersection(o_geom_28992, b_geom_28992)) AS intersection_area_m2,
                ST_Area(o_geom_28992) AS osm_area_m2,
                ST_Area(b_geom_28992) AS bag_area_m2,
                ST_Distance(
                    ST_Centroid(o_geom_28992),
                    ST_Centroid(b_geom_28992)
                ) AS centroid_distance_m
            FROM candidates
        ),
        scored2 AS (
            SELECT
                osm_db_id,
                bag_db_id,
                intersection_area_m2,
                osm_area_m2,
                bag_area_m2,
                centroid_distance_m,
                intersection_area_m2 / NULLIF((osm_area_m2 + bag_area_m2 - intersection_area_m2), 0) AS match_iou,
                (intersection_area_m2 / osm_area_m2) AS osm_coverage_ratio
            FROM scored1
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY bag_db_id
                    ORDER BY match_iou DESC, centroid_distance_m ASC
                ) AS rn
            FROM scored2
            WHERE osm_coverage_ratio > 0.6 -- AND intersection_area_m2 > 0 AND match_iou >= 0.5 AND centroid_distance_m <= 20

        )
        SELECT 
            bag_db_id,
            osm_db_id,
            osm_coverage_ratio,
            match_iou,
            centroid_distance_m,
            intersection_area_m2,
            'geometry_cov_ratio_iou_centroid' AS match_method,
            match_iou AS match_confidence,
            rn
        FROM ranked
        -- WHERE rn = 1;  -- DO NOT INCLUDE THIS LINE... KEEP ALL MATCHING GEOMETRIES.  
               
    """)

    # WITH candidates AS (temporary result): creates something like...
    """ [{'osm_db_id': 1, 'bag_db_id': 1086, 'intersection_area_m2': 2858.3462500725964, 'osm_area_m2': 2858.7582824350866, 'bag_area_m2': 2858.7464188594977, 'centroid_distance_m': 0.002836518686952818},
      {'osm_db_id': 2, 'bag_db_id': 499, 'intersection_area_m2': 0.66649169711007, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 213.86569388145136, 'centroid_distance_m': 35.51465309591829},
      {'osm_db_id': 2, 'bag_db_id': 902, 'intersection_area_m2': 2807.059288746372, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 2807.408029189145, 'centroid_distance_m': 0.00928699453896358},
      {'osm_db_id': 2, 'bag_db_id': 1170, 'intersection_area_m2': 0.02655041097794062, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 1110.8414234753263, 'centroid_distance_m': 52.642304046342296}]    
      """
    

    result = db.execute(sql)           # CursorResult Object: (db) connection execute returns a cursor (a structure that allows us to traverse a result)
    db.commit()
    return result.rowcount if result.rowcount is not None else 0

