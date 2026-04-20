
from app.core.db import SessionLocal
from app.workflows.match_osm_bag import run_match_osm_bag 



def main():

    db = SessionLocal()
    try:
        result = run_match_osm_bag(db=db)

        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
