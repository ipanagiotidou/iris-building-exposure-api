from app.core.db import SessionLocal
from app.services.finalize_buildings import populate_geometry_in_final_buildings_table

def main():
    db = SessionLocal()
    try:
        inserted = populate_geometry_in_final_buildings_table(db, rebuild=True)
        print(f"Inserted {inserted} rows.")
    finally:
        db.close()

if __name__ == "__main__":
    main()