"""
Middleware configuration for ZedConnect
CORS and other middlewares
"""

from fastapi.middleware.cors import CORSMiddleware

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