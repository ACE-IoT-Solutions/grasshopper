"""A simple test to verify our test fixture is working"""

import inspect
import os
import sys
from tempfile import TemporaryDirectory

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the path to the Grasshopper directory
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grasshopper"))
)

from grasshopper.api import api_router
from grasshopper.web_app import create_app


@pytest.fixture
def test_client():
    """Create a test instance of the FastAPI application"""
    # Create a fresh FastAPI instance for testing
    app = FastAPI()

    # Debug information
    print(f"API Router routes: {[route.path for route in api_router.routes]}")

    # Mount the router directly
    app.include_router(api_router)

    # Debug information - print all routes
    print(f"App routes: {[route.path for route in app.routes]}")

    # Create a test temporary directory for agent_data_path
    with TemporaryDirectory() as temp_dir:
        # Setup test directories
        os.makedirs(os.path.join(temp_dir, "ttl"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "compare"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "network_config"), exist_ok=True)

        # Set app state
        app.extra = {"agent_data_path": temp_dir}

        # Return the app with TestClient
        with TestClient(app) as client:
            yield client


def test_hello_endpoint(test_client):
    """Test the hello endpoint"""
    response = test_client.get("/operations/hello")
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content}")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}
