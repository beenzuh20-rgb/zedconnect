"""
Configuration settings for ZedMatch
JWT and other app settings
"""

import os

# JWT Settings - Use environment variable in production, fallback to fixed key for development
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# App settings
APP_NAME = "ZedMatch"
APP_VERSION = "1.0.0"

# Profile picture upload settings
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "profile_pics")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max
