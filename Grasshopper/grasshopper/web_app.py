"""FastAPI application for Grasshopper"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os


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
    """Create FastAPI app with configuration"""
    app = FastAPI(
        title="Grasshopper API",
        description="Manage the detection of devices in Bacnet",
    )
    
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
        app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    except Exception:
        pass
    
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the index HTML file"""
        try:
            with open(os.path.join("dist", "index.html"), "r") as f:
                return f.read()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Index file not found")
    
    @app.get("/{path:path}")
    async def catch_all(path: str):
        """Catch-all route for frontend SPA"""
        if path.startswith('api'):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return RedirectResponse("/")
    
    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to responses"""
        response = await call_next(request)
        
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
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