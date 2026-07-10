"""
Configuration settings for ZedConnect
JWT and other app settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (override any existing env vars)
load_dotenv(override=True)

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days

# App settings
APP_NAME = "ZedConnect"
APP_VERSION = "1.0.0"

# Database settings
# Neon PostgreSQL connection string format:
# postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/database_name?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it to your Neon PostgreSQL connection string."
    )

# Cloudinary settings
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    raise RuntimeError(
        "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET "
        "environment variables must be set. "
        "Sign up at https://cloudinary.com to get your free credentials."
    )

# Profile picture upload settings
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "profile_pics")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max
DEFAULT_PROFILE_PIC = "/static/default_profile.png"
