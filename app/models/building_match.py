from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BuildingMatch(Base):
    __tablename__ = "building_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    osm_building_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bag_building_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    match_iou: Mapped[float | None] = mapped_column(Float, nullable=True)      # IoU (Intersection over Union) --> Overlap Quality
    centroid_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)     # Proximity Quality 
    intersection_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)     # Useful for Debugging


    match_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    match_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # later for validation using OSM's ref:bag
    agrees_with_ref_bag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

          
          