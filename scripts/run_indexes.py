from app.core.db import engine
from app.services.indexes import create_spatial_indexes


def main() -> None:
    create_spatial_indexes(engine)
    print("Spatial indexes created successfully.")


if __name__ == "__main__":
    main()