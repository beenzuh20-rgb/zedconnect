"""
Run script for ZedMatch
Start the FastAPI development server

For PostgreSQL, set the DATABASE_URL environment variable:
    Windows: set DATABASE_URL=postgresql://user:password@localhost/zedmatch
    Linux/Mac: export DATABASE_URL=postgresql://user:password@localhost/zedmatch

For HTTPS, set the SSL_CERTFILE and SSL_KEYFILE environment variables:
    Windows: set SSL_CERTFILE=path/to/cert.pem && set SSL_KEYFILE=path/to/key.pem
    Linux/Mac: export SSL_CERTFILE=path/to/cert.pem && export SSL_KEYFILE=path/to/key.pem

Then run: pip install -r requirements.txt
"""

import os
import uvicorn

if __name__ == "__main__":
    # HTTPS configuration
    ssl_certfile = os.getenv("SSL_CERTFILE")
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    
    if ssl_certfile and ssl_keyfile:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=7777,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile
        )
    else:
        # Development mode (HTTP)
        uvicorn.run("app.main:app", host="0.0.0.0", port=7777)
