from app.core.db import Base, engine
# from app.models.aoi import AOI
from app.models.building import Building
from app.models.source_building import OSMBuildingRaw, MicrosoftBuildingRaw


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()