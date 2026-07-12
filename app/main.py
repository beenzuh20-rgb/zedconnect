"""
zedmatch - A Zambia-focused Dating App
Main application entry point
"""

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import get_db, init_db
from app import models, config
from app.routers import auth, users, matches, chat, reports
from app.middleware import add_middlewares
from app.webrtc_signaling import signaling_websocket


# Rate limiter setup
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_GENERAL],
    enabled=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="zedmatch",
    description="A Zambia-focused dating application",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS and other middlewares (security headers, CSRF, request size limits)
add_middlewares(app)

# Mount static files for CSS and images
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(matches.router)
app.include_router(chat.router)
app.include_router(reports.router)

# WebRTC signaling WebSocket endpoint (must be last to avoid path conflicts)
from fastapi import WebSocket

@app.websocket("/ws/signaling")
async def websocket_signaling(websocket: WebSocket):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        await signaling_websocket(websocket, db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page - shows different navigation based on login status"""
    try:
        current_user = await auth.get_current_user(request, db)
        is_logged_in = True
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
    except:
        current_user = None
        is_logged_in = False
        new_matches_count = 0
        unread_messages_count = 0

    from app.security import sanitize_html
    safe_user_name = sanitize_html(current_user.full_name) if current_user else ""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zedmatch - Home</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body style="display: flex; flex-direction: column; min-height: 100vh;">
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">zedmatch</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/matches/browse">Browse</a></li>
                    <li><a href="/matches/mutual">Matches</a>{' <span class="notification-badge">' + str(new_matches_count) + '</span>' if new_matches_count > 0 else ''}</li>
                    <li><a href="/chat/">Chat</a>{' <span class="notification-badge">' + str(unread_messages_count) + '</span>' if unread_messages_count > 0 else ''}</li>
    """
    
    if is_logged_in:
        html_content += """
                    <li><a href="/users/profile">Profile</a></li>
                    <li><a href="/auth/logout">Logout</a></li>
        """
    else:
        html_content += """
                    <li><a href="/auth/login">Login</a></li>
                    <li><a href="/auth/register">Register</a></li>
        """
    
    html_content += f"""
                </ul>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="hero">
                <h1>Welcome to zedmatch ❤️</h1>
                <p class="tagline">Connecting hearts across Zambia - from Lusaka to Copperbelt and beyond!</p>
                
                <div class="hero-buttons">
                    <a href="/auth/register" class="btn btn-primary">Get Started</a>
                    {'' if is_logged_in else '<a href="/auth/login" class="btn btn-secondary">Login</a>'}
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


# Favicon
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


# Terms and Conditions page
@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Display terms and conditions page"""
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse("terms.html", {"request": request})