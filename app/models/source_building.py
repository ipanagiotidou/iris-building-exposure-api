from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String,  DateTime, func, ForeignKey, UniqueConstraint 
from sqlalchemy.orm import Mapped, mapped_column, relationship  # orm = object-related mapping 
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from app.core.db.db import Base
from app.models import Building


# Its purpose is to preserve every original source record associated with a canonical building, without duplicating the canonical building itself.
# registered with SQLAlchemy's Base.metadata when the module is imported.
# Relationship 1 Canonical Record -> Many Source Records 
# CONNECT SOURCE WITH CANONICAL THROUGH MATCHING LOGIC - we can connect the source records to your canonical building table through the matching workflow
class BuildingSourceRecord(Base):
    __tablename__ = "building_source_records"

    # CONSTRAINT: prevent duplicate source records from being linked to the same canonical building
    __table_args__ = (
        UniqueConstraint(
            "source_dataset",
            "source_record_id",
            name="uq_building_source_record"
        ),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FOREIGN KEY TO CANONICAL TABLE 
    # Link to canonical building - This attribute is a foreign key that refers to the primary key of the canonical building table.
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id"),   
        nullable=True,
        index=True
    )

    # Original source identity
    source_dataset: Mapped[str] = mapped_column(String(50), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Original source attributes
    source_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Original source geometry
    source_geom: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326),
        nullable=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


    # RELATIONSHIPS
    # The relationship doesn't create an additional database column. The actual database link is established by building_id and its ForeignKey.
    # RELATIONSHIP ATTRIBUTE that allows you to access the related Building object associated with a BuildingSourceRecord object.
    # The relationship() definitions add the convenient Python-level navigation. 
    # For example: building_source_record.building --> returns the canonical building associated with that source record.
    # NOTE: the "Building | None" was added because the building_id attribute will initially be NULL and will be populated during matching.
    building: Mapped["Building | None"] = relationship(
        back_populates="source_records"
    )
