from sqlalchemy.engine import Engine
from app.core.db import engine


from app.core.db import SessionLocal
from app.services.export import export_final_buildings_to_geojson

def main():
    db = SessionLocal()
    try:
        output = export_final_buildings_to_geojson(engine=engine)
        print(f"output {output} ")
    finally:
        db.close()

if __name__ == "__main__":
    main()