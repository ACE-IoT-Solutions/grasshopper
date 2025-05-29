"""FastAPI application for Grasshopper"""

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api import (
    api_router,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")
INDEX_PATH = os.path.join(DIST_DIR, "index.html")


class Config:
    HOST = "127.0.0.1"
    PORT = 5000


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    ENV = "development"
    DEBUG = True


def create_app(config_class=None):
    """
    Create and configure a FastAPI application for the Grasshopper service.

    This function sets up a FastAPI application with:
    - API router for backend operations
    - CORS middleware for cross-origin requests
    - Configuration settings based on the provided config class
    - Static file serving for frontend assets
    - Frontend routes for the single-page application
    - Security headers middleware

    Args:
        config_class (str, optional): The name of the configuration class to use.
            Must be a class defined in this module. Defaults to None, which will
            use DevelopmentConfig.

    Returns:
        FastAPI: The configured FastAPI application
    """
    app = FastAPI(
        title="Grasshopper API",
        description="Manage the detection of devices in Bacnet",
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    # Apply CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Set config based on provided class
    config_class_obj = globals().get(config_class)
    if not config_class_obj:
        app.extra["config"] = DevelopmentConfig()
        print(f"Config class '{config_class}' not found.")
    else:
        app.extra["config"] = config_class_obj()

    # Static files setup
    try:
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    except Exception:
        pass

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """
        Serve the index HTML file.

        This route handler returns the main HTML file for the single-page application.

        Returns:
            HTMLResponse: The contents of the index.html file

        Raises:
            HTTPException: If the index file cannot be found
        """
        try:
            with open(INDEX_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Index file not found")

    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        """
        Catch-all route for the frontend single-page application.

        This route handler redirects all non-API requests to the root path,
        allowing the SPA to handle client-side routing.

        Args:
            path (str): The requested path

        Returns:
            RedirectResponse: A redirect to the root path

        Raises:
            HTTPException: If the path starts with 'api' but doesn't match any API routes
        """
        if path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return RedirectResponse("/")

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """
        Middleware to add security headers to all responses.

        This middleware adds various security headers to HTTP responses to improve
        the security posture of the application, including:
        - CORS headers
        - Content Security Policy
        - X-Frame-Options
        - X-XSS-Protection
        - And other security-related headers

        Args:
            request (Request): The incoming HTTP request
            call_next (Callable): The next middleware or route handler in the chain

        Returns:
            Response: The HTTP response with added security headers
        """
        response = await call_next(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css 'unsafe-inline'; "
            "img-src 'self' https://fastapi.tiangolo.com/img/favicon.png data:; "
            "connect-src 'self' 'unsafe-inline'; "
            "worker-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response

    return app
