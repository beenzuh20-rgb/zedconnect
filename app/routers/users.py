"""
Users router for ZedMatch
Handles user profile viewing and editing
"""

import os
import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app import models, config
from app.database import get_db
from app.routers.auth import get_current_user
from PIL import Image

import cloudinary
import cloudinary.uploader

# Configure Cloudinary at module level
cloudinary.config(
    cloud_name=config.CLOUDINARY_CLOUD_NAME,
    api_key=config.CLOUDINARY_API_KEY,
    api_secret=config.CLOUDINARY_API_SECRET,
    secure=True
)

# Create router
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Available interests for users to select
INTERESTS = [
    "Music", "Movies", "Sports", "Travel", "Food", "Reading",
    "Gaming", "Cooking", "Dancing", "Hiking", "Photography",
    "Art", "Technology", "Fashion", "Fitness", "Camping"
]

# Relationship goals options
RELATIONSHIP_GOALS = [
    "dating", "relationship", "marriage", "friendship"
]


def save_profile_picture(file: UploadFile, user_id: int) -> str:
    """Upload profile picture to Cloudinary, return the secure URL"""
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: jpg, jpeg, png, gif, webp")

    # Read file bytes for size check and upload
    file_bytes = file.file.read()
    file_size = len(file_bytes)

    # Check file size
    if file_size > config.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size: 5MB")

    # Validate that it's actually an image by attempting to open it with PIL
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if necessary (for PNG with transparency, etc.)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        # Resize to max 400x400 for profile pictures
        image.thumbnail((400, 400), Image.Resampling.LANCZOS)
        # Save processed image to bytes for upload
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG", quality=85)
        img_bytes.seek(0)
        upload_file_bytes = img_bytes.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    # Upload to Cloudinary
    public_id = f"profile_{user_id}_{uuid.uuid4().hex[:8]}"
    try:
        result = cloudinary.uploader.upload(
            upload_file_bytes,
            public_id=public_id,
            folder="zedconnect_profile_pics",
            overwrite=True,
            resource_type="image",
            transformation=[
                {"width": 400, "height": 400, "crop": "limit", "quality": "auto:good"}
            ]
        )
        return result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image to cloud storage: {str(e)}")


def get_nav_notifications(db: Session, current_user: models.User):
    """Get notification counts for navbar badges"""
    new_matches_count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.type == "new_match",
        models.Notification.is_read == False
    ).count()
    
    unread_messages_count = db.query(models.Message).filter(
        models.Message.receiver_id == current_user.id,
        models.Message.is_read == False,
        models.Message.message_type == "text"
    ).count()
    
    return new_matches_count, unread_messages_count


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display current user's profile page"""
    provinces = models.ZAMBIA_PROVINCES
    csrf_token = request.cookies.get("csrf_token", "")
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>ZedMatch - My Profile</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/matches/browse">Browse</a></li>
                    <li><a href="/matches/mutual">Matches</a>{' <span class="notification-badge">' + str(new_matches_count) + '</span>' if new_matches_count > 0 else ''}</li>
                    <li><a href="/chat/">Chat</a>{' <span class="notification-badge">' + str(unread_messages_count) + '</span>' if unread_messages_count > 0 else ''}</li>
                    <li><a href="/users/profile">Profile</a></li>
                    <li><a href="/auth/logout">Logout</a></li>
                </ul>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="profile-container">
                <h2>My Profile</h2>
                
                <div class="profile-card">
                    <img src="{current_user.profile_picture_url or '/static/default_profile.png'}" alt="Profile Picture" class="profile-pic-large" id="preview-pic">
                    
                    <form action="/users/profile/edit" method="post" class="profile-form" enctype="multipart/form-data">
                        <input type="hidden" name="csrf_token" value="{csrf_token}">
                        <div class="form-group">
                            <label for="profile_pic">Profile Picture</label>
                            <input type="file" id="profile_pic" name="profile_pic" accept="image/jpeg,image/png,image/gif,image/webp" onchange="previewImage(this)">
                            <p class="form-hint">Max size: 5MB. Formats: JPG, PNG, GIF, WebP</p>
                        </div>
                        
                        <div class="form-group">
                            <label for="full_name">Full Name</label>
                            <input type="text" id="full_name" name="full_name" value="{current_user.full_name or ''}">
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="age">Age</label>
                                <input type="number" id="age" name="age" min="18" max="100" value="{current_user.age or ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="gender">Gender</label>
                                <select id="gender" name="gender">
                                    <option value="">Select Gender</option>
                                    <option value="male" {'selected' if current_user.gender == 'male' else ''}>Male</option>
                                    <option value="female" {'selected' if current_user.gender == 'female' else ''}>Female</option>
                                    <option value="other" {'selected' if current_user.gender == 'other' else ''}>Other</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="location">Location (Province)</label>
                            <select id="location" name="location">
                                <option value="">Select Province</option>
                                {''.join([f'<option value="{p}" {'selected' if current_user.location == p else ''}>{p}</option>' for p in provinces])}
                            </select>
                        </div>
                        
<div class="form-group">
                            <label for="bio">Bio</label>
                            <textarea id="bio" name="bio" rows="4">{current_user.bio or ''}</textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Interests (select up to 5)</label>
                            <div class="interests-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.5rem; margin-top: 0.5rem;">
                                {''.join([f'<label style="display: flex; align-items: center; gap: 0.3rem; font-size: 0.9rem; color: var(--text-secondary);"><input type="checkbox" name="interests" value="{interest}" {'checked' if current_user.interests and interest in current_user.interests.split(',') else ''}> {interest}</label>' for interest in INTERESTS])}
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="relationship_goals">Relationship Goals</label>
                            <select id="relationship_goals" name="relationship_goals">
                                <option value="">Select Goals</option>
                                {''.join([f'<option value="{goal}" {'selected' if current_user.relationship_goals == goal else ''}>{goal.title()}</option>' for goal in RELATIONSHIP_GOALS])}
                            </select>
                        </div>
                        
                        <button type="submit" class="btn btn-primary">Save Profile</button>
                    </form>
                    
                    <form action="/users/profile/delete" method="post" onsubmit="return confirm('Are you sure you want to delete your profile? This action cannot be undone.')" style="margin-top: 1rem;">
                        <input type="hidden" name="csrf_token" value="{csrf_token}">
                        <button type="submit" class="btn btn-danger">Delete Profile</button>
                    </form>
                </div>
            </div>
        </main>
        
        <footer class="footer">
            <p>&copy; 2024 ZedMatch - Connecting hearts in Zambia</p>
            <div class="footer-links">
                <a href="/auth/terms">Terms & Conditions</a>
                <a href="/auth/terms#privacy">Privacy Policy</a>
                <a href="/auth/terms#cookie">Cookie Policy</a>
                <a href="/auth/terms#community">Community Guidelines</a>
                <a href="/auth/terms#safety">Safety Guidelines</a>
            </div>
            <div class="footer-terms">
                <h4>Key Terms Summary</h4>
                <p><strong>Terms of Service:</strong> You must be 18+ and provide accurate information. No harassment or fake accounts.</p>
                <p><strong>Privacy:</strong> We collect profile data, location, and messages. Your data is protected.</p>
                <p><strong>Safety:</strong> Meet in public places. Use in-app messaging. Report suspicious behavior.</p>
            </div>
        </footer>
        
        <script>
        function previewImage(input) {{
            if (input.files && input.files[0]) {{
                const reader = new FileReader();
                reader.onload = function(e) {{
                    document.getElementById('preview-pic').src = e.target.result;
                }};
                reader.readAsDataURL(input.files[0]);
            }}
        }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/profile/{user_id}", response_class=HTMLResponse)
async def view_user_profile(
    request: Request, 
    user_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View another user's profile"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>ZedMatch - {user.full_name or 'User Profile'}</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/matches/browse">Browse</a></li>
                    <li><a href="/matches/mutual">Matches</a>{' <span class="notification-badge">' + str(new_matches_count) + '</span>' if new_matches_count > 0 else ''}</li>
                    <li><a href="/chat/">Chat</a>{' <span class="notification-badge">' + str(unread_messages_count) + '</span>' if unread_messages_count > 0 else ''}</li>
                    <li><a href="/users/profile">Profile</a></li>
                    <li><a href="/auth/logout">Logout</a></li>
                </ul>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="profile-container">
                <h2>{user.full_name or 'Anonymous'}</h2>
                
                <div class="profile-card">
                    <img src="{user.profile_picture_url or '/static/default_profile.png'}" alt="Profile Picture" class="profile-pic-large">
                    
<div class="user-info">
                        <p class="age-gender">{user.age or 'N/A'} years old • {user.gender or 'Not specified'}</p>
                        <p class="location">📍 {user.location or 'Zambia'}</p>
                        <p class="bio">{user.bio or 'No bio yet'}</p>
                        {f'<p class="interests" style="margin-top: 0.5rem;"><strong>Interests:</strong> {user.interests}</p>' if user.interests else ''}
                        {f'<p class="goals" style="margin-top: 0.3rem;"><strong>Looking for:</strong> {user.relationship_goals.title() if user.relationship_goals else 'Not specified'}</p>' if user.relationship_goals else ''}
                    </div>
                    
                    <div class="user-actions" style="margin-top: 2rem;">
                        <form action="/matches/like/{user.id}" method="post" style="display:inline;">
                            <button type="submit" class="btn btn-like">❤️ Like</button>
                        </form>
                        <a href="/matches/browse" class="btn btn-secondary">Back to Browse</a>
                        <a href="/report/user/{user.id}" class="btn btn-report" title="Report this user">🚩 Report</a>
                    </div>
                </div>
            </div>
        </main>
        
                <footer class="footer">
            <p>&copy; 2024 ZedMatch - Connecting hearts in Zambia</p>
            <div class="footer-links">
                <a href="/auth/terms">Terms & Conditions</a>
                <a href="/auth/terms#privacy">Privacy Policy</a>
                <a href="/auth/terms#cookie">Cookie Policy</a>
                <a href="/auth/terms#community">Community Guidelines</a>
                <a href="/auth/terms#safety">Safety Guidelines</a>
            </div>
           
        </footer>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/profile/edit")
async def edit_profile(
    request: Request,
    full_name: str = Form(None),
    age: int = Form(None),
    gender: str = Form(None),
    location: str = Form(None),
    bio: str = Form(None),
    interests: list = Form(None),
    relationship_goals: str = Form(None),
    profile_pic: UploadFile = File(None),
    csrf_token: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Handle profile picture upload
    if profile_pic and profile_pic.filename:
        try:
            profile_pic_url = save_profile_picture(profile_pic, current_user.id)
            current_user.profile_picture_url = profile_pic_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to upload profile picture: {str(e)}")
    
    # Update user fields
    if full_name is not None:
        current_user.full_name = full_name
    if age is not None:
        current_user.age = age
    if gender is not None:
        current_user.gender = gender
    if location is not None:
        current_user.location = location
    if bio is not None:
        current_user.bio = bio
    if interests is not None:
        current_user.interests = ",".join(interests) if interests else None
    if relationship_goals is not None:
        current_user.relationship_goals = relationship_goals
    
    db.commit()
    db.refresh(current_user)
    
    return RedirectResponse(url="/users/profile", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/profile/delete")
async def delete_profile(
    request: Request,
    csrf_token: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete current user's profile"""
    # Delete all related data first
    # Delete messages sent and received
    db.query(models.Message).filter(
        (models.Message.sender_id == current_user.id) | (models.Message.receiver_id == current_user.id)
    ).delete(synchronize_session=False)
    
    # Delete likes given and received
    db.query(models.Like).filter(
        (models.Like.liker_id == current_user.id) | (models.Like.liked_id == current_user.id)
    ).delete(synchronize_session=False)
    
    # Delete blocks given and received
    db.query(models.Block).filter(
        (models.Block.blocker_id == current_user.id) | (models.Block.blocked_id == current_user.id)
    ).delete(synchronize_session=False)
    
    # Delete reports made by user
    db.query(models.Report).filter(models.Report.reporter_id == current_user.id).delete(synchronize_session=False)
    
    # Delete reports made against user
    db.query(models.Report).filter(models.Report.reported_id == current_user.id).delete(synchronize_session=False)
    
    # Delete the user
    db.delete(current_user)
    db.commit()
    
    # Clear the session cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response
