"""
Database configuration for ZedConnect
Using SQLAlchemy with PostgreSQL (Neon)
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Ensure SSL is enabled for Neon PostgreSQL
if "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL_SSL = f"{DATABASE_URL}&sslmode=require"
    else:
        DATABASE_URL_SSL = f"{DATABASE_URL}?sslmode=require"
else:
    DATABASE_URL_SSL = DATABASE_URL

# Create engine with PostgreSQL-optimized settings
# pool_pre_ping: verify connections before using them (handles Neon's idle timeout)
# pool_size: default connection pool size
# max_overflow: additional connections beyond pool_size if needed
engine = create_engine(
    DATABASE_URL_SSL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI.
    Yields a database session and ensures it is closed after use.
    Handles connection errors gracefully.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times - uses IF NOT EXISTS internally.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
