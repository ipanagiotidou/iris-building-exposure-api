
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
    
    # 3857? CHECK UTM 

    """
    SQL: 
        - WITH clause defines a temporary result that can be used within a query

    """
    sql = text("""
        INSERT INTO building_matches (
            osm_building_id,
            bag_building_id,
            match_iou,
            centroid_distance_m,
            intersection_area_m2,
            match_method,
            match_status,
            match_confidence
        )
        WITH candidates AS (
            SELECT
                o.id AS osm_building_id,
                b.id AS bag_building_id,

                ST_Area(
                    ST_Intersection(
                        ST_Transform(o.geom, 3857),
                        ST_Transform(b.geom, 3857)
                    )
                ) AS intersection_area_m2,

                ST_Area(ST_Transform(o.geom, 3857)) AS osm_area_m2,
                ST_Area(ST_Transform(b.geom, 3857)) AS bag_area_m2,

                ST_Distance(
                    ST_Centroid(ST_Transform(o.geom, 3857)),
                    ST_Centroid(ST_Transform(b.geom, 3857))
                ) AS centroid_distance_m

            FROM buildings_osm_canonical o
            JOIN buildings_bag_canonical b
            ON ST_Intersects(o.geom, b.geom)
        ),
        scored AS (
            SELECT
                osm_building_id,
                bag_building_id,
                intersection_area_m2,
                centroid_distance_m,
                intersection_area_m2 / NULLIF((osm_area_m2 + bag_area_m2 - intersection_area_m2), 0) AS match_iou
            FROM candidates
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY osm_building_id
                    ORDER BY match_iou DESC, centroid_distance_m ASC
                ) AS rn
            FROM scored
            WHERE
                intersection_area_m2 > 0
                AND intersection_area_m2 / NULLIF((osm_area_m2 + bag_area_m2 - intersection_area_m2), 0) >= 0.10
                AND centroid_distance_m <= 20
        )
        SELECT
            osm_building_id,
            bag_building_id,
            match_iou,
            centroid_distance_m,
            intersection_area_m2,
            'geometry_iou_centroid' AS match_method,
            'accepted' AS match_status,
            match_iou AS match_confidence
        FROM ranked
        WHERE rn = 1;  
    """)

    #  ACTUAL EXAMPLE FROM WITH clause that creates temporary result "candidates": 
    """ [{'osm_building_id': 1, 'bag_building_id': 1086, 'intersection_area_m2': 2858.3462500725964, 'osm_area_m2': 2858.7582824350866, 'bag_area_m2': 2858.7464188594977, 'centroid_distance_m': 0.002836518686952818},
      {'osm_building_id': 2, 'bag_building_id': 499, 'intersection_area_m2': 0.66649169711007, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 213.86569388145136, 'centroid_distance_m': 35.51465309591829},
      {'osm_building_id': 2, 'bag_building_id': 902, 'intersection_area_m2': 2807.059288746372, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 2807.408029189145, 'centroid_distance_m': 0.00928699453896358},
      {'osm_building_id': 2, 'bag_building_id': 1170, 'intersection_area_m2': 0.02655041097794062, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 1110.8414234753263, 'centroid_distance_m': 52.642304046342296}]    
      """
    

    result = db.execute(sql)           # CursorResult Object: (db) connection execute returns a cursor (a structure that allows us to traverse a result)
    db.commit()
    return result.rowcount if result.rowcount is not None else 0






# PostGIS - intersection, IoU, Centroid Distance
# Python  - Candidates
def compute_osm_bag_match_candidates_with_python(db: Session) -> list[dict]:

    # INDEX FOR BETTER PERFRORMANCE.

    # PRODUCES ONE ROW PER MATCHING PAIR (o, b)
    # this means multiple candidate matches per OSM building
    # IMPORTANT NOTE: INNER JOIN --> if an OSM building has no intersecting BAG it will not appear at all
    # I SHOULD CHOOSE A FULL JOIN TO HAVE ALL MATHCED + UNMATHCED (FROM BOTH DATASETS)
    # DETECT THE UNMATCHED BASED ON THE NULL ON POSTGIS UNIQUE IDS PROBABLY - one the "other dataset" --> See SQL training with Baraa 
    
    # 3857? CHECK UTM 


    sql = text("""
        SELECT
            o.id AS osm_building_id,
            b.id AS bag_building_id,

            ST_Area(
                ST_Intersection(
                    ST_Transform(o.geom, 3857),
                    ST_Transform(b.geom, 3857)
                )
            ) AS intersection_area_m2,

            ST_Area(ST_Transform(o.geom, 3857)) AS osm_area_m2,
            ST_Area(ST_Transform(b.geom, 3857)) AS bag_area_m2,

            ST_Distance(
                ST_Centroid(ST_Transform(o.geom, 3857)),
                ST_Centroid(ST_Transform(b.geom, 3857))
            ) AS centroid_distance_m

        FROM osm_buildings_canonical o
        JOIN bag_buildings_canonical b
          ON ST_Intersects(o.geom, b.geom) 
    """)



    # IF I WAS MATHCING IN PYTHON
    result = db.execute(sql)           # CursorResult Object: (db) connection execute returns a cursor (a structure that allows us to traverse a result)
    rows = result.mappings().all()     # CursorResult object with a .mappings() method that returns a list of dicts (convert each row to a dictionary)

    """
    [{'FirstName': 'Gord', 'LastName': 'Thompson'}, 
     {'FirstName': 'Bob', 'LastName': 'Loblaw'}]

     ACTUAL EXAMPLE FROM MY DATASET: 
     [{'osm_building_id': 1, 'bag_building_id': 1086, 'intersection_area_m2': 2858.3462500725964, 'osm_area_m2': 2858.7582824350866, 'bag_area_m2': 2858.7464188594977, 'centroid_distance_m': 0.002836518686952818},
      {'osm_building_id': 2, 'bag_building_id': 499, 'intersection_area_m2': 0.66649169711007, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 213.86569388145136, 'centroid_distance_m': 35.51465309591829},
      {'osm_building_id': 2, 'bag_building_id': 902, 'intersection_area_m2': 2807.059288746372, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 2807.408029189145, 'centroid_distance_m': 0.00928699453896358},
      {'osm_building_id': 2, 'bag_building_id': 1170, 'intersection_area_m2': 0.02655041097794062, 'osm_area_m2': 2808.4664505405894, 'bag_area_m2': 1110.8414234753263, 'centroid_distance_m': 52.642304046342296}]    """

    candidates = []
    for row in rows:
        intersection_area = row["intersection_area_m2"] or 0.0
        osm_area = row["osm_area_m2"] or 0.0
        bag_area = row["bag_area_m2"] or 0.0

        union_area = osm_area + bag_area - intersection_area
        match_iou = intersection_area / union_area if union_area > 0 else 0.0   # in case of negative result set union as 0

        candidates.append(
            {
                "osm_building_id": row["osm_building_id"],
                "bag_building_id": row["bag_building_id"],
                "intersection_area_m2": intersection_area,
                "centroid_distance_m": row["centroid_distance_m"],
                "match_iou": match_iou,
            }
        )

    return candidates
