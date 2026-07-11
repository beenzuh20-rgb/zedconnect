"""
Database fix script for ZedMatch
Adds missing columns to messages table
Run this with: python fix_db.py
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

# Missing columns for messages table
MISSING_COLUMNS = [
    ("message_type", "VARCHAR DEFAULT 'text'"),
    ("media_url", "VARCHAR"),
    ("media_duration", "INTEGER"),
    ("image_url", "VARCHAR"),  # Legacy column
    ("voice_note_url", "VARCHAR"),  # Legacy column
]

# Columns to alter (change from NOT NULL to NULL)
ALTER_COLUMNS = [
    ("content", "ALTER TABLE messages ALTER COLUMN content DROP NOT NULL"),
]

def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    result = conn.execute(
        text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table AND column_name = :col
        """),
        {"table": table_name, "col": column_name}
    )
    return result.fetchone() is not None

def run_migration():
    """Add missing columns to the messages table and fix constraints"""
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Needed for DDL statements
        
        # Check existing columns in messages table
        result = conn.execute(
            text("""
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'messages'
                ORDER BY ordinal_position
            """)
        )
        existing = {row[0]: row[1] for row in result}
        logger.info(f"Existing columns in messages table: {', '.join(sorted(existing.keys()))}")
        
        # Add missing columns
        added = 0
        for col_name, col_type in MISSING_COLUMNS:
            if col_name not in existing:
                logger.info(f"Adding column: {col_name} ({col_type})")
                conn.execute(
                    text(f'ALTER TABLE messages ADD COLUMN {col_name} {col_type}')
                )
                added += 1
            else:
                logger.info(f"Column already exists: {col_name}")
        
        if added > 0:
            logger.info(f"✅ Successfully added {added} missing column(s)")
        else:
            logger.info("✅ All columns already exist - no migration needed")
        
        # Alter columns to allow NULL if needed
        altered = 0
        for col_name, alter_sql in ALTER_COLUMNS:
            if col_name in existing and existing[col_name] == 'NO':
                logger.info(f"Altering column: {col_name} to allow NULL")
                conn.execute(text(alter_sql))
                altered += 1
            else:
                logger.info(f"Column {col_name} already allows NULL or doesn't exist")
        
        if altered > 0:
            logger.info(f"✅ Successfully altered {altered} column(s)")
        
        # Verify the final state
        result = conn.execute(
            text("""
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'messages'
                ORDER BY ordinal_position
            """)
        )
        final_columns = [f"{row[0]} (nullable={row[1]}, type={row[2]})" for row in result]
        logger.info(f"Final columns in messages table:\n  " + "\n  ".join(final_columns))

if __name__ == "__main__":
    run_migration()
    logger.info("Database fix complete!")