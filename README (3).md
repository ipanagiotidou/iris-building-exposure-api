# 🏗️ Building Exposure Pipeline

!\[Python](https://img.shields.io/badge/python-3.11-blue)
!\[Poetry](https://img.shields.io/badge/poetry-managed-blueviolet)
!\[PostGIS](https://img.shields.io/badge/postgis-enabled-green)
!\[Docker](https://img.shields.io/badge/docker-ready-blue)
!\[License](https://img.shields.io/badge/license-MIT-lightgrey)

A geospatial data pipeline that ingests, matches, and enriches building data from OSM and BAG into a unified canonical dataset.

\---

## ✨ Features

* Canonical data modeling (OSM + BAG)
* Geometric matching (IoU, centroid distance, coverage ratio)
* Attribute enrichment with source prioritization
* Spatial indexing for performance
* End-to-end pipeline via Make
* GeoJSON export

\---

## 🧱 Architecture



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

\---

## 🧰 Tech Stack

* Python 3.11
* Poetry
* PostgreSQL + PostGIS
* GeoPandas
* SQLAlchemy
* Docker
* Make

\---

## 📁 Project Structure

```
├── app/
│ ├── core/ # DB config, settings
│ ├── models/ # ORM models
│ └── services/ # ingest, match, enrichment logic
│
├── scripts/ # pipeline entry points
├── outputs/ # exported results
│
├── Makefile
├── pyproject.toml
├── .env.example
└── README.md
```

\---

## ⚙️ Requirements

* Python 3.11
* Poetry
* Docker \& Docker Compose
* Make

\---

## 🚀 Quick Start

```bash
git clone <your-repo-url>
cd <project>
make install
cp .env.example .env
make pipeline
```

Output:

```
outputs/final\_buildings.geojson
```

🔐 Environment Setup

Create a .env file:

```
cp .env.example .env
```

Example:

```
POSTGRES\_USER=postgres
POSTGRES\_PASSWORD=postgres
POSTGRES\_DB=building\_exposure
POSTGRES\_HOST=localhost
POSTGRES\_PORT=5432
```

## ▶️ Pipeline Commands

|Step|Command|
|-|-|
|Install|`make install`|
|Init DB|`make init-db`|
|Ingest|`make ingest-all`|
|Indexes|`make create-indexes`|
|Match|`make match`|
|Final table|`make run-final`|
|Export|`make export-final`|
|Full pipeline|`make run`|

\---

## 🧠 Matching Logic

Buildings are matched using:

* Intersection-over-Union (IoU)
* Centroid distance
* Coverage ratio

Top match (`rn = 1`) is selected per BAG building.

\---

## 🏗️ Data Model Strategy

### Geometry

* BAG = primary geometry source
* OSM used for enrichment or when BAG is missing

\---

### Attribute Priority

|Attribute|Priority|
|-|-|
|year\_built|BAG → OSM|
|occupancy\_type|BAG → OSM|
|roof\_shape|OSM → BAG|
|height|OSM → BAG|
|building\_type|OSM → BAG|
|construction\_type|OSM → BAG|

\---

### Tags

* `tags\_json` comes from OSM
* Applied to:

  * OSM buildings
  * BAG buildings with an OSM match

\---

## 🗺️ Coordinate Systems

* Matching: EPSG:28992
* Export: EPSG:4326

\---

## ⚡ Performance

Spatial indexes are created on geometry columns:

```sql
CREATE INDEX idx\_buildings\_geom
ON buildings
USING GIST (geom);
```

📦 Output
`outputs/final\_buildings.geojson `

Includes:

* geometry
* enriched attributes
* source tracking
* OSM tags

Check data

```sql
SELECT COUNT(\*) FROM buildings;
```

\---

## 📜 Data Sources \& Licenses

This project uses data from the following sources:

### 🗺️ OpenStreetMap (OSM)

* Source: https://www.openstreetmap.org
* License: **Open Database License (ODbL) v1.0**
* Details: https://opendatacommons.org/licenses/odbl/1-0/

**Requirements:**

* Attribution required
* Share-alike: any derived database must also be shared under ODbL

### 🏢 BAG (Basisregistratie Adressen en Gebouwen)

* Source: https://www.kadaster.nl
* License: **Public Domain (CC0 1.0)**
* Details: https://creativecommons.org/publicdomain/zero/1.0/

**Notes:**

* Data can be used freely without restrictions
* Attribution is not legally required (but recommended)

\---

## 📦 Dataset License

The dataset in `outputs/` is derived from OpenStreetMap and BAG data.

* OSM data is licensed under **ODbL v1.0**
* BAG data is licensed under **CC0 1.0**

As a result, the final dataset is distributed under:

👉 **Open Database License (ODbL) v1.0**

If you use or redistribute this dataset, you must:

* Provide attribution to OpenStreetMap contributors
* Share any derivative database under the same license

See `outputs/LICENSE.txt` for details.

\---

### ⚠️ Important

The final dataset produced by this pipeline may be considered a **derived database** under the OSM ODbL license.

If you distribute or share the resulting dataset:

* You must provide proper attribution to OpenStreetMap contributors
* You may be required to share the dataset under the same ODbL license

\---

### 📌 Attribution

© OpenStreetMap contributors

\---

👤 Author

Ioanna Panagiotidou

