from pathlib import Path

import geopandas as gpd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def export_final_buildings_to_geojson(
    engine: Engine,
    output_path: str = "outputs/final_buildings.geojson",
) -> Path:
    """
    Export the final `buildings` table to a GeoJSON file.

    Args:
        engine: SQLAlchemy engine
        output_path: path to the output GeoJSON file

    Returns:
        Path to the written GeoJSON file
    """

    sql = text("""
        SELECT
            id,
            source_dataset,
            source_record_id,
            geom
        FROM buildings
    """)

    gdf = gpd.read_postgis(sql, engine, geom_col="geom")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(output, driver="GeoJSON")
    return output