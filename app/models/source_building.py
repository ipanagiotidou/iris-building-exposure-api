"""raw data is preserved"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.core.db import Base


""" 
GENERAL THINGS:
    - Altogether: “geom is a mapped attribute, stored in DB as a geometry column”

    - geom: Mapped[object] 
            --> type hint for SQLAlchemy ORM (Python typing / ORM hint)
            --> “This attribute is mapped to a database COLUMN
            --> this is a COLUMN-managed ATTRIBUTE, NOT JUST a normal Python attribute
    
    - geom = mapped_column(Geometry(...))
            --> the actual database column definition
            --> 

"""

### --------- OSM ------------------------------------------------------------------------------

class OSMBuildingRaw(Base):

    """
    the raw OSM building data table should be PERMISSIVE, not strict. 
    We want to preserve all the raw data, even if some columns are missing or have inconsistent values. 
    
    So raw table columns should be:
        - close to source naming
        - mostly nullable
        - lightly cleaned
        - easy to inspect

        Not:
        - strict
        - canonical
        - heavily interpreted

    Logic for defining the raw table schema DATA TYPES:
        Core OSM fields like osm_id, element, and geom have a well-defined structure, 
        so they can be strictly typed in your database schema. 
        However, OSM tags are inherently flexible and stored as free-form key-value pairs, 
        where values are not consistently typed (even when they represent numbers or booleans). 
        For this reason, it’s best to store tags as strings (or JSONB) during ingestion and only 
        cast selected fields to strict types during a later normalization step.

    """
    
    __tablename__ = "osm_buildings_raw"

    #  __table_args__ attribute allows passing extra arguments to that Table. 
    # UniqueConstraint("col2", "col3", name="uix_1")
    # What makes one raw OSM record unique --> Osm_id is unique only within object type. (relation, way, node)
    __table_args__ = (
        UniqueConstraint("element", "osm_id", name= "uq_osm_raw_element_osm_id"),
    )
    

    # this id is NOT based on pandas index 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Raw Source Identity 
    # some OSM IDs are numeric, but some are alphanumeric (e.g. "way/12345", "relation/67890")
    osm_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    element: Mapped[str | None] = mapped_column(String(50), nullable=True)  # way, relation

    # selected raw OSM tags
    # I used building tag to fetch so it shouldn't be null.
    building: Mapped[str] = mapped_column(String(50), nullable=False)  # building is the building_type 
    building_use: Mapped[str | None] = mapped_column(String(50), nullable=True)   
    building_levels: Mapped[str | None] = mapped_column(String(50), nullable=True)
    building_material: Mapped[str | None] = mapped_column(String(50), nullable=True)

    ref_bag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    height: Mapped[str | None] = mapped_column(String(50), nullable=True)

    roof_shape: Mapped[str | None] = mapped_column(String(50), nullable=True)
    roof_material: Mapped[str | None] = mapped_column(String(50), nullable=True)
    roof_levels: Mapped[str | None] = mapped_column(String(50), nullable=True)
    roof_orientation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    roof_height: Mapped[float | None] = mapped_column(String(50), nullable=True)
    roof_direction: Mapped[str | None] = mapped_column(String(50), nullable=True)


    # full source tags snapshot as JSON  
    tags_json: Mapped[dict | None] = mapped_column(JSONB, nullable=False)

    # Datetime when the record was ingested into the database.
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)       
    
    # Raw Geometry 
    # OBJECT: cause geomety data can be in various formats (e.g., Polygon, Multi-polygon, Point, WKB, WKT, GeoJSON).
    # I will try to ingest the geometry as WKB (Well-Known Binary) format.
    # WKB is a compact binary representation of geometry that is more efficient for storage and querying in PostGIS compared to WKT (Well-Known Text) or GeoJSON.
    geom: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=False) # multipolygon, polygon, linestring, point, etc.


    def __repr__(self) -> str:
        return f"OSMBuildingRaw(id={self.id!r}, osm_id={self.osm_id!r})"




### --------- BAG ------------------------------------------------------------------------------

class BAGBuildingRaw(Base):
    

    """
    the raw BAG building data table should be PERMISSIVE, not strict. 
    We want to preserve all the raw data, even if some columns are missing or have inconsistent values. 
    
    So raw table columns should be:
        - close to source naming
        - mostly nullable
        - lightly cleaned
        - easy to inspect
        Not:
        - strict
        - canonical
        - heavily interpreted


    """
    
    __tablename__ = "bag_buildings_raw"

    #  __table_args__ attribute allows passing extra arguments to that Table. 
    # UniqueConstraint("col2", "col3", name="uix_1")
    __table_args__ = (
        UniqueConstraint("bag_id", name="uq_bag_raw_bag_id"),
    )


    # this id is NOT based on pandas index 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Raw Source Identity 
    # some BAG IDs are numeric, but could be anything.
    # this should change to identificatie
    bag_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  #  bag_id: identificatie

    # selected raw BAG columns
    aantal_verblijfsobjecten: Mapped[str] = mapped_column(String(50), nullable=True)    # number_of_units: number of residential properties
    bouwjaar: Mapped[str | None] = mapped_column(String(50), nullable=True)              # construction_year
    gebruiksdoel: Mapped[str | None] = mapped_column(String(250), nullable=True)          # intented_use: e.g. retail function, residential function
    status: Mapped[str | None] = mapped_column(String(250), nullable=True)     # status: e.g. demolished,  in use , renovation, not realized 


    # Datetime when the record was ingested into the database.
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)       
    
    # Raw Geometry 
    # object cause geomety data can be in various formats (e.g., WKB, WKT, GeoJSON).
    # I will try to ingest the geometry as WKB (Well-Known Binary) format in PostGIS.
    # WKB is a compact binary representation of geometry that is more efficient for storage and querying in PostGIS compared to WKT (Well-Known Text) or GeoJSON.
    geom: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=False) # multipolygon, polygon, linestring, point, etc.


    def __repr__(self) -> str:
        return f"BAGBuildingRaw(id={self.id!r}, osm_id={self.bag_id!r})"






### --------- MICROSOFT ------------------------------------------------------------------------------

class MicrosoftBuildingRaw(Base):
    
    __tablename__ = "microsoft_buildings_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # aoi_id: Mapped[int] = mapped_column(ForeignKey("aois.id"), nullable=False, index=True)
    # source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    # ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


