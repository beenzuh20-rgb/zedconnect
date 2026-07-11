"""
Database models for ZedMatch
User, Match, and Message models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Zambia provinces for location choices
ZAMBIA_PROVINCES = [
    "Lusaka", "Copperbelt", "Central", "Eastern", 
    "Luapula", "Northern", "North-Western", "Southern", "Western"
]

class User(Base):
    """
    User model for storing user information
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)  # "male", "female", "other"
    location = Column(String, nullable=True)  # Zambia province
    bio = Column(Text, nullable=True)
    profile_picture_url = Column(String, default="/static/default_profile.png")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Profile verification
    is_verified = Column(Boolean, default=False)  # Email or phone verified
    verification_token = Column(String, nullable=True)  # Token for email verification
    
    # Password reset
    reset_token = Column(String, nullable=True)  # Token for password reset
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)  # Expiration time for reset token
    
    # Interests and relationship goals
    interests = Column(Text, nullable=True)  # Comma-separated interests
    relationship_goals = Column(String, nullable=True)  # "dating", "relationship", "marriage", "friendship"
    
    # Relationships
    likes_given = relationship("Like", foreign_keys="Like.liker_id", back_populates="liker")
    likes_received = relationship("Like", foreign_keys="Like.liked_id", back_populates="liked")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    blocks_given = relationship("Block", foreign_keys="Block.blocker_id", back_populates="blocker")
    blocks_received = relationship("Block", foreign_keys="Block.blocked_id", back_populates="blocked")


class Like(Base):
    """
    Like model for the swipe right functionality
    A user can like another user
    """
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    liker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    liked_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    liker = relationship("User", foreign_keys=[liker_id], back_populates="likes_given")
    liked = relationship("User", foreign_keys=[liked_id], back_populates="likes_received")


class Message(Base):
    """
    Message model for chat between matched users
    Supports text, voice notes, and photo sharing
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=True)  # Text content (optional for media)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    
    # Media support (new columns)
    message_type = Column(String, default="text")  # "text", "voice", "photo"
    media_url = Column(String, nullable=True)  # URL for voice note or photo
    media_duration = Column(Integer, nullable=True)  # Duration in seconds for voice notes
    
    # Legacy columns for backward compatibility (may exist in database)
    image_url = Column(String, nullable=True)  # Old photo URL column
    voice_note_url = Column(String, nullable=True)  # Old voice note URL column
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")


class Block(Base):
    """
    Block model for user blocking functionality
    A user can block another user to prevent messages
    """
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocks_given")
    blocked = relationship("User", foreign_keys=[blocked_id], back_populates="blocks_received")


class Notification(Base):
    """
    Notification model for tracking new matches and unread messages
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # "new_match", "unread_message"
    related_id = Column(Integer, nullable=True)  # user_id or conversation id
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")


class Report(Base):
    """
    Report model for user reporting functionality
    A user can report another user for inappropriate behavior
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, dismissed, action_taken
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported = relationship("User", foreign_keys=[reported_id])