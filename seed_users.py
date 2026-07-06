"""
Seed script to create fake user profiles for ZamConnect
"""

from app.database import SessionLocal, engine
from app import models
from app.routers.auth import get_password_hash
import random

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Sample data
first_names_male = ["Chileshe", "Mwape", "Nkombo", "Sikota", "Chibwana", "Mwansa", "Kunda", "Chisanga", "Banda", "Mwelwa"]
first_names_female = ["Mwape", "Chisanga", "Nkombo", "Sikota", "Chileshe", "Banda", "Kunda", "Chibwana", "Mwansa", "Chisenga"]
last_names = ["Phiri", "Banda", "Chiluba", "Mwanza", "Kasonde", "Chitala", "Mumba", "Chibwana", "Sikota", "Nkombo"]

locations = ["Lusaka", "Copperbelt", "Central", "Eastern", "Luapula", "Northern", "North-Western", "Southern", "Western"]
genders = ["male", "female"]

bios = [
    "Love exploring the beauty of Zambia, from Victoria Falls to the Luangwa Valley!",
    "Passionate about Zambian music, especially traditional drums and kalindula.",
    "Looking for someone to share nshima and relish with!",
    "Love dancing to Zambian hits and trying out traditional dishes.",
    "Weekend warrior - hiking in the hills and enjoying village life.",
    "Tech enthusiast from Lusaka, building the future of Zambia.",
    "Foodie who loves trying different Zambian cuisines.",
    "Adventure seeker, always looking for the next travel destination in Zambia.",
]

def create_fake_users():
    db = SessionLocal()
    
    # Delete existing users
    db.query(models.User).delete()
    db.commit()
    
    # Special profile you requested
    special_user = models.User(
        email="nkombo.sikota@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Nkombo Sikota",
        age=30,
        gender="female",
        location="Western",
        bio="Looking for someone to share nshima and relish with!",
        profile_picture_url="https://images.unsplash.com/photo-1517841905240-4722065025b7?q=80&w=2070"  # Romantic African woman
    )
    db.add(special_user)
    
    # Create 19 more fake users
    for i in range(19):
        gender = random.choice(genders)
        if gender == "male":
            first_name = random.choice(first_names_male)
        else:
            first_name = random.choice(first_names_female)
        
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        # Use pravatar.cc for reliable profile pictures
        # This service provides random avatar images that always load
        user = models.User(
            email=f"user{i+1}@example.com",
            hashed_password=get_password_hash("password123"),
            full_name=full_name,
            age=random.randint(18, 35),
            gender=gender,
            location=random.choice(locations),
            bio=random.choice(bios),
            profile_picture_url=f"https://i.pravatar.cc/300?img={i+1}"
        )
        db.add(user)
    
    db.commit()
    db.close()
    print("✅ Created 20 fake user profiles! (Including Nkombo Sikota)")

if __name__ == "__main__":
    create_fake_users()