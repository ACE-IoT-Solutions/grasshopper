"""Tests for file operation endpoints"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Use absolute imports
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grasshopper"))
)
from tests.api.test_fixture import api_client


def test_upload_ttl_file(api_client):
    """Test uploading a TTL file"""
    client, temp_dir = api_client

    # Create test file for upload
    test_content = "test ttl content"
    response = client.post(
        "/operations/ttl",
        files={"file": ("test_upload.ttl", test_content, "application/octet-stream")},
    )

    assert response.status_code == 201
    assert "message" in response.json()
    assert "file_path" in response.json()
    assert response.json()["message"] == "File test_upload.ttl uploaded successfully"

    # Verify file was saved
    uploaded_file_path = os.path.join(temp_dir, "ttl", "test_upload.ttl")
    assert os.path.exists(uploaded_file_path)
    with open(uploaded_file_path, "r") as f:
        assert f.read() == test_content


def test_upload_ttl_file_invalid_extension(api_client):
    """Test uploading a file with invalid extension"""
    client, _ = api_client

    response = client.post(
        "/operations/ttl",
        files={"file": ("test.txt", "test content", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "File type not allowed"}


def test_upload_ttl_file_no_file(api_client):
    """Test uploading without a file"""
    client, _ = api_client

    response = client.post("/operations/ttl")
    assert response.status_code == 422  # FastAPI validation error


def test_download_ttl_file(api_client):
    """Test downloading a TTL file"""
    client, temp_dir = api_client

    # Create test file
    test_content = "test ttl content for download"
    test_filename = "test_download.ttl"
    file_path = os.path.join(temp_dir, "ttl", test_filename)
    with open(file_path, "w") as f:
        f.write(test_content)

    response = client.get(f"/operations/ttl_file/{test_filename}")
    assert response.status_code == 200
    assert response.content.decode() == test_content


def test_download_ttl_file_not_found(api_client):
    """Test downloading a non-existent file"""
    client, _ = api_client
    response = client.get("/operations/ttl_file/nonexistent.ttl")
    assert response.status_code == 404


def test_delete_ttl_file(api_client):
    """Test deleting a TTL file"""
    client, temp_dir = api_client

    # Create test file
    test_filename = "test_delete.ttl"
    file_path = os.path.join(temp_dir, "ttl", test_filename)
    with open(file_path, "w") as f:
        f.write("test content for deletion")

    # Verify file exists
    assert os.path.exists(file_path)

    # Delete the file
    response = client.delete(f"/operations/ttl_file/{test_filename}")
    assert response.status_code == 200
    assert response.json() == {"message": "File deleted successfully"}

    # Verify file no longer exists
    assert not os.path.exists(file_path)


def test_delete_ttl_file_not_found(api_client):
    """Test deleting a non-existent file"""
    client, _ = api_client
    response = client.delete("/operations/ttl_file/nonexistent.ttl")
    assert response.status_code == 404


@patch("grasshopper.api.Graph")
@patch("grasshopper.api.build_networkx_graph")
@patch("grasshopper.api.Network")
@patch("grasshopper.api.pass_networkx_to_pyvis")
def test_get_ttl_network(
    mock_pass_network, mock_network, mock_build_graph, mock_graph, api_client
):
    """Test getting network visualization data from a TTL file"""
    client, temp_dir = api_client

    # Setup mocks
    mock_network_instance = MagicMock()
    mock_network.return_value = mock_network_instance
    mock_network_instance.nodes = [{"id": 1, "label": "test"}]
    mock_network_instance.edges = [{"from": 1, "to": 2}]

    mock_build_graph.return_value = (MagicMock(), {}, {})

    # Create test file
    test_filename = "test_network.ttl"
    file_path = os.path.join(temp_dir, "ttl", test_filename)
    with open(file_path, "w") as f:
        f.write("test ttl content")

    response = client.get(f"/operations/ttl_network/{test_filename}")
    assert response.status_code == 200
    assert "nodes" in response.json()
    assert "edges" in response.json()
    assert response.json()["nodes"] == [{"id": 1, "label": "test"}]
    assert response.json()["edges"] == [{"from": 1, "to": 2}]

    # Verify mocks were called
    mock_graph.return_value.parse.assert_called_once()
    mock_build_graph.assert_called_once()
    mock_network.assert_called_once()
    mock_pass_network.assert_called_once()
