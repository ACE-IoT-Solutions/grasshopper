"""Tests for Grasshopper agent web server and API setup"""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Import fixtures
from tests.agent.conftest import mock_agent


def test_configure_server_setup_calls(mock_agent):
    """Test that configure_server_setup makes the expected calls"""
    # Call the method
    mock_agent.configure_server_setup()
    
    # Verify that the method was called
    mock_agent.configure_server_setup.assert_called_once()


def test_setup_routes_calls(mock_agent):
    """Test that setup_routes makes the expected calls"""
    # Create a mock FastAPI app
    mock_app = MagicMock()
    
    # Call the method
    mock_agent.setup_routes(mock_app)
    
    # Verify that the method was called with the right arguments
    mock_agent.setup_routes.assert_called_once_with(mock_app)


def test_start_server_calls(mock_agent):
    """Test that _start_server makes the expected calls"""
    # Set up test parameters
    host = "127.0.0.1"
    port = 8888
    
    # Call the method
    result = mock_agent._start_server(host, port)
    
    # Verify that the method was called with the right arguments
    mock_agent._start_server.assert_called_once_with(host, port)
    
    # Verify the result
    assert result == 0


def test_start_server_with_ssl_calls(mock_agent):
    """Test that _start_server with SSL makes the expected calls"""
    # Set up test parameters
    host = "127.0.0.1"
    port = 8888
    ssl_context = {
        "certfile": "/path/to/cert",
        "keyfile": "/path/to/key"
    }
    
    # Call the method
    result = mock_agent._start_server(host, port, ssl_context)
    
    # Verify that the method was called with the right arguments
    mock_agent._start_server.assert_called_once_with(host, port, ssl_context)
    
    # Verify the result
    assert result == 0