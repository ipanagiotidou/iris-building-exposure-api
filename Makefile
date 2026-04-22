
# full pipeline
all: init-db ingest-all create-indexes match run-final export-all 

install:
	poetry install 

# run the api locally 
run:
	cd app && poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# stop:
# 	pkill -f "uvicorn main:app" || true

# kill by port 
stop:
	fuser -k 8000/tcp || true

restart: stop
	cd app && poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000

logs:
	lsof -i :8000 || true


# start the db
db-up:
	docker-compose up -d db

# stop the db 
db-down:
	docker-compose down

# reset the db volume 
db-down-v:
	docker-compose down -v

# ensure PostGIS exists
enable-postgis:
	docker exec -i building_exposure_db psql -U postgres -d building_exposure -c "CREATE EXTENSION IF NOT EXISTS postgis;"
	docker exec -i building_exposure_db psql -U postgres -d building_exposure -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

# enable postgis & create tables in one command
init-db: enable-postgis
	poetry run python -m scripts.init_db

ingest-all:
	poetry run python -m scripts.run_ingest_all

# after ingesting the data - before matching
create-indexes:
	poetry run python -m scripts.run_indexes

match:
	poetry run python -m scripts.run_match_osm_bag

run-final:
	poetry run python -m scripts.run_pipeline

export-final:
	poetry run python -m scripts.run_export

export-bag:
	poetry run python -m scripts.run_export_bag

export-osm:
	poetry run python -m scripts.run_export_osm

export-all: export-final export-bag export-osm



