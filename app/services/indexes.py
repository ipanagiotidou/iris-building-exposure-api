from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_spatial_indexes(engine: Engine) -> None:
    """
    Create spatial indexes needed by the pipeline.
    Safe to run multiple times.
    """
    sql_statements = [
        """
        CREATE INDEX IF NOT EXISTS idx_bag_buildings_canonical_geom
        ON bag_buildings_canonical
        USING GIST (geom)
        WHERE geom IS NOT NULL;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_osm_buildings_canonical_geom
        ON osm_buildings_canonical
        USING GIST (geom)
        WHERE geom IS NOT NULL;
        """,
    ]

    with engine.begin() as conn:
        for sql in sql_statements:
            conn.execute(text(sql))