"""
Authentication router for ZedConnect
Handles user registration, login, and JWT token management
"""

from datetime import datetime, timedelta
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app import models, config
from app.database import get_db

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# Helper functions
def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current user from cookie"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    if token.startswith("Bearer "):
        token = token[7:].strip()
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


# ====================== ROUTES ======================

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - Register</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedConnect</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/auth/login">Login</a></li>
                    <li><a href="/auth/register">Register</a></li>
                </ul>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Create Your Account</h2>
                <p class="subtitle">Join ZedConnect and find your perfect match in Zambia</p>
                <form action="/auth/register" method="post" class="auth-form">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required placeholder="Enter your email">
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required placeholder="Create a password">
                    </div>
                    <div class="form-group">
                        <label for="full_name">Full Name</label>
                        <input type="text" id="full_name" name="full_name" placeholder="Your full name">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="age">Age</label>
                            <input type="number" id="age" name="age" min="18" max="100" placeholder="25">
                        </div>
                        <div class="form-group">
                            <label for="gender">Gender</label>
                            <select id="gender" name="gender">
                                <option value="">Select Gender</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="location">Location (Province)</label>
                        <select id="location" name="location">
                            <option value="">Select Province</option>
                            <option value="Lusaka">Lusaka</option>
                            <option value="Copperbelt">Copperbelt</option>
                            <option value="Central">Central</option>
                            <option value="Eastern">Eastern</option>
                            <option value="Luapula">Luapula</option>
                            <option value="Northern">Northern</option>
                            <option value="North-Western">North-Western</option>
                            <option value="Southern">Southern</option>
                            <option value="Western">Western</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="bio">Bio</label>
                        <textarea id="bio" name="bio" rows="3" placeholder="Tell us about yourself..."></textarea>
                    </div>
                    <div class="terms-checkbox">
                        <input type="checkbox" id="terms_accepted" name="terms_accepted" required>
                        <label for="terms_accepted">I agree to the <a href="/terms">Terms & Conditions</a>, Privacy Policy, and Community Guidelines. I confirm I am at least 18 years old.</label>
                    </div>
                    <button type="submit" class="btn btn-primary">Register</button>
                </form>
                <p class="auth-link">Already have an account? <a href="/auth/login">Login here</a></p>
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


@router.post("/register")
async def register(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    age: str = Form(None),
    gender: str = Form(None),
    location: str = Form(None),
    bio: str = Form(None),
    profile_picture_url: str = Form("/static/default_profile.png"),
    terms_accepted: str = Form(None),
):
    form_data = await request.form()
    print("=== RAW FORM ===", dict(form_data))

    # Validate terms acceptance
    if not terms_accepted or terms_accepted.lower() != "on":
        raise HTTPException(status_code=400, detail="You must accept the Terms & Conditions to register")

    try:
        age_int = int(age) if age and str(age).strip() else None
    except:
        age_int = None

    try:
        if get_user_by_email(db, email):
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(password)
        new_user = models.User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name or "New User",
            age=age_int,
            gender=gender if gender else None,
            location=location if location else None,
            bio=bio or "",
            profile_picture_url=profile_picture_url
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"✅ SUCCESS: User {new_user.id} created!")

        access_token = create_access_token(data={"user_id": new_user.id})
        response = RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=60*60*24*7, samesite="lax")
        return response
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedConnect - Login</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedConnect</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/auth/login">Login</a></li>
                    <li><a href="/auth/register">Register</a></li>
                </ul>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Welcome Back</h2>
                <p class="subtitle">Login to your ZedConnect account</p>
                <form action="/auth/login" method="post" class="auth-form">
                    <div class="form-group">
                        <label for="username">Email</label>
                        <input type="email" id="username" name="username" required placeholder="Enter your email">
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required placeholder="Enter your password">
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
                <p class="auth-link">Don't have an account? <a href="/auth/register">Register here</a></p>
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


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"user_id": user.id})
    response = RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response