import os

from sqlalchemy import create_engine   # Create a database connection. 
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings # access the settings object from the config module to get the database URL and other configuration values.

# This module creates the database ENGINE and a SESSION factory.
engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# declarative base class provided by SQLAlchemy.
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception: # This helps when something fails mid-transaction.
        db.rollback()
        raise
    finally:
        db.close()

