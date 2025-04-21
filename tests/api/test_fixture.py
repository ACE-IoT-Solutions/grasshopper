"""Common test fixtures for API tests"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from tempfile import TemporaryDirectory
from fastapi import FastAPI

# Add the path to the Grasshopper directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Grasshopper')))

from grasshopper.api import api_router, compare_rdf_queue


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
        
        # Set app state in both locations used by the code
        app.state.agent_data_path = temp_dir
        app.extra = {"agent_data_path": temp_dir}
        
        # Clear the queue
        while not compare_rdf_queue.empty():
            compare_rdf_queue.get()
        
        # Return the app with TestClient
        with TestClient(app) as client:
            yield client, temp_dir