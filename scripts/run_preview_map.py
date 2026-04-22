from app.core.db import SessionLocal
from app.services.visualize import make_preview_map

def main():
    make_preview_map()


if __name__ == "__main__":
    main()