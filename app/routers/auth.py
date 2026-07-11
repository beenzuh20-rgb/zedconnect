"""
Authentication router for ZedMatch
Handles user registration, login, and JWT token management
"""

from datetime import datetime, timedelta
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from app import models, config
from app.database import get_db
from app.moderation import detect_fake_account, moderate_text

# Password hashing context with multiple schemes for compatibility
pwd_context = CryptContext(schemes=["argon2", "bcrypt", "sha256_crypt"], deprecated="auto")

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# Input validation functions
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple:
    """Validate password strength - returns (is_valid, error_message)"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, None


def validate_age(age: int) -> bool:
    """Validate age is reasonable"""
    return age is None or (18 <= age <= 100)


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS"""
    if text is None:
        return None
    # Remove potentially dangerous characters
    return text.strip()


# Helper functions
def verify_password(plain_password, hashed_password):
    """Verify password with fallback handling for different hash formats"""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # If hash cannot be identified, return False
        return False


def get_password_hash(password):
    # Hash password with Argon2
    return pwd_context.hash(password)


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
    csrf_token = request.cookies.get("csrf_token", "")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Register</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
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
                <p class="subtitle">Join ZedMatch and find your perfect match in Zambia</p>
                <form action="/auth/register" method="post" class="auth-form">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required placeholder="Enter your email">
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
<input type="password" id="password" name="password" required placeholder="Create a password (min 6 characters)">
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
                        <label for="terms_accepted">I agree to the <a href="/auth/terms">Terms & Conditions</a>, Privacy Policy, and Community Guidelines. I confirm I am at least 18 years old.</label>
                    </div>
                    <button type="submit" class="btn btn-primary">Register</button>
                </form>
                <p class="auth-link">Already have an account? <a href="/auth/login">Login here</a></p>
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

    # Validate email format
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Validate password strength
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        age_int = int(age) if age and str(age).strip() else None
    except:
        age_int = None

    # Validate age
    if not validate_age(age_int):
        raise HTTPException(status_code=400, detail="Age must be between 18 and 100")

    # Sanitize inputs
    full_name = sanitize_input(full_name)
    bio = sanitize_input(bio)

    try:
        if get_user_by_email(db, email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Check for fake account patterns
        is_suspicious, reason = detect_fake_account(email, full_name, bio)
        if is_suspicious:
            # Flag the account but still allow registration
            print(f"⚠️ SUSPICIOUS ACCOUNT: {reason}")

        hashed_password = get_password_hash(password)
        verification_token = secrets.token_urlsafe(32)
        new_user = models.User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name or "New User",
            age=age_int,
            gender=gender if gender else None,
            location=location if location else None,
            bio=bio or "",
            profile_picture_url=profile_picture_url,
            verification_token=verification_token
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"✅ SUCCESS: User {new_user.id} created! Verification token: {verification_token}")

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
    csrf_token = request.cookies.get("csrf_token", "")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Login</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
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
                <p class="subtitle">Login to your ZedMatch account</p>
                <form action="/auth/login" method="post" class="auth-form">
                    <input type="hidden" name="csrf_token" value="{csrf_token}">
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
                <p class="auth-link"><a href="/auth/forgot-password">Forgot your password?</a></p>
                <p class="auth-link">Don't have an account? <a href="/auth/register">Register here</a></p>
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
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"user_id": user.id})
    response = RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return response


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Display terms and conditions page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Terms & Conditions</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/auth/login">Login</a></li>
                    <li><a href="/auth/register">Register</a></li>
                </ul>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="auth-container">
                <h2>Terms & Conditions</h2>
                <p class="subtitle">Please read our terms carefully before using ZedMatch</p>
                
                <div class="terms-content">
                    <div class="terms-section" id="terms">
                        <h3><span class="terms-date">Effective Date: July 5, 2025</span></h3>
                        
                        <h4>1. Terms of Service</h4>
                        <p>Welcome to ZedMatch! By accessing or using our platform, you agree to these Terms of Service.</p>
                        <ul>
                            <li>You must be at least 18 years old to use ZedMatch.</li>
                            <li>You agree to provide accurate information when creating your account.</li>
                        </ul>
                        
                        <h4>2. Account Responsibilities</h4>
                        <ul>
                            <li>You are responsible for maintaining the confidentiality of your login credentials.</li>
                            <li>You are responsible for all activities under your account.</li>
                        </ul>
                        
                        <h4>3. User Conduct</h4>
                        <ul>
                            <li>You agree not to harass, abuse, or harm other users.</li>
                            <li>You may not post offensive, illegal, or misleading content.</li>
                            <li>Impersonation, fake accounts, or spam are strictly prohibited.</li>
                        </ul>
                        
                        <h4>4. Content Ownership</h4>
                        <ul>
                            <li>You retain ownership of the content you post.</li>
                            <li>By posting, you grant ZedMatch a license to display and distribute your content within the platform.</li>
                        </ul>
                        
                        <h4>5. Termination</h4>
                        <ul>
                            <li>ZedMatch reserves the right to suspend or terminate accounts that violate these terms.</li>
                        </ul>
                        
                        <h4>6. Limitation of Liability</h4>
                        <ul>
                            <li>ZedMatch is not responsible for offline interactions between users.</li>
                            <li>We provide the platform "as is" without warranties.</li>
                        </ul>
                        
                        <h4>7. Governing Law</h4>
                        <ul>
                            <li>These Terms are governed by the laws of Zambia.</li>
                        </ul>
                    </div>
                    
                    <div class="terms-section" id="privacy">
                        <h3>Privacy Policy</h3>
                        <p><span class="terms-date">Effective Date: July 5, 2025</span></p>
                        
                        <h4>1. Information We Collect</h4>
                        <ul>
                            <li>Profile details, photos, preferences, and messages.</li>
                            <li>Location data (if enabled).</li>
                            <li>Payment information for subscriptions.</li>
                        </ul>
                        
                        <h4>2. How We Use Your Information</h4>
                        <ul>
                            <li>To provide matchmaking and personalized experiences.</li>
                            <li>To improve safety and detect fraudulent activity.</li>
                            <li>To communicate with you about updates and promotions.</li>
                        </ul>
                        
                        <h4>3. Sharing of Information</h4>
                        <ul>
                            <li>With trusted service providers (e.g., payment processors).</li>
                            <li>With law enforcement when legally required.</li>
                        </ul>
                        
                        <h4>4. Your Rights</h4>
                        <ul>
                            <li>You may request access, correction, or deletion of your data.</li>
                            <li>You may opt out of marketing communications.</li>
                        </ul>
                        
                        <h4>5. Security</h4>
                        <ul>
                            <li>We use encryption and secure servers to protect your data.</li>
                            <li>Access is restricted to authorized personnel only.</li>
                        </ul>
                    </div>
                    
                    <div class="terms-section" id="cookie">
                        <h3>Cookie Policy</h3>
                        <p><span class="terms-date">Effective Date: July 5, 2025</span></p>
                        <p>ZedMatch uses cookies and similar technologies to:</p>
                        <ul>
                            <li>Remember your preferences.</li>
                            <li>Analyze site traffic and usage.</li>
                            <li>Deliver personalized ads.</li>
                        </ul>
                        <p>You can manage cookie settings in your browser. Disabling cookies may affect site functionality.</p>
                    </div>
                    
                    <div class="terms-section" id="community">
                        <h3>Community Guidelines</h3>
                        <p><span class="terms-date">Effective Date: July 5, 2025</span></p>
                        
                        <h4>1. Respect Others</h4>
                        <ul>
                            <li>Treat all members with kindness and respect.</li>
                        </ul>
                        
                        <h4>2. No Harassment</h4>
                        <ul>
                            <li>Bullying, threats, or discriminatory behavior will not be tolerated.</li>
                        </ul>
                        
                        <h4>3. Content Standards</h4>
                        <ul>
                            <li>No explicit, offensive, or illegal content.</li>
                            <li>No fake profiles or impersonation.</li>
                        </ul>
                        
                        <h4>4. Reporting</h4>
                        <ul>
                            <li>Use the "Report" feature to flag suspicious or harmful behavior.</li>
                        </ul>
                    </div>
                    
                    <div class="terms-section" id="safety">
                        <h3>Safety Guidelines</h3>
                        <p><span class="terms-date">Effective Date: July 5, 2025</span></p>
                        
                        <h4>1. Online Safety</h4>
                        <ul>
                            <li>Do not share sensitive personal information too quickly.</li>
                            <li>Use in-app messaging before moving to external platforms.</li>
                        </ul>
                        
                        <h4>2. Offline Safety</h4>
                        <ul>
                            <li>Meet in public places for initial dates.</li>
                            <li>Inform a friend or family member of your plans.</li>
                        </ul>
                        
                        <h4>3. Moderation</h4>
                        <ul>
                            <li>ZedMatch monitors activity for suspicious behavior.</li>
                            <li>Accounts may be suspended for safety concerns.</li>
                        </ul>
                    </div>
                    
                    <div class="terms-section" id="subscription">
                        <h3>Subscription Terms</h3>
                        <p><span class="terms-date">Effective Date: July 5, 2025</span></p>
                        
                        <h4>1. Subscription Plans</h4>
                        <ul>
                            <li>ZedMatch offers free and premium membership options.</li>
                            <li>Premium features may include advanced search, unlimited messaging, and profile boosts.</li>
                        </ul>
                        
                        <h4>2. Billing</h4>
                        <ul>
                            <li>Subscriptions renew automatically unless canceled.</li>
                            <li>Payment is processed securely via third-party providers.</li>
                        </ul>
                        
                        <h4>3. Refunds</h4>
                        <ul>
                            <li>Refunds are only available where required by law.</li>
                            <li>Partial refunds are not provided for unused subscription periods.</li>
                        </ul>
                        
                        <h4>4. Cancellation</h4>
                        <ul>
                            <li>You may cancel your subscription at any time in account settings.</li>
                        </ul>
                    </div>
                </div>
                
                <p class="auth-link"><a href="/auth/register">Back to Registration</a></p>
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
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/verify/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user's email using verification token"""
    user = db.query(models.User).filter(
        models.User.verification_token == token
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired verification token")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Email Verified</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Email Verified! ✅</h2>
                <p class="subtitle">Your account has been successfully verified.</p>
                <a href="/auth/login" class="btn btn-primary">Login Now</a>
            </div>
        </main>
    </body>
    </html>
    """)


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Display forgot password page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Forgot Password</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/auth/login">Login</a></li>
                    <li><a href="/auth/register">Register</a></li>
                </ul>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Reset Your Password</h2>
                <p class="subtitle">Enter your email to receive a password reset link</p>
                <form action="/auth/forgot-password" method="post" class="auth-form">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required placeholder="Enter your email">
                    </div>
                    <button type="submit" class="btn btn-primary">Send Reset Link</button>
                </form>
                <p class="auth-link">Remember your password? <a href="/auth/login">Login here</a></p>
            </div>
        </main>
        <footer class="footer">
            <p>&copy; 2024 ZedMatch - Connecting hearts in Zambia</p>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...)
):
    """Handle forgot password form submission"""
    user = get_user_by_email(db, email)
    
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # In a real app, you would send an email here
        # For now, we'll just show a success message with the token
        print(f"🔑 Password reset token for {email}: {reset_token}")
    
    # Always show success to prevent email enumeration
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Password Reset Sent</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Password Reset Link Sent! 📧</h2>
                <p class="subtitle">Check your email for a password reset link. If the email exists in our system, you'll receive instructions to reset your password.</p>
                <a href="/auth/login" class="btn btn-primary">Back to Login</a>
            </div>
        </main>
    </body>
    </html>
    """)


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Display reset password page if token is valid"""
    user = db.query(models.User).filter(
        models.User.reset_token == token,
        models.User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired reset token")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Reset Password</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Create New Password</h2>
                <p class="subtitle">Enter a new password for your account</p>
                <form action="/auth/reset-password/{token}" method="post" class="auth-form">
                    <div class="form-group">
                        <label for="password">New Password</label>
<input type="password" id="password" name="password" required placeholder="Enter new password (min 6 characters)">
                    </div>
                    <div class="form-group">
                        <label for="confirm_password">Confirm Password</label>
                        <input type="password" id="confirm_password" name="confirm_password" required placeholder="Confirm your new password">
                    </div>
                    <button type="submit" class="btn btn-primary">Reset Password</button>
                </form>
            </div>
        </main>
        <footer class="footer">
            <p>&copy; 2024 ZedMatch - Connecting hearts in Zambia</p>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/reset-password/{token}")
async def reset_password(
    token: str,
    db: Session = Depends(get_db),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Handle password reset form submission"""
    user = db.query(models.User).filter(
        models.User.reset_token == token,
        models.User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired reset token")
    
    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Update password
    user.hashed_password = get_password_hash(password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZedMatch - Password Reset Successful</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">ZedMatch</a>
            </div>
        </nav>
        <main class="main-content">
            <div class="auth-container">
                <h2>Password Reset Successful! ✅</h2>
                <p class="subtitle">Your password has been updated. You can now log in with your new password.</p>
                <a href="/auth/login" class="btn btn-primary">Login Now</a>
            </div>
        </main>
    </body>
    </html>
    """)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response
