"""Configuration file for pytest tests"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from tempfile import TemporaryDirectory
from fastapi import FastAPI
from multiprocessing import Queue

from Grasshopper.grasshopper.api import api_router


@pytest.fixture
def api_client():
    """Create a test instance of the FastAPI application with API router mounted directly"""
    app = FastAPI(title="Grasshopper API Test")
    
    # Mount the router directly, preserving its /operations prefix
    app.include_router(api_router)
    
    # Create a test temporary directory for agent_data_path
    with TemporaryDirectory() as temp_dir:
        # Setup test directories
        os.makedirs(os.path.join(temp_dir, "ttl"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "compare"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "network_config"), exist_ok=True)
        
        # Set up the task queues in app state
        app.state.task_queue = Queue()
        app.state.processing_task_queue = Queue()
        
        # Set app state in both locations used by the code
        app.extra = {"agent_data_path": temp_dir}
        
        # Return the app with TestClient
        with TestClient(app) as client:
            yield client, temp_dir