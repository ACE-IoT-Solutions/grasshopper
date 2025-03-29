from fastapi import FastAPI, Request, Response, HTTPException, Body
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
import sys
import shutil
import json
import ipaddress
import grequests
import atexit
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
from io import BytesIO
from datetime import datetime
from pathlib import Path

from .api import setup_routes

class Config(object):
    HOST = "127.0.0.1"
    PORT = "5000"
    SERVER_URL = f"{HOST}:{PORT}"

class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    SERVER_URL = None
    ENV = "development"
    DEBUG = True
    # HOST = "127.0.0.1"
    # PORT = "5001"
    # SERVER_URL = f"{HOST}:{PORT}"

def create_app(config_class=None):
    app = FastAPI(
        title="Grasshopper API",
        description="Manage the detection of devices in Bacnet"
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    
    # Store configurations
    app.state.agent_data_path = None
    if config_class == "ProductionConfig":
        app.state.config = ProductionConfig
    else:
        app.state.config = DevelopmentConfig
        
    # Add security headers middleware
    @app.middleware("http")
    async def apply_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline';"
            "style-src 'self' 'unsafe-inline';"
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
    
    # Setup static files (for single-page application)
    dist_path = Path('dist')
    
    # Handle redirects for SPAs
    @app.get("/")
    async def index():
        return FileResponse('dist/index.html')
    
    @app.get("/{path:path}")
    async def catch_all(path: str):
        if path.startswith('api'):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return RedirectResponse(url='/')
    
    # Try to mount static files if the directory exists
    if dist_path.exists():
        app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    # Setup API routes
    setup_routes(app)
    
    return app