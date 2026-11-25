from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String,  DateTime, func, ForeignKey, UniqueConstraint 
from sqlalchemy.orm import Mapped, mapped_column, relationship  # orm = object-related mapping 
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from app.core.db.db import Base

""" 
EXPLAIN Mapped + mapped_column:

    - Altogether: “geom is a mapped attribute, stored in DB as a geometry COLUMN."

    - geom: Mapped[...] = mapped_column(...) 
    # Left side: COLUMN-MANAGED ATTRIBUTE
    # Right side: DATABASE COLUMN

    - LEFT SIDE: geom: Mapped[object]   --> Python typing / ORM hint.
            --> type hint for SQLAlchemy ORM (Python typing / ORM hint).
            --> This attribute is mapped to a database COLUMN.
            --> This is a COLUMN-MANAGED ATTRIBUTE, NOT JUST a normal Python attribute. 
    
    - RIGHT SIDE: mapped_column(Geometry(...))
            --> the actual database column definition.

"""

# Define the Data Model. 
# To do so, make a Python class that inherits from Base, which is the declarative base class provided by SQLAlchemy.
# The canonical building table should be STRICT. We want to enforce a consistent, clean, canonical schema.
# Each attribute of the class represents a column in the relevant database table.
# registered with SQLAlchemy's Base.metadata when the module is imported.
class Building(Base):
    # Name of table in the database.
    __tablename__ = "buildings"      # one row per canonical building, containing the selected/final attributes.


    # Identity
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)  # when primary_key=True, SQLAlchemy automatically creates a unique index on that column.

    # Geometry
    geom: Mapped[object] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326), 
        nullable=False
    )

    # Geometry attributes 
    footprint_area_m2: Mapped[float | None] = mapped_column(Float)
    floorspace_m2: Mapped[float | None] = mapped_column(Float)
    
    # Building attributes 
    building_type: Mapped[str | None] = mapped_column(String(100)) 
    construction_type: Mapped[str | None] = mapped_column(String(100))
    occupancy_type: Mapped[str | None] = mapped_column(String(100))

    num_storeys: Mapped[int | None] = mapped_column(Integer)
    height_m: Mapped[float | None] = mapped_column(Float,)
    roof_shape: Mapped[str | None] = mapped_column(String(100))
    year_built: Mapped[int | None] = mapped_column(Integer)


    # Processing Information
    is_matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False) 
    match_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    inference_method: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(1000))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), 
        onupdate=func.now(), nullable=False
    )


    # full source tags snapshot as JSON  
    tags_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


    # RELATIONSHIPS - it's not a DB column. A Convenient Python Navigation.
    # The relationship doesn't create an additional database column. The actual database link is established by building_id and its ForeignKey.
    # relationship attribute that ALLOWS you to ACCESS the RELATED BuildingSourceRecord objects associated with a Building object.
    # The relationship() definitions add the convenient Python-level navigation. 
    # For example: building.source_records --> returns all source records belonging to that building.
    # Why cascade="all, delete-orphan"?
    #       -- If a canonical building is deleted, its associated source records are deleted too. 
    #       -- This is appropriate if source records cannot exist independently of a canonical building.
    source_records: Mapped[list["BuildingSourceRecord"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan"
    )


    def __repr__(self) -> str:
        return f"Building(id={self.id!r}, source={self.source_dataset!r})"
    

