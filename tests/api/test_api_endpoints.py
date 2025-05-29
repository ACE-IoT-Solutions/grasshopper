"""Basic endpoint tests for the FastAPI application"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import sys


def test_hello_endpoint(api_client):
    """Test the hello endpoint"""
    client, _ = api_client
    response = client.get("/operations/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_get_ttl_list_empty(api_client):
    """Test getting TTL list when directory is empty"""
    client, _ = api_client
    response = client.get("/operations/ttl")
    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_get_ttl_list_with_files(api_client):
    """Test getting TTL list when files exist"""
    client, temp_dir = api_client

    # Create test files
    ttl_dir = os.path.join(temp_dir, "ttl")
    test_files = ["test1.ttl", "test2.ttl", "notttl.txt"]
    for file_name in test_files:
        with open(os.path.join(ttl_dir, file_name), "w") as f:
            f.write("test content")

    response = client.get("/operations/ttl")
    assert response.status_code == 200
    assert set(response.json()["data"]) == {"test1.ttl", "test2.ttl"}
