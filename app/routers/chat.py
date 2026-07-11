"""
Chat router for ZedMatch
Handles messaging between matched users with voice notes, photo sharing, read receipts, and blocking
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.routers.auth import get_current_user
import os
import uuid
from datetime import datetime
from pathlib import Path

# Create router
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# Media upload directory
MEDIA_DIR = Path("app/static/chat_media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def is_user_blocked(db: Session, user_id: int, other_user_id: int) -> bool:
    """Check if a user is blocked by another user"""
    block = db.query(models.Block).filter(
        models.Block.blocker_id == user_id,
        models.Block.blocked_id == other_user_id
    ).first()
    return block is not None


def is_mutual_match(db: Session, user1_id: int, user2_id: int) -> bool:
    """Check if two users are mutual matches"""
    my_like = db.query(models.Like).filter(
        models.Like.liker_id == user1_id,
        models.Like.liked_id == user2_id
    ).first()
    
    their_like = db.query(models.Like).filter(
        models.Like.liker_id == user2_id,
        models.Like.liked_id == user1_id
    ).first()
    
    return my_like is not None and their_like is not None


@router.get("/", response_class=HTMLResponse)
async def chat_list(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display list of chat conversations"""
    # Get all users that current user has matched with
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
        # Get last message
        last_message = db.query(models.Message).filter(
            ((models.Message.sender_id == current_user.id) & (models.Message.receiver_id == match.id)) |
            ((models.Message.sender_id == match.id) & (models.Message.receiver_id == current_user.id))
        ).order_by(models.Message.created_at.desc()).first()
        
        # Get unread count
        unread_count = db.query(models.Message).filter(
            models.Message.sender_id == match.id,
            models.Message.receiver_id == current_user.id,
            models.Message.is_read == False
        ).count()
        
        last_msg_text = ""
        if last_message:
            # Handle both new message_type and old columns (image_url, voice_note_url)
            msg_type = last_message.message_type or ""
            if msg_type == "voice" or last_message.voice_note_url:
                last_msg_text = "🎤 Voice note"
            elif msg_type == "photo" or last_message.image_url:
                last_msg_text = "📷 Photo"
            else:
                last_msg_text = last_message.content or ""
        
        conversations += f"""
        <a href="/chat/with/{match.id}" class="conversation-item">
            <img src="{match.profile_picture_url or '/static/default_profile.png'}" alt="Profile" class="conversation-pic">
            <div class="conversation-info">
                <h3>{match.full_name or 'Anonymous'}</h3>
                <p>{last_msg_text or 'Tap to start chatting'}</p>
            </div>
            {'<span class="unread-badge">' + str(unread_count) + '</span>' if unread_count > 0 else ''}
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
    if not is_mutual_match(db, current_user.id, user_id):
        raise HTTPException(status_code=403, detail="You can only chat with mutual matches")
    
    # Check if current user is blocked
    if is_user_blocked(db, user_id, current_user.id):
        raise HTTPException(status_code=403, detail="You have been blocked by this user")
    
    # Get messages between users
    messages = db.query(models.Message).filter(
        ((models.Message.sender_id == current_user.id) & (models.Message.receiver_id == user_id)) |
        ((models.Message.sender_id == user_id) & (models.Message.receiver_id == current_user.id))
    ).order_by(models.Message.created_at).all()
    
    # Mark messages as read
    for message in messages:
        if message.receiver_id == current_user.id and not message.is_read:
            message.is_read = True
    db.commit()
    
    # Build messages HTML
    messages_html = ""
    for message in messages:
        is_sent = "sent" if message.sender_id == current_user.id else "received"
        
        # Handle both new message_type and old columns (image_url, voice_note_url)
        msg_type = message.message_type or ""
        if msg_type == "voice" or message.voice_note_url:
            # Use voice_note_url for old messages, media_url for new ones
            media_url = message.media_url or message.voice_note_url or ""
            messages_html += f"""
            <div class="message {is_sent}">
                <div class="message-content">
                    <div class="voice-message">
                        <audio controls>
                            <source src="{media_url}" type="audio/webm">
                            Your browser does not support the audio element.
                        </audio>
                        <span class="voice-duration">{message.media_duration or 0}s</span>
                    </div>
                </div>
                <div class="message-time">
                    {message.created_at.strftime('%H:%M') if message.created_at else ''}
                    {'<span class="read-receipt">✓✓</span>' if message.is_read else '<span class="read-receipt">✓</span>'}
                </div>
            </div>
            """
        elif msg_type == "photo" or message.image_url:
            # Use image_url for old messages, media_url for new ones
            media_url = message.media_url or message.image_url or ""
            messages_html += f"""
            <div class="message {is_sent}">
                <div class="message-content">
                    <div class="photo-message">
                        <img src="{media_url}" alt="Shared photo" onclick="window.open('{media_url}', '_blank')">
                    </div>
                </div>
                <div class="message-time">
                    {message.created_at.strftime('%H:%M') if message.created_at else ''}
                    {'<span class="read-receipt">✓✓</span>' if message.is_read else '<span class="read-receipt">✓</span>'}
                </div>
            </div>
            """
        else:
            messages_html += f"""
            <div class="message {is_sent}">
                <div class="message-content">
                    {message.content}
                </div>
                <div class="message-time">
                    {message.created_at.strftime('%H:%M') if message.created_at else ''}
                    {'<span class="read-receipt">✓✓</span>' if message.is_read else '<span class="read-receipt">✓</span>'}
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
                    <button onclick="blockUser({other_user.id}, '{other_user.full_name or 'Anonymous'}')" class="btn-block-user" title="Block User">🚫</button>
                </div>
                
                <div class="messages-container">
                    {messages_html}
                </div>
                
                <form action="/chat/send/{other_user.id}" method="post" class="message-form" enctype="multipart/form-data">
                    <div class="message-input-container">
                        <input type="text" name="content" placeholder="Type your message..." autocomplete="off" id="message-input">
                        <label for="photo-upload" class="btn-photo-upload" title="Send Photo">📷</label>
                        <input type="file" id="photo-upload" name="photo" accept="image/*" style="display: none;">
                        <button type="button" class="btn-voice-record" title="Record Voice Note" onclick="startVoiceRecording()">🎤</button>
                    </div>
                    <button type="submit" class="btn btn-primary" style="padding: 12px 20px; border-radius: 24px;">📤 Send</button>
                </form>
                
                <div id="voice-recording-ui" class="voice-recording-ui" style="display: none;">
                    <div class="recording-indicator">
                        <span class="recording-dot"></span>
                        <span>Recording... <span id="recording-timer">0:00</span></span>
                    </div>
                    <div class="recording-actions">
                        <button type="button" class="btn-stop-recording" onclick="stopVoiceRecording()">Stop</button>
                        <button type="button" class="btn-cancel-recording" onclick="cancelVoiceRecording()">Cancel</button>
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
        
        <script>
        let mediaRecorder;
        let audioChunks = [];
        let recordingTimer;
        let seconds = 0;
        
        async function startVoiceRecording() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = event => {{
                    audioChunks.push(event.data);
                }};
                
                mediaRecorder.onstop = async () => {{
                    const audioBlob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                    const formData = new FormData();
                    formData.append('voice', audioBlob, 'voice.webm');
                    
                    const response = await fetch('/chat/send/{other_user.id}', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    if (response.ok) {{
                        window.location.reload();
                    }}
                }};
                
                mediaRecorder.start();
                document.getElementById('voice-recording-ui').style.display = 'block';
                document.querySelector('.message-input-container').style.display = 'none';
                
                seconds = 0;
                recordingTimer = setInterval(() => {{
                    seconds++;
                    const mins = Math.floor(seconds / 60);
                    const secs = seconds % 60;
                    document.getElementById('recording-timer').textContent = mins + ':' + (secs < 10 ? '0' : '') + secs;
                }}, 1000);
            }} catch (err) {{
                alert('Could not access microphone. Please check permissions.');
            }}
        }}
        
        function stopVoiceRecording() {{
            if (mediaRecorder && mediaRecorder.state === 'recording') {{
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                clearInterval(recordingTimer);
            }}
        }}
        
        function cancelVoiceRecording() {{
            if (mediaRecorder && mediaRecorder.state === 'recording') {{
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                clearInterval(recordingTimer);
            }}
            document.getElementById('voice-recording-ui').style.display = 'none';
            document.querySelector('.message-input-container').style.display = 'flex';
        }}
        
        async function blockUser(userId, userName) {{
            if (confirm('Are you sure you want to block ' + userName + '? You will not be able to message each other.')) {{
                const response = await fetch('/chat/block/' + userId, {{
                    method: 'POST'
                }});
                if (response.ok) {{
                    alert('User blocked successfully');
                    window.location.href = '/chat/';
                }}
            }}
        }}
        
        // Handle photo upload
        document.getElementById('photo-upload').addEventListener('change', async function(e) {{
            const file = e.target.files[0];
            if (file) {{
                const formData = new FormData();
                formData.append('photo', file);
                
                const response = await fetch('/chat/send/{other_user.id}', {{
                    method: 'POST',
                    body: formData
                }});
                
                if (response.ok) {{
                    window.location.reload();
                }}
            }}
        }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/send/{user_id}")
async def send_message(
    user_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a matched user (text, voice, or photo)"""
    # Check if user exists
    other_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if users are matched
    if not is_mutual_match(db, current_user.id, user_id):
        raise HTTPException(status_code=403, detail="You can only chat with mutual matches")
    
    # Check if current user is blocked
    if is_user_blocked(db, user_id, current_user.id):
        raise HTTPException(status_code=403, detail="You have been blocked by this user")
    
    # Check if other user is blocked by current user
    if is_user_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=403, detail="You have blocked this user")
    
    form = await request.form()
    
    # Handle voice note
    if 'voice' in form:
        voice_file = form['voice']
        if voice_file:
            # Save voice file
            file_ext = '.webm'
            file_name = f"voice_{uuid.uuid4()}{file_ext}"
            file_path = MEDIA_DIR / file_name
            
            # Read and save the file
            content = await voice_file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Get duration from form or estimate
            duration = int(form.get('duration', 0))
            
            new_message = models.Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                message_type="voice",
                media_url=f"/static/chat_media/{file_name}",
                media_duration=duration
            )
            db.add(new_message)
            db.commit()
            return RedirectResponse(url=f"/chat/with/{user_id}", status_code=status.HTTP_303_SEE_OTHER)
    
    # Handle photo
    if 'photo' in form:
        photo_file = form['photo']
        if photo_file:
            # Save photo file
            file_ext = os.path.splitext(photo_file.filename)[1] or '.jpg'
            file_name = f"photo_{uuid.uuid4()}{file_ext}"
            file_path = MEDIA_DIR / file_name
            
            # Read and save the file
            content = await photo_file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            new_message = models.Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                message_type="photo",
                media_url=f"/static/chat_media/{file_name}"
            )
            db.add(new_message)
            db.commit()
            return RedirectResponse(url=f"/chat/with/{user_id}", status_code=status.HTTP_303_SEE_OTHER)
    
    # Handle text message
    content = form.get('content', '')
    if content:
        new_message = models.Message(
            sender_id=current_user.id,
            receiver_id=user_id,
            content=content,
            message_type="text"
        )
        db.add(new_message)
        db.commit()
    
    return RedirectResponse(url=f"/chat/with/{user_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/block/{user_id}")
async def block_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user from messaging"""
    # Check if user exists
    other_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already blocked
    existing_block = db.query(models.Block).filter(
        models.Block.blocker_id == current_user.id,
        models.Block.blocked_id == user_id
    ).first()
    
    if not existing_block:
        new_block = models.Block(
            blocker_id=current_user.id,
            blocked_id=user_id
        )
        db.add(new_block)
        db.commit()
    
    return JSONResponse(content={"success": True, "message": "User blocked successfully"})


@router.post("/unblock/{user_id}")
async def unblock_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    block = db.query(models.Block).filter(
        models.Block.blocker_id == current_user.id,
        models.Block.blocked_id == user_id
    ).first()
    
    if block:
        db.delete(block)
        db.commit()
    
    return JSONResponse(content={"success": True, "message": "User unblocked successfully"})


@router.get("/blocked", response_class=HTMLResponse)
async def blocked_users(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display list of blocked users"""
    blocked = db.query(models.Block).filter(
        models.Block.blocker_id == current_user.id
    ).all()
    
    blocked_users_list = ""
    for block in blocked:
        blocked_user = db.query(models.User).filter(models.User.id == block.blocked_id).first()
        if blocked_user:
            blocked_users_list += f"""
            <div class="blocked-user-item">
                <img src="{blocked_user.profile_picture_url or '/static/default_profile.png'}" alt="Profile" class="blocked-user-pic">
                <div class="blocked-user-info">
                    <h3>{blocked_user.full_name or 'Anonymous'}</h3>
                    <p>Blocked on {block.created_at.strftime('%Y-%m-%d')}</p>
                </div>
                <button onclick="unblockUser({blocked_user.id})" class="btn-unblock">Unblock</button>
            </div>
            """
    
    if not blocked:
        blocked_users_list = """
        <div class="no-blocked">
            <p>You haven't blocked any users.</p>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - Blocked Users</title>
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
            <div class="blocked-container">
                <h2>Blocked Users</h2>
                <a href="/chat/" class="back-link">← Back to Messages</a>
                
                <div class="blocked-users-list">
                    {blocked_users_list}
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
        
        <script>
        async function unblockUser(userId) {{
            const response = await fetch('/chat/unblock/' + userId, {{
                method: 'POST'
            }});
            if (response.ok) {{
                window.location.reload();
            }}
        }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)