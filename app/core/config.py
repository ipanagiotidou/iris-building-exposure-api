
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

"""
pydantic setting (→ structured, validated, scalable):   preferred over os.getenv(...) → low-level, manual
 - reads from .env or environment     --> MAPS database_url to environment variable DATABASE_URL
 - validates types
 - throws error if missing
 - gives structured object 

"""

class Settings(BaseSettings):
    # database
    database_url: str

    # API keys / endpoints
    opentopography_api_key: str | None = None
    pdok_bag_base_url: str = "https://api.pdok.nl/kadaster/bag/ogc/v2"
    pdok_bag_buildings_base_url: str = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items"
    stac_search_url: str | None = None


    # app paths / cache 
    #   Path('/'): Creates a Path object pointing to root directory
    cache_name: str = "http_cache"
    raw_data_dir: Path = Path("data/raw")
    output_data_dir: Path = Path("data/output")


    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore"
        )


settings = Settings()

