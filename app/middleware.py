"""
Middleware configuration for zedmatch
CORS, CSRF protection, security headers, rate limiting, and request size limits
"""

import os
import secrets
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app import config

# CSRF token storage (in production, use Redis or database)
csrf_tokens = {}

def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token exists in store"""
    return token in csrf_tokens


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Content Security Policy - mitigates XSS
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://res.cloudinary.com *; "
            "media-src 'self' blob: data:; "
            "connect-src 'self' ws: wss: https://res.cloudinary.com; "
            "frame-ancestors 'none';"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (HTTP Strict Transport Security) - only when HTTPS is enforced
        if config.ENFORCE_HTTPS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Prevent IE from executing downloaded files in site's context
        response.headers["X-Download-Options"] = "noopen"

        # Permissions policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), accelerometer=()"
        )

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for form submissions"""

    # Paths that don't require CSRF validation
    SKIP_PATHS = {"/auth/logout"}

    # Safe methods that don't need CSRF
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)

        # For safe methods (GET, HEAD, etc.)
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF token in cookie for HTML responses
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                token = generate_csrf_token()
                csrf_tokens[token] = True
                response.set_cookie(
                    key="csrf_token",
                    value=token,
                    httponly=False,  # Must be accessible to JavaScript for AJAX
                    samesite="strict",
                    secure=config.SESSION_COOKIE_SECURE
                )
            return response

        # For state-changing methods (POST, PUT, DELETE, PATCH)
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            # Skip CSRF for explicitly allowed paths
            if request.url.path in self.SKIP_PATHS:
                return await call_next(request)

            # Get token from header first (AJAX), then cookie (form fallback), then form field
            csrf_token = (
                request.headers.get("X-CSRF-Token") or
                request.cookies.get("csrf_token", "")
            )

            # For form submissions, also check form body
            if not csrf_token and request.method == "POST":
                try:
                    form = await request.form()
                    csrf_token = form.get("csrf_token", "")
                except Exception:
                    pass

            if not csrf_token or not validate_csrf_token(csrf_token):
                return Response(
                    content="CSRF validation failed. Please refresh the page and try again.",
                    status_code=403
                )

        response = await call_next(request)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""

    async def dispatch(self, request: Request, call_next):
        # Check content-length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > config.MAX_REQUEST_BODY_SIZE:
                    return Response(
                        content="Request body too large",
                        status_code=413
                    )
            except ValueError:
                pass

        # For multipart uploads, check after reading
        response = await call_next(request)
        return response


def add_middlewares(app):
    """
    Add all necessary middlewares to the FastAPI app
    """
    # CORS middleware with specific origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Content-Type", "Authorization", "X-CSRF-Token",
            "X-Requested-With", "Accept", "Origin"
        ],
    )

    # Request size limit middleware (applied early)
    app.add_middleware(RequestSizeLimitMiddleware)

    # CSRF protection middleware
    app.add_middleware(CSRFMiddleware)

    # Security headers middleware (applied last so it wraps all responses)
    app.add_middleware(SecurityHeadersMiddleware)