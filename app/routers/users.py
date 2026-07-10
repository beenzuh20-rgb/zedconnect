"""
Users router for ZedConnect
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


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request, 
    current_user: models.User = Depends(get_current_user)
):
    """Display current user's profile page"""
    provinces = models.ZAMBIA_PROVINCES
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - My Profile</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedConnect</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/matches/browse">Browse</a></li>
                    <li><a href="/matches/mutual">Matches</a></li>
                    <li><a href="/chat/">Chat</a></li>
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
                        
                        <button type="submit" class="btn btn-primary">Save Profile</button>
                    </form>
                </div>
            </div>
        </main>
        
                <footer class="footer">
            <p>&copy; 2024 ZedConnect - Connecting hearts in Zambia</p>
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
    db: Session = Depends(get_db)
):
    """View another user's profile"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - {user.full_name or 'User Profile'}</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedConnect</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/matches/browse">Browse</a></li>
                    <li><a href="/matches/mutual">Matches</a></li>
                    <li><a href="/chat/">Chat</a></li>
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
            <p>&copy; 2024 ZedConnect - Connecting hearts in Zambia</p>
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
    profile_pic: UploadFile = File(None),
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
    
    db.commit()
    db.refresh(current_user)
    
    return RedirectResponse(url="/users/profile", status_code=status.HTTP_303_SEE_OTHER)