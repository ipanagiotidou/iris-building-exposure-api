import geopandas as gpd
import folium
from sqlalchemy import create_engine

from app.core.config import settings



    

def make_preview_map():
    engine = create_engine(settings.database_url)

    tooltip = folium.GeoJsonTooltip(fields=[
        "source_dataset",
        "source_record_id",
        "footprint_area_m2",
        "footprint_area_m2_source",
        "floorspace_m2",
        "floorspace_m2_source",
        "building_type",
        "building_type_source",
        "occupancy_type",
        "occupancy_type_source",
        "num_storeys",
        "num_storeys_source",
        "height_m",
        "height_m_source",
        "year_built",
        "year_built_source",
        "geometry_source"])

    bag_gdf = gpd.read_postgis(
        """
        SELECT
            source_dataset,
            source_record_id,
            footprint_area_m2,
            footprint_area_m2_source,
            floorspace_m2,
            floorspace_m2_source,
            building_type,
            building_type_source,
            occupancy_type,
            occupancy_type_source,
            num_storeys,
            num_storeys_source,
            height_m,
            height_m_source,
            year_built,
            year_built_source,
            geometry_source,
            geom
        FROM bag_buildings_canonical
        """,
        engine,
        geom_col="geom"
    )

    osm_gdf = gpd.read_postgis(
        """
        SELECT
            source_dataset,
            source_record_id,
            footprint_area_m2,
            footprint_area_m2_source,
            floorspace_m2,
            floorspace_m2_source,
            building_type,
            building_type_source,
            occupancy_type,
            occupancy_type_source,
            num_storeys,
            num_storeys_source,
            height_m,
            height_m_source,
            year_built,
            year_built_source,
            geometry_source,
            geom
        FROM osm_buildings_canonical
        """,
        engine,
        geom_col="geom"
    )

    final_gdf = gpd.read_postgis(
        """
        SELECT
            source_dataset,
            source_record_id,
            footprint_area_m2,
            footprint_area_m2_source,
            floorspace_m2,
            floorspace_m2_source,
            building_type,
            building_type_source,
            occupancy_type,
            occupancy_type_source,
            num_storeys,
            num_storeys_source,
            height_m,
            height_m_source,
            year_built,
            year_built_source,
            geometry_source,
            geom
        FROM buildings
        """,
        engine,
        geom_col="geom"
    )

    bag_gdf = bag_gdf.to_crs(4326)
    osm_gdf = osm_gdf.to_crs(4326)
    final_gdf = final_gdf.to_crs(4326)

    center = final_gdf.unary_union.centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=17, tiles="CartoDB positron")

    folium.GeoJson(
        bag_gdf,
        name="BAG canonical",
        style_function=lambda x: {
            "color": "blue",
            "weight": 1,
            "fillOpacity": 0.15,
        },
        tooltip=folium.GeoJsonTooltip(fields=["source_record_id", "year_built"])
    ).add_to(m)  

    folium.GeoJson(
        osm_gdf,
        name="OSM canonical",
        style_function=lambda x: {
            "color": "red",
            "weight": 1,
            "fillOpacity": 0.15,
        },
        tooltip=folium.GeoJsonTooltip(fields=["source_record_id", "building_type", "num_storeys"])
    ).add_to(m)  #tooltip=folium.GeoJsonTooltip(fields=["source_record_id", "building_type", "num_storeys"])


    folium.GeoJson(
        final_gdf,
        name="Final buildings",
        style_function=lambda x: {
            "color": "green",
            "weight": 2,
            "fillOpacity": 0.2,
        },
        tooltip=tooltip
    ).add_to(m)  # tooltip=folium.GeoJsonTooltip(fields=["source_dataset", "source_record_id", "height_m", "num_storeys", "roof_shape"])

    folium.LayerControl(collapsed=False).add_to(m)

    m.save("outputs/building_comparison_map.html")