"""
Configuration settings for ZedConnect
JWT and other app settings
"""

import secrets
import os

# JWT Settings
SECRET_KEY = secrets.token_urlsafe(32)  # Generate a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# App settings
APP_NAME = "ZedConnect"
APP_VERSION = "1.0.0"

# Profile picture upload settings
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "profile_pics")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max