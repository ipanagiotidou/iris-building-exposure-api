
.PHONY: run stop restart logs

help:
	@echo "Available commands:"
	@echo "  make install        - install Poetry dependencies"
	@echo "  make db-up          - start PostGIS in Docker"
	@echo "  make db-down        - stop Docker services"
	@echo "  make db-reset       - stop Docker services and delete DB volume"
	@echo "  make db-logs        - tail database logs"
	@echo "  make db-ps          - show Docker service status"
	@echo "  make compose-config - validate/render docker compose config"
	@echo "  make init-db        - create database tables"
	@echo "  make dev            - run FastAPI development server"
	@echo "  make run            - alias for dev"
	@echo "  make check          - start DB and initialize tables"

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

# initialize tables 
create-db-tables:
	poetry run python -m scripts.init_db

# start the db
db-up:
	docker-compose up -d db

# stop the db 
db-down:
	docker-compose down

# reset the db volume 
db-down-v:
	docker-compose down -v

reset-db:
	curl -X POST http://localhost:8000/buildings/admin/reset-db

# ensure PostGIS exists
enable-postgis:
	docker exec -i building_exposure_db psql -U postgres -d building_exposure -c "CREATE EXTENSION IF NOT EXISTS postgis;"
	docker exec -i building_exposure_db psql -U postgres -d building_exposure -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

# enable postgis & create tables in one command
init-db: enable-postgis
	poetry run python -m scripts.init_db

ingest-all:
	poetry run python -m scripts.run_ingest_all

match:
	poetry run python -m scripts.run_match_osm_bag

run-final-geom:
	poetry run python -m scripts.run_pipeline


epport-final:
	poetry run python -m scripts.run_export



