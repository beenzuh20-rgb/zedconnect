"""
Database initialization script for zedconnect
Creates all tables in PostgreSQL database
"""

from app.database import engine
from app import models

def init_db():
    """Create all database tables"""
    print("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()