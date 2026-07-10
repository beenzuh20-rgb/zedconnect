"""
Chat router for ZedConnect
Handles messaging between matched users
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
import os

# Create router
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


@router.get("/", response_class=HTMLResponse)
async def chat_list(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display list of chat conversations"""
    # Get all users that current user has matched with
    # (users they've liked who also liked them back)
    liked_user_ids = [like.liked_id for like in current_user.likes_given]
    
    # Find mutual matches
    mutual_match_ids = []
    for liked_id in liked_user_ids:
        mutual_like = db.query(models.Like).filter(
            models.Like.liker_id == liked_id,
            models.Like.liked_id == current_user.id
        ).first()
        if mutual_like:
            mutual_match_ids.append(liked_id)
    
    # Get mutual match user objects
    matches = db.query(models.User).filter(
        models.User.id.in_(mutual_match_ids)
    ).all()
    
    # Build conversation list HTML
    conversations = ""
    for match in matches:
        conversations += f"""
        <a href="/chat/with/{match.id}" class="conversation-item">
            <img src="{match.profile_picture_url or '/static/default_profile.png'}" alt="Profile" class="conversation-pic">
            <div class="conversation-info">
                <h3>{match.full_name or 'Anonymous'}</h3>
                <p>Tap to start chatting</p>
            </div>
        </a>
        """
    
    if not matches:
        conversations = """
        <div class="no-conversations">
            <p>No conversations yet! Match with people to start chatting.</p>
            <a href="/matches/browse" class="btn btn-primary">Find Matches</a>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - Messages</title>
        <link rel="stylesheet" href="/static/css/style.css">
        <script src="/static/js/webrtc.js"></script>
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
            <div class="chat-list-container">
                <h2>Messages</h2>
                
                <div class="conversations-list">
                    {conversations}
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
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/with/{user_id}", response_class=HTMLResponse)
async def chat_with_user(
    request: Request,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with a specific matched user"""
    # Check if user exists
    other_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if users are matched (mutual like)
    my_like = db.query(models.Like).filter(
        models.Like.liker_id == current_user.id,
        models.Like.liked_id == user_id
    ).first()
    
    their_like = db.query(models.Like).filter(
        models.Like.liker_id == user_id,
        models.Like.liked_id == current_user.id
    ).first()
    
    if not (my_like and their_like):
        raise HTTPException(status_code=403, detail="You can only chat with mutual matches")
    
    # Get messages between users
    messages = db.query(models.Message).filter(
        ((models.Message.sender_id == current_user.id) & (models.Message.receiver_id == user_id)) |
        ((models.Message.sender_id == user_id) & (models.Message.receiver_id == current_user.id))
    ).order_by(models.Message.created_at).all()
    
    # Build messages HTML - separate text and image messages
    messages_html = ""
    for message in messages:
        is_sent = "sent" if message.sender_id == current_user.id else "received"
        time_str = message.created_at.strftime('%H:%M') if message.created_at else ''
        
        if message.image_url:
            # Photo message - use "Shared photo" card style
            messages_html += f"""
            <div class="message {is_sent} message-photo">
                <div class="message-content">
                    <div class="photo-card">
                        <img src="{message.image_url}" alt="Shared photo" class="photo-message-img">
                        <div class="photo-label">📷 Shared photo</div>
                    </div>
                </div>
                <div class="message-time">
                    {time_str}
                </div>
            </div>
            """
        else:
            # Text message - clean bubble with escaped text
            messages_html += f"""
            <div class="message {is_sent}">
                <div class="message-content">
                    {message.content}
                </div>
                <div class="message-time">
                    {time_str}
                </div>
            </div>
            """
    
    if not messages:
        messages_html = """
        <div class="no-messages">
            <p>No messages yet. Say hello!</p>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - Chat with {other_user.full_name or 'User'}</title>
        <link rel="stylesheet" href="/static/css/style.css">
        <script src="/static/js/webrtc.js"></script>
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
            <div class="chat-container">
                <div class="chat-header">
                    <a href="/chat/" class="back-link">← Back</a>
                    <h2>Chat with {other_user.full_name or 'Anonymous'}</h2>
                    <div class="chat-call-buttons">
                        <button onclick="callManager.startCall({other_user.id}, '{other_user.full_name or 'Anonymous'}', 'video')" class="btn-video-call">📹 Video Call</button>
                        <button onclick="callManager.startCall({other_user.id}, '{other_user.full_name or 'Anonymous'}', 'audio')" class="btn-audio-call">📞 Audio Call</button>
                    </div>
                </div>
                
                <div class="messages-container">
                    {messages_html}
                </div>
                
                <form action="/chat/send/{other_user.id}" method="post" class="message-form">
                    <input type="text" name="content" placeholder="Type your message..." required autocomplete="off">
                    <button type="submit">Send</button>
                </form>
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
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/send/{user_id}")
async def send_message(
    user_id: int,
    content: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a matched user"""
    # Check if user exists
    other_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if users are matched
    my_like = db.query(models.Like).filter(
        models.Like.liker_id == current_user.id,
        models.Like.liked_id == user_id
    ).first()
    
    their_like = db.query(models.Like).filter(
        models.Like.liker_id == user_id,
        models.Like.liked_id == current_user.id
    ).first()
    
    if not (my_like and their_like):
        raise HTTPException(status_code=403, detail="You can only chat with mutual matches")
    
    # Create message
    new_message = models.Message(
        sender_id=current_user.id,
        receiver_id=user_id,
        content=content
    )
    db.add(new_message)
    db.commit()
    
    return RedirectResponse(url=f"/chat/with/{user_id}", status_code=status.HTTP_303_SEE_OTHER)