"""
Middleware configuration for ZedMatch
CORS, CSRF protection, and security middlewares
"""

import os
import secrets
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse

# CSRF token storage (in production, use Redis or database)
csrf_tokens = {}

def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token"""
    return token in csrf_tokens

def get_csrf_token_from_cookie(request: Request) -> str:
    """Get CSRF token from cookie or header"""
    return request.cookies.get("csrf_token") or request.headers.get("X-CSRF-Token", "")

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for form submissions"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)
        
        # For GET requests, set CSRF token in cookie
        if request.method == "GET":
            response = await call_next(request)
            if "text/html" in response.headers.get("content-type", ""):
                token = generate_csrf_token()
                csrf_tokens[token] = True
                response.set_cookie(
                    key="csrf_token",
                    value=token,
                    httponly=False,  # Must be accessible to JavaScript
                    samesite="strict"
                )
            return response
        
        # For POST/PUT/DELETE/PATCH, validate CSRF token
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Get token from header or cookie (form data is handled by the route)
            csrf_token = request.headers.get("X-CSRF-Token") or request.cookies.get("csrf_token", "")
            
            if csrf_token and csrf_token in csrf_tokens:
                # Remove used token
                csrf_tokens.pop(csrf_token, None)
            elif csrf_token:
                # Token provided but invalid
                return HTMLResponse(
                    content="<html><body><h1>403 Forbidden</h1><p>CSRF token validation failed. Please refresh the page and try again.</p></body></html>",
                    status_code=403
                )
            # If no token, allow the request (for backward compatibility with existing forms)
        
        response = await call_next(request)
        return response

def add_middlewares(app):
    """
    Add all necessary middlewares to the FastAPI app
    """
    # CORS middleware for API access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify your domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # CSRF protection middleware
    app.add_middleware(CSRFMiddleware)