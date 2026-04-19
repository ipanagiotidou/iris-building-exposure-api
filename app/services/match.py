
""" 
MATCHING STRATEGY: 2-STEP LOGIC
    1) generate CANDIDATE PAIRS (compare buildings that spatially intersect or are close enough)
    2) compute METRICS (IoU, centroid distance, Intersection Area)

"""


from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.building_match import BuildingMatch


def compute_osm_bag_match_candidates(db: Session) -> list[dict]:

    # PRODUCES ONE ROW PER MATCHING PAIR (o, b)
    # this means multiple candidate matches per OSM building
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

        FROM buildings_osm_canonical o
        JOIN buildings_bag_canonical b
          ON ST_Intersects(o.geom, b.geom)
    """)

    result = db.execute(sql)
    # rows = result.mappings().all()

    # candidates = []
    # for row in rows:
    #     intersection_area = row["intersection_area_m2"] or 0.0
    #     osm_area = row["osm_area_m2"] or 0.0
    #     bag_area = row["bag_area_m2"] or 0.0

    #     union_area = osm_area + bag_area - intersection_area
    #     match_iou = intersection_area / union_area if union_area > 0 else 0.0

    #     candidates.append(
    #         {
    #             "osm_building_id": row["osm_building_id"],
    #             "bag_building_id": row["bag_building_id"],
    #             "intersection_area_m2": intersection_area,
    #             "centroid_distance_m": row["centroid_distance_m"],
    #             "match_iou": match_iou,
    #         }
    #     )

    # return candidates
    return result