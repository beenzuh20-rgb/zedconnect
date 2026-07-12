"""
Configuration settings for zedmatch
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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))  # 15 minutes short-lived
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days for refresh

# App settings
APP_NAME = "zedmatch"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

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
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_CHAT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp3", ".ogg", ".wav", ".webm"}
ALLOWED_CHAT_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm"
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max
MAX_CHAT_FILE_SIZE = 10 * 1024 * 1024  # 10MB max
DEFAULT_PROFILE_PIC = "/static/default_profile.png"

# Rate limiting settings
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "3/hour")
RATE_LIMIT_MESSAGE = os.getenv("RATE_LIMIT_MESSAGE", "30/minute")
RATE_LIMIT_GENERAL = os.getenv("RATE_LIMIT_GENERAL", "100/minute")

# Request limits
MAX_REQUEST_BODY_SIZE = int(os.getenv("MAX_REQUEST_BODY_SIZE", str(10 * 1024 * 1024)))  # 10MB
MAX_CONTENT_LENGTH = 5000  # Max chars for text fields

# CORS - specify allowed origins in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")

# Security
ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "").lower() in ("true", "1", "yes")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
