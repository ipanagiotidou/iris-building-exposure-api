from app.core.db import Base, engine

# DO NOT DELETE THESE IMPORTS EVEN IF THE CLASSES ARE NOT ACCESSED ...
# REASON: "a model gets registered only when python IMPORTS THE FILE WHERE THE CLASS IS DEFINED"
from app.models.building import BAGCanonicalBuilding, OSMCanonicalBuilding, BuildingCanonicalBase, Building
from app.models.building_match import BuildingMatch
from app.models.source_building import OSMBuildingRaw, BAGBuildingRaw


def main():
    # IMPORTANT NOTE:
    #   - create_all() will only create tables from models that are already registered in Base.metadata
    #   - Registered = "a model gets registered only when python IMPORTS THE FILE WHERE THE CLASS IS DEFINED"
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()