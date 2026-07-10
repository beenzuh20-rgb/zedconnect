"""
Database migration script to add missing columns to the users table.
Run this with: python migrate_db.py
"""

import logging
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure SSL is enabled for Neon PostgreSQL
if "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL_SSL = f"{DATABASE_URL}&sslmode=require"
    else:
        DATABASE_URL_SSL = f"{DATABASE_URL}?sslmode=require"
else:
    DATABASE_URL_SSL = DATABASE_URL

engine = create_engine(DATABASE_URL_SSL, pool_pre_ping=True)

# Columns that need to be added
MISSING_COLUMNS = [
    ("is_verified", "BOOLEAN DEFAULT FALSE"),
    ("verification_token", "VARCHAR"),
    ("reset_token", "VARCHAR"),
    ("reset_token_expires", "TIMESTAMP WITH TIME ZONE"),
    ("interests", "TEXT"),
    ("relationship_goals", "VARCHAR"),
]

def column_exists(conn, column_name):
    """Check if a column exists in the users table"""
    result = conn.execute(
        text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = :col
        """),
        {"col": column_name}
    )
    return result.fetchone() is not None

def run_migration():
    """Add missing columns to the users table"""
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Needed for DDL statements in some PostgreSQL setups
        
        # First, check existing columns
        result = conn.execute(
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
        )
        existing = {row[0] for row in result}
        logger.info(f"Existing columns: {', '.join(sorted(existing))}")
        
        # Add missing columns
        added = 0
        for col_name, col_type in MISSING_COLUMNS:
            if not column_exists(conn, col_name):
                logger.info(f"Adding column: {col_name} ({col_type})")
                conn.execute(
                    text(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}')
                )
                added += 1
            else:
                logger.info(f"Column already exists: {col_name}")
        
        if added > 0:
            logger.info(f"✅ Successfully added {added} missing column(s)")
        else:
            logger.info("✅ All columns already exist - no migration needed")
        
        # Verify the final state
        result = conn.execute(
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
        )
        final_columns = [f"{row[0]} ({row[1]})" for row in result]
        logger.info(f"Final columns:\n  " + "\n  ".join(final_columns))

if __name__ == "__main__":
    run_migration()
    logger.info("Migration complete!")