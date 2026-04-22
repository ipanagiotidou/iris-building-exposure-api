from app.core.db import SessionLocal
from app.services.finalize_buildings import populate_final_geometry, resolve_attributes, derive_missing_attributes

def main():
    db = SessionLocal()
    try:
        inserted = populate_final_geometry(db)
        print(f"Inserted {inserted} rows.")
        attr_resolved = resolve_attributes(db)
        print(f"ATTRIBUTES RESOLVED.")
        derive_missing_attributes(db)
        print(f"ATTRIBUTES DERIVED.")

    finally:
        db.close()

if __name__ == "__main__":
    main()