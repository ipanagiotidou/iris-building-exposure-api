



This project creates a building-level dataset by combining multiple open sources to create a more complete and accurate representation, both geometrically and semantically, for a selected area of interest.




## Architecture

Fetching OSM + BAG<br>
↓<br>
Ingestion in PostGIS<br>
↓<br>
Spatial Indexing<br>
↓<br>
Spatial Matching<br>
↓<br>
Final Buildings Table with Geometry \& Attributes <br>
↓<br>
Attribute Enrichment<br>
↓<br>
Export



## Tech Stack

* Python 3.11
* Poetry
* PostgreSQL + PostGIS
* GeoPandas
* SQLAlchemy
* Docker
* Make



## Requirements

* Python 3.11
* Poetry version 2.1.2
* Docker \& Docker Compose Docker version 28.5.1
* Make GNU Make 4.2.1


## Quick Start

```bash
git clone https://github.com/ipanagiotidou/iris-building-exposure-api.git
cd iris-building-exposure-api
make install
make db-up
make init-db
make all
```

**Outputs**:
* `outputs/final_buildings.geojson `, 
* `building_comparison_map.html`

**Original BAG and OSM data**:
* `outputs/bag_buildings.geojson`, 
* `outputs/osm_buildings.geojson`



##  Pipeline Commands

|Step|Command|
|-|-|
|Install dependencies|`make install`|
|Build DB Image|`make db-up`|
|Create DB tables|`make init-db`|
|Ingest data|`make ingest-all`|
|Create Indexes|`make create-indexes`|
|Spatial Matching|`make match`|
|Create Final table|`make run-final`|
|Export geojson, html|`make export-final`|
|Run full pipeline|`make run`|






## Data Sources \& Licenses

This project uses data from the following sources:

### OpenStreetMap (OSM)

* Source: https://www.openstreetmap.org
* License: **Open Database License (ODbL) v1.0**
* Details: https://opendatacommons.org/licenses/odbl/1-0/


### BAG (Basisregistratie Adressen en Gebouwen)

* Source: https://www.kadaster.nl
* License: **Public Domain (CC0 1.0)**
* Details: https://creativecommons.org/publicdomain/zero/1.0/



### Attribution

© OpenStreetMap contributors



### Author
Ioanna Panagiotidou

