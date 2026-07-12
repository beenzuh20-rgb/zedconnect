"""
Matches router for zedmatch
Handles like system and mutual matches
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.routers.auth import get_current_user
from datetime import datetime

# Create router
router = APIRouter(
    prefix="/matches",
    tags=["matches"]
)


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


@router.get("/browse", response_class=HTMLResponse)
async def browse_users(
    request: Request,
    current_user: models.User = Depends(get_current_user),   # ← Fixed
    db: Session = Depends(get_db)
):
    """Browse other users to like (swipe right)"""
    # Get users that current user hasn't liked yet
    liked_user_ids = [like.liked_id for like in current_user.likes_given]
    liked_user_ids.append(current_user.id)  # Exclude self
    
    users = db.query(models.User).filter(
        ~models.User.id.in_(liked_user_ids)
    ).all()
    
    # Get notification counts
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    
    # Build user cards HTML
    user_cards = ""
    for user in users:
        user_cards += f"""
        <div class="user-card">
            <img src="{user.profile_picture_url or '/static/default_profile.png'}" alt="Profile Picture" class="profile-pic">
            <div class="user-info">
                <h3>{user.full_name or 'Anonymous'}</h3>
                <p class="age-gender">{user.age or 'N/A'} years old • {user.gender or 'Not specified'}</p>
                <p class="location">📍 {user.location or 'Zambia'}</p>
                <p class="bio">{user.bio or 'No bio yet'}</p>
            </div>
            <div class="user-actions">
                <a href="/users/profile/{user.id}" class="btn btn-secondary">View Profile</a>
                <form action="/matches/like/{user.id}" method="post" style="display:inline;">
                    <button type="submit" class="btn btn-like">❤️ Like</button>
                </form>
                <a href="/report/user/{user.id}" class="btn btn-report" title="Report this user">🚩 Report</a>
            </div>
        </div>
        """
    
    if not users:
        user_cards = """
        <div class="no-users">
            <p>No more users to browse! Check back later or update your preferences.</p>
            <a href="/matches/mutual" class="btn btn-primary">View Your Matches</a>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zedmatch - Browse Users</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">zedmatch</a>
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
            <div class="browse-container">
                <h2>Find Your Match</h2>
                <p class="subtitle">Discover people in Zambia</p>
                
                <div class="user-cards">
                    {user_cards}
                </div>
            </div>
        </main>
        
               <footer class="footer">
            <p>&copy; 2024 zedmatch - Connecting hearts in Zambia</p>
            <div class="footer-links">
                <a href="/auth/terms">Terms & Conditions</a>
                <a href="/auth/terms#privacy">Privacy Policy</a>
                <a href="/auth/terms#cookie">Cookie Policy</a>
                <a href="/auth/terms#community">Community Guidelines</a>
                <a href="/auth/terms#safety">Safety Guidelines</a>
            </div>
           
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/like/{user_id}")
async def like_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),   # ← Fixed
    db: Session = Depends(get_db)
):
    """Like a user (swipe right)"""
    user_to_like = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_like:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_like = db.query(models.Like).filter(
        models.Like.liker_id == current_user.id,
        models.Like.liked_id == user_id
    ).first()
    
    if existing_like:
        return RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)
    
    new_like = models.Like(liker_id=current_user.id, liked_id=user_id)
    db.add(new_like)
    db.commit()
    
    mutual_like = db.query(models.Like).filter(
        models.Like.liker_id == user_id,
        models.Like.liked_id == current_user.id
    ).first()
    
    if mutual_like:
        new_match_notification = models.Notification(
            user_id=user_id,
            type="new_match",
            related_id=current_user.id
        )
        db.add(new_match_notification)
        db.commit()
        return RedirectResponse(url="/matches/mutual", status_code=status.HTTP_303_SEE_OTHER)
    
    return RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/mutual", response_class=HTMLResponse)
async def mutual_matches(
    request: Request,
    current_user: models.User = Depends(get_current_user),   # ← Fixed
    db: Session = Depends(get_db)
):
    """View mutual matches"""
    # Mark match notifications as read
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.type == "new_match",
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    # Get notification counts
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    
    # ... (your original code)
    users_who_liked_me = db.query(models.Like).filter(
        models.Like.liked_id == current_user.id
    ).all()
    
    mutual_match_ids = []
    for like in users_who_liked_me:
        my_like = db.query(models.Like).filter(
            models.Like.liker_id == current_user.id,
            models.Like.liked_id == like.liker_id
        ).first()
        if my_like:
            mutual_match_ids.append(like.liker_id)
    
    mutual_matches = db.query(models.User).filter(
        models.User.id.in_(mutual_match_ids)
    ).all()
    
    match_cards = ""
    for match in mutual_matches:
        match_cards += f"""
        <div class="match-card">
            <img src="{match.profile_picture_url or '/static/default_profile.png'}" alt="Profile" class="match-pic">
            <h3>{match.full_name or 'Anonymous'}</h3>
            <p>{match.age or 'N/A'} years old • {match.location or 'Zambia'}</p>
            <a href="/chat/with/{match.id}" class="btn btn-primary">Send Message</a>
        </div>
        """
    
    if not mutual_matches:
        match_cards = """
        <div class="no-matches">
            <p>No matches yet! Keep browsing and liking people.</p>
            <a href="/matches/browse" class="btn btn-primary">Browse Users</a>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zedmatch - My Matches</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">zedmatch</a>
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
            <div class="matches-container">
                <h2>Your Matches</h2>
                <p class="subtitle">People who liked you back!</p>
                
                <div class="matches-grid">
                    {match_cards}
                </div>
            </div>
        </main>
        
                <footer class="footer">
            <p>&copy; 2024 zedmatch - Connecting hearts in Zambia</p>
            <div class="footer-links">
                <a href="/auth/terms">Terms & Conditions</a>
                <a href="/auth/terms#privacy">Privacy Policy</a>
                <a href="/auth/terms#cookie">Cookie Policy</a>
                <a href="/auth/terms#community">Community Guidelines</a>
                <a href="/auth/terms#safety">Safety Guidelines</a>
            </div>
            
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)