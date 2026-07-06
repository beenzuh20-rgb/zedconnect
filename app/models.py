"""
Database models for ZedConnect
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
    
    # Relationships
    likes_given = relationship("Like", foreign_keys="Like.liker_id", back_populates="liker")
    likes_received = relationship("Like", foreign_keys="Like.liked_id", back_populates="liked")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")


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
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")


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
