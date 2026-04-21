from datetime import datetime

from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint
from geoalchemy2 import Geometry

from sqlalchemy.dialects.postgresql import JSONB


from app.core.db import Base

""" 
Mapped: A type annotation that indicates a mapped column in a SQLAlchemy ORM model.
mapped_column: A function used to define a column in a SQLAlchemy ORM model, specifying its type and other attributes.

This structure, known as a Declarative Mapping, defines at once both a Python object model, 
as well as database metadata that describes real SQL tables that exist, 
or will exist, in a particular database:

In SQLAlchemy’s declarative style, each MAPPED CLASS represents a table definition plus the Python object model for rows in that table

"""

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


# The canonical building table should be STRICT, not permissive.
# We want to enforce a consistent, clean, canonical schema. 
class BuildingCanonicalBase(Base):
    __abstract__ = True


    # Identity
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_dataset: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Geometry - related 
    footprint_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    footprint_area_m2_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    floorspace_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    floorspace_m2_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Core attributes 
    building_type: Mapped[str | None] = mapped_column(String(100), nullable=True) 
    building_type_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    construction_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    construction_type_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    occupancy_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occupancy_type_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    num_storeys: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_storeys_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_m_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    roof_shape: Mapped[str | None] = mapped_column(String(100), nullable=True)
    roof_shape_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    year_built: Mapped[str | None] = mapped_column(Integer, nullable=True)
    year_built_source: Mapped[str | None] = mapped_column(String(100), nullable=True)


    # Later pipeline fields
    match_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_matched: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Created 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # full source tags snapshot as JSON  
    tags_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Geometry
    geometry_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # NOT centroid: Mapped[object | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    def __repr__(self) -> str:
        return f"Building(id={self.id!r}, source={self.source_dataset!r})"
    


class OSMCanonicalBuilding(BuildingCanonicalBase):
    __tablename__ = "osm_buildings_canonical"

    # # IMPROVEMENT FOR DUPLICATES: 
    # # I SHOULD ENFORCE A UNIQUE CONSTRAINT HERE AS WELL. 
    # # I AM MISSING THE ELEMENT COLUMN TO CONSTRUCT IT and make it robust
    # __table_args__ = (
    #     UniqueConstraint("source_record_id"),
    # )

class BAGCanonicalBuilding(BuildingCanonicalBase):
    __tablename__ = "bag_buildings_canonical"

    # # DUPLICATES NO MORE:
    # # UniqueConstraint("col2", "col3", name="uix_1")
    # __table_args__ = (
    #     UniqueConstraint("source_record_id"),
    # )


class Building(BuildingCanonicalBase):
    __tablename__ = "buildings"

