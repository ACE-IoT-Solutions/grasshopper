"""Tests for more complex API endpoints"""
import os
import sys
import uuid
import pytest
from unittest.mock import patch, MagicMock

# Use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Grasshopper')))
from tests.api.test_fixture import api_client


def test_add_ttl_compare_queue(api_client):
    """Test adding TTL files to comparison queue"""
    client, temp_dir = api_client
    
    # Create test files
    ttl_dir = os.path.join(temp_dir, "ttl")
    file1 = os.path.join(ttl_dir, "file1.ttl")
    file2 = os.path.join(ttl_dir, "file2.ttl")
    
    with open(file1, 'w') as f:
        f.write("test content 1")
    
    with open(file2, 'w') as f:
        f.write("test content 2")
    
    # Add to queue
    response = client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "file1.ttl", "ttl_2": "file2.ttl"}
    )
    
    assert response.status_code == 202
    assert response.json() == {"message": "File accepted"}
    
    # Check queue
    response = client.get("/operations/ttl_compare_queue")
    assert response.status_code == 200
    assert "queue" in response.json()
    assert len(response.json()["queue"]) == 1
    assert response.json()["queue"][0]["ttl_1"] == "file1.ttl"
    assert response.json()["queue"][0]["ttl_2"] == "file2.ttl"


def test_add_ttl_compare_queue_file_not_found(api_client):
    """Test adding non-existent files to comparison queue"""
    client, _ = api_client
    
    response = client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "nonexistent1.ttl", "ttl_2": "nonexistent2.ttl"}
    )
    
    assert response.status_code == 404


def test_add_ttl_compare_queue_duplicate(api_client):
    """Test adding duplicate comparison to queue"""
    client, temp_dir = api_client
    
    # Create test files
    ttl_dir = os.path.join(temp_dir, "ttl")
    file1 = os.path.join(ttl_dir, "file1.ttl")
    file2 = os.path.join(ttl_dir, "file2.ttl")
    
    with open(file1, 'w') as f:
        f.write("test content 1")
    
    with open(file2, 'w') as f:
        f.write("test content 2")
    
    # Add to queue
    client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "file1.ttl", "ttl_2": "file2.ttl"}
    )
    
    # Try to add again
    response = client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "file1.ttl", "ttl_2": "file2.ttl"}
    )
    
    assert response.status_code == 400
    
    # Try reverse order
    response = client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "file2.ttl", "ttl_2": "file1.ttl"}
    )
    
    assert response.status_code == 400


def test_delete_ttl_compare_queue_task(api_client):
    """Test removing a task from comparison queue"""
    client, temp_dir = api_client
    
    # Create test files
    ttl_dir = os.path.join(temp_dir, "ttl")
    file1 = os.path.join(ttl_dir, "file1.ttl")
    file2 = os.path.join(ttl_dir, "file2.ttl")
    
    with open(file1, 'w') as f:
        f.write("test content 1")
    
    with open(file2, 'w') as f:
        f.write("test content 2")
    
    # Add to queue
    client.post(
        "/operations/ttl_compare_queue",
        json={"ttl_1": "file1.ttl", "ttl_2": "file2.ttl"}
    )
    
    # Get task ID
    response = client.get("/operations/ttl_compare_queue")
    task_id = response.json()["queue"][0]["id"]
    
    # Delete task
    response = client.delete(f"/operations/ttl_compare_queue_tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify queue is empty
    response = client.get("/operations/ttl_compare_queue")
    assert len(response.json()["queue"]) == 0


def test_delete_nonexistent_task(api_client):
    """Test removing a non-existent task from comparison queue"""
    client, _ = api_client
    
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/operations/ttl_compare_queue_tasks/{fake_id}")
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_delete_compare_file(api_client):
    """Test deleting a comparison file"""
    client, temp_dir = api_client
    
    # Create a test file to delete
    compare_dir = os.path.join(temp_dir, "compare")
    test_file = "test_compare.ttl"
    file_path = os.path.join(compare_dir, test_file)
    with open(file_path, 'w') as f:
        f.write("test content for deletion")
    
    # Verify file exists
    assert os.path.exists(file_path)
    
    # Delete the file
    response = client.delete(f"/operations/ttl_compare/{test_file}")
    assert response.status_code == 200
    assert response.json() == {"message": f"File {test_file} deleted successfully"}
    
    # Verify file no longer exists
    assert not os.path.exists(file_path)


def test_delete_network_config_file(api_client):
    """Test deleting a network config file"""
    client, temp_dir = api_client
    
    # Create a test file to delete
    network_config_dir = os.path.join(temp_dir, "network_config")
    test_file = "test_config.json"
    file_path = os.path.join(network_config_dir, test_file)
    with open(file_path, 'w') as f:
        f.write('{"test": "content"}')
    
    # Verify file exists
    assert os.path.exists(file_path)
    
    # Delete the file
    response = client.delete(f"/operations/network_config/{test_file}")
    assert response.status_code == 200
    assert response.json() == {"message": "File deleted successfully"}
    
    # Verify file no longer exists
    assert not os.path.exists(file_path)


@patch('grasshopper.api.StringIO')
@patch('grasshopper.api.Graph')
@patch('grasshopper.api.build_networkx_graph')
def test_export_csv(mock_build_graph, mock_graph, mock_stringio, api_client):
    """Test exporting a TTL file to CSV"""
    client, temp_dir = api_client
    
    # Setup mocks
    mock_nx_graph = MagicMock()
    mock_node_data = {
        "device1": {
            "type": "Device",
            "device-address": "1",
            "network-id": ["network1"],
            "vendor-id": "vendor/1"
        },
        "router1": {
            "type": "Router",
            "device-address": "2",
            "subnet": "192.168.1.0/24",
            "vendor-id": "vendor/2"
        }
    }
    mock_edge_data = {}
    
    mock_build_graph.return_value = (mock_nx_graph, mock_node_data, mock_edge_data)
    mock_nx_graph.edges.return_value = []
    mock_nx_graph.nodes = ["device1", "router1"]
    
    # Create test file
    ttl_dir = os.path.join(temp_dir, "ttl")
    file1 = os.path.join(ttl_dir, "export_test.ttl")
    
    with open(file1, 'w') as f:
        f.write("test content")
    
    # Mock StringIO to capture CSV output
    mock_stringio_instance = MagicMock()
    mock_stringio.return_value = mock_stringio_instance
    mock_stringio_instance.getvalue.return_value = "CSV content"
    
    response = client.get("/operations/csv_export/export_test.ttl")
    
    # Check response headers
    assert response.status_code == 200
    assert "Content-Disposition" in response.headers
    assert "export_test.ttl.csv" in response.headers["Content-Disposition"]
    assert response.headers["Content-Type"] == "text/csv"