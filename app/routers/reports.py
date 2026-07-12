"""
Reports router for zedconnect
Handles user reporting functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.routers.auth import get_current_user

# Create router
router = APIRouter(
    prefix="/report",
    tags=["reports"]
)

# Common report reasons
REPORT_REASONS = [
    "Fake account",
    "Harassment or bullying",
    "Inappropriate content",
    "Spam or scam",
    "Underage user",
    "Solicitation",
    "Impersonation",
    "Offensive profile",
    "Other"
]


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


@router.get("/user/{user_id}", response_class=HTMLResponse)
async def report_user_page(
    request: Request,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display the report user form"""
    # Don't allow reporting yourself
    if current_user.id == user_id:
        return RedirectResponse(url="/matches/browse", status_code=status.HTTP_303_SEE_OTHER)
    
    reported_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    
    reasons_options = "".join([
        f'<option value="{r}">{r}</option>' for r in REPORT_REASONS
    ])
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zedconnect - Report User</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">zedconnect</a>
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
            <div class="report-container">
                <h2>Report User</h2>
                <p class="subtitle">Reporting <strong>{reported_user.full_name or 'Anonymous'}</strong></p>
                <p class="report-info">Your report is confidential. The reported user will not know who submitted it.</p>
                
                <div class="report-card">
                    <form action="/report/user/{user_id}" method="post" class="report-form">
                        <div class="form-group">
                            <label for="reason">Reason for Report</label>
                            <select id="reason" name="reason" required>
                                <option value="">Select a reason</option>
                                {reasons_options}
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="details">Additional Details</label>
                            <textarea id="details" name="details" rows="5" placeholder="Please provide any additional information that might help our team review this report..." maxlength="1000"></textarea>
                            <p class="form-hint">Max 1000 characters. Include relevant context, but do not share personal contact information.</p>
                        </div>
                        
                        <div class="report-actions">
                            <button type="submit" class="btn btn-danger">Submit Report</button>
                            <a href="javascript:history.back()" class="btn btn-secondary">Cancel</a>
                        </div>
                    </form>
                </div>
                
                <div class="report-guidelines">
                    <h3>Reporting Guidelines</h3>
                    <ul>
                        <li>Reports are reviewed by our moderation team within 24-48 hours.</li>
                        <li>False or malicious reporting may result in action against your account.</li>
                        <li>If you feel you are in immediate danger, please contact local authorities.</li>
                        <li>For urgent safety concerns, please email safety@zedconnect.com</li>
                    </ul>
                </div>
            </div>
        </main>
        
        <footer class="footer">
            <p>&copy; 2024 zedconnect - Connecting hearts in Zambia</p>
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


@router.post("/user/{user_id}")
async def submit_report(
    request: Request,
    user_id: int,
    reason: str = Form(...),
    details: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a report against a user"""
    # Don't allow reporting yourself
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")
    
    reported_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not reason or reason not in REPORT_REASONS:
        raise HTTPException(status_code=400, detail="Please select a valid reason for reporting")
    
    # Create the report
    new_report = models.Report(
        reporter_id=current_user.id,
        reported_id=user_id,
        reason=reason,
        details=details or "",
        status="pending"
    )
    db.add(new_report)
    db.commit()
    
    # Redirect with a success message (using query param for simplicity)
    response = RedirectResponse(
        url="/report/success",
        status_code=status.HTTP_303_SEE_OTHER
    )
    return response


@router.get("/success", response_class=HTMLResponse)
async def report_success(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Display report submission success page"""
    new_matches_count, unread_messages_count = get_nav_notifications(db, current_user)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>zedconnect - Report Submitted</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-container">
                <a href="/" class="logo">zedconnect</a>
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
            <div class="report-success-container">
                <div class="success-card">
                    <div class="success-icon">✅</div>
                    <h2>Report Submitted</h2>
                    <p>Thank you for helping keep zedconnect safe!</p>
                    <p>Our moderation team will review your report within 24-48 hours.</p>
                    <div class="success-actions">
                        <a href="/matches/browse" class="btn btn-primary">Back to Browse</a>
                        <a href="/matches/mutual" class="btn btn-secondary">View Matches</a>
                    </div>
                </div>
            </div>
        </main>
        
        <footer class="footer">
            <p>&copy; 2024 zedconnect - Connecting hearts in Zambia</p>
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