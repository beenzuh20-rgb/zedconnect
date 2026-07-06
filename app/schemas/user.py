"""
User schema for ZedConnect
Pydantic models for user data validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional

# Zambia provinces
ZAMBIA_PROVINCES = [
    "Lusaka", "Copperbelt", "Central", "Eastern", 
    "Luapula", "Northern", "North-Western", "Southern", "Western"
]

# Gender choices
GENDER_CHOICES = ["male", "female", "other"]


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = "/static/default_profile.png"


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: int
    email: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None

    class Config:
        orm_mode = True