
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Load, validate and expose application settings."""

    # Application 
    app_name: str = "Building Exposure API"
    app_env: str = "development"    # identifies whether the application is running in development, testing, or production.
    debug: bool = True             # controls development-related behavior 

    # Database
    postgres_user: str
    postgres_password: str
    postgres_host: str 
    postgres_port: int 
    postgres_db: str

    # External services
    pdok_bag_base_url: str  # it automatically reads the PDOK_BAG_BASE_URL environment variable and assigns its value to the pdok_bag_base_url attribute.
    stac_search_url: str    # it automatically reads the STAC_SEARCH_URL environment variable and assigns its value to the stac_search_url attribute.
    opentopography_api_key: str | None = None

    # Storage 
    raw_data_dir: Path = Path("data/raw")       # Path('/'): Creates a Path object pointing to root directory 
    output_data_dir: Path = Path("data/output")

    # Cache 
    cache_name: str 


    # Settings class is designed to read from environment variables and .env files. 
    # The model_config attribute specifies that the .env file should be used for configuration, and any extra settings not defined in the class will be ignored. 
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    @property   # This decorator allows you to access this method as if it were an attribute, without needing to call it like a regular method.
    def database_url(self) -> URL:
        """Construct the database URL from the individual components."""
        return str(
            URL.create(
                drivername="postgresql+psycopg",  # PostgreSQL driver for SQLAlchemy. It allows SQLAlchemy to communicate with PostgreSQL databases.
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
            )
        )

    @property
    def pdok_bag_buildings_base_url(self) -> str:
        """Construct the PDOK BAG buildings base URL from the base URL."""
        return f"{self.pdok_bag_base_url}/collections/pand/items"


# reads the .env file and creates a Settings object with the values from the .env file and environment variables.
# Settings() reads the configuration and validates it. If any required settings are missing or have the wrong type, it will raise an error.
settings = Settings()

