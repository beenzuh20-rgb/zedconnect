"""
Security utilities for zedconnect
Token blacklisting, password validation, input sanitization, rate limiting setup
"""

import re
import uuid
import html
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from jose import jwt
from app import models, config


def generate_jti() -> str:
    """Generate a unique JWT ID for token tracking"""
    return uuid.uuid4().hex


def create_access_token(data: dict) -> Tuple[str, str]:
    """Create a JWT access token with jti claim. Returns (token, jti)"""
    to_encode = data.copy()
    jti = generate_jti()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": jti, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt, jti


def create_refresh_token(data: dict) -> Tuple[str, str]:
    """Create a refresh token. Returns (token, jti)"""
    to_encode = data.copy()
    jti = generate_jti()
    expire = datetime.utcnow() + timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": jti, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt, jti


def revoke_token(db: Session, token_jti: str, expires_at: datetime):
    """Add a token to the blacklist"""
    blacklisted = models.TokenBlacklist(
        token_jti=token_jti,
        expires_at=expires_at
    )
    db.add(blacklisted)
    db.commit()


def is_token_revoked(db: Session, token_jti: str) -> bool:
    """Check if a token has been revoked"""
    return db.query(models.TokenBlacklist).filter(
        models.TokenBlacklist.token_jti == token_jti
    ).first() is not None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, None


def sanitize_html(text: Optional[str]) -> str:
    """Escape HTML characters to prevent XSS"""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_age(age: Optional[int]) -> bool:
    """Validate age is reasonable"""
    return age is None or (18 <= age <= 100)


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """Sanitize user input - strip whitespace"""
    if text is None:
        return None
    return text.strip()


def cleanup_expired_tokens(db: Session):
    """Remove expired tokens from the blacklist (call periodically)"""
    db.query(models.TokenBlacklist).filter(
        models.TokenBlacklist.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    db.commit()