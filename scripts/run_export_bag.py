from sqlalchemy.engine import Engine
from app.core.db import engine
from app.core.db import SessionLocal
from app.services.export import export_raw_bag_buildings

def main():
    db = SessionLocal()
    try:
        output = export_raw_bag_buildings(engine=engine)
        print(f"output {output} ")
    finally:
        db.close()

if __name__ == "__main__":
    main()