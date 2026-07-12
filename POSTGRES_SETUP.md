# PostgreSQL Setup Guide for zedmatch

This guide will help you switch from SQLite to PostgreSQL for production use.

## Prerequisites

1. **Install PostgreSQL**
   - Download from: https://www.postgresql.org/download/
   - Or use a cloud service like:
     - [Supabase](https://supabase.com/)
     - [Neon.tech](https://neon.tech/)
     - [AWS RDS](https://aws.amazon.com/rds/)
     - [Google Cloud SQL](https://cloud.google.com/sql)

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Option 1: Local PostgreSQL

1. **Create a database**
   ```sql
   -- Connect to PostgreSQL
   psql -U postgres
   
   -- Create database
   CREATE DATABASE zedmatch;
   
   -- Create user (optional)
   CREATE USER zedmatch_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE zedmatch TO zedmatch_user;
   ```

2. **Update .env file**
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost/zedmatch
   ```

### Option 2: Cloud PostgreSQL (Supabase/Neon)

1. Get your connection string from your provider
2. Update .env file
   ```env
   DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
   ```

## Running the Application

1. **Initialize the database** (creates all tables)
   ```bash
   python init_db.py
   ```

2. **Run the application**
   ```bash
   python run.py
   ```

## PostgreSQL Connection String Format

```
postgresql://[username[:password]@][host[:port]][/database][?parameter=value]
```

### Examples:

- **Local with password:**
  ```
  postgresql://postgres:mypassword@localhost/zedmatch
  ```

- **Local without password (trust authentication):**
  ```
  postgresql://postgres@localhost/zedmatch
  ```

- **Cloud with SSL:**
  ```
  postgresql://user:pass@aws.connect.psdb.cloud/zedmatch?sslmode=require
  ```

## Troubleshooting

### Connection refused
- Ensure PostgreSQL is running: `sudo service postgresql start` (Linux) or check Services (Windows)
- Check if PostgreSQL is listening on port 5432

### Authentication failed
- Verify username and password
- Check `pg_hba.conf` for authentication settings

### SSL errors (cloud providers)
- Add `?sslmode=require` to your connection string
- Or use `sslmode=prefer` for local development

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///./zedmatch.db` |
| `SECRET_KEY` | JWT secret key (32+ chars) | `your-secret-key-change-in-production-min-32-chars!` |
| `APP_NAME` | Application name | `zedmatch` |
| `APP_VERSION` | Application version | `1.0.0` |

## Notes

- The app will automatically use SQLite if `DATABASE_URL` is not set or is SQLite
- PostgreSQL connection pooling is configured for production use (pool_size=10, max_overflow=20)
