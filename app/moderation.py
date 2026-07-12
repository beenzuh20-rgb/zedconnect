"""
Content moderation and fake account detection for zedmatch
"""

import re
from typing import List, Tuple

# Banned words/phrases for content moderation
BANNED_WORDS = [
    "spam", "scam", "fake", "bot", "illegal", "drugs", "weed",
    # Add more as needed
]

# Suspicious patterns for fake account detection
SUSPICIOUS_PATTERNS = [
    r"^[a-z]{10,}",  # Random lowercase strings
    r"^[0-9]{5,}",   # Mostly numbers
    r"(.)\1{4,}",    # Repeated characters
]

def moderate_text(text: str) -> Tuple[bool, str]:
    """
    Check if text contains banned content
    Returns (is_safe, reason)
    """
    if not text:
        return True, None
    
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word in text_lower:
            return False, f"Content contains banned word: {word}"
    
    return True, None


def detect_fake_account(email: str, full_name: str, bio: str) -> Tuple[bool, str]:
    """
    Detect potential fake accounts based on patterns
    Returns (is_suspicious, reason)
    """
    # Check email patterns
    if email:
        email_local = email.split("@")[0] if "@" in email else email
        for pattern in SUSPICIOUS_PATTERNS:
            if re.match(pattern, email_local):
                return True, "Suspicious email pattern detected"
    
    # Check name patterns
    if full_name:
        for pattern in SUSPICIOUS_PATTERNS:
            if re.match(pattern, full_name):
                return True, "Suspicious name pattern detected"
    
    # Check bio patterns
    if bio:
        is_safe, reason = moderate_text(bio)
        if not is_safe:
            return True, reason
    
    return False, None


def get_moderation_flags(user) -> List[str]:
    """
    Get list of moderation flags for a user
    """
    flags = []
    
    # Check if user has suspicious patterns
    is_suspicious, reason = detect_fake_account(
        user.email, 
        user.full_name, 
        user.bio
    )
    if is_suspicious:
        flags.append(f"Suspicious: {reason}")
    
    # Check if user is not verified
    if not user.is_verified:
        flags.append("Not verified")
    
    return flags