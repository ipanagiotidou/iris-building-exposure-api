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
               source_dataset,
               source_record_id,
               footprint_area_m2,
               footprint_area_m2_source,
               floorspace_m2,
               floorspace_m2_source,
               building_type,
               building_type_source,
               construction_type,
               construction_type_source,
               occupancy_type,
               occupancy_type_source,
               num_storeys,
               num_storeys_source,
               height_m,
               height_m_source,
               roof_shape,
               roof_shape_source, 
               year_built,
               year_built_source,
               tags_json,
               geometry_source, 
               ST_Transform(geom, 4326) AS geom              
        FROM buildings
    """)

    gdf = gpd.read_postgis(sql, engine, geom_col="geom")
   
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(output, driver="GeoJSON")
    return output


def export_raw_osm_buildings(
    engine: Engine,
    output_path: str = "outputs/osm_buildings.geojson",
) -> Path:
    
    """
    Export the initial OSM table to a GeoJSON file.

    Args:
        engine: SQLAlchemy engine
        output_path: path to the output GeoJSON file

    Returns:
        Path to the written GeoJSON file
    """

    sql = text("""
        SELECT 
               *           
        FROM osm_buildings_raw
    """)

    gdf = gpd.read_postgis(sql, engine, geom_col="geom")
   
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(output, driver="GeoJSON")
    return output




def export_raw_bag_buildings(   
        engine: Engine,
        output_path: str = "outputs/bag_buildings.geojson",
) -> Path:
    
    """
    Export the initial BAG table to a GeoJSON file.

    Args:
        engine: SQLAlchemy engine
        output_path: path to the output GeoJSON file

    Returns:
        Path to the written GeoJSON file
    """

    sql = text("""
        SELECT 
               *           
        FROM bag_buildings_raw
    """)

    gdf = gpd.read_postgis(sql, engine, geom_col="geom")
   
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(output, driver="GeoJSON")
    return output