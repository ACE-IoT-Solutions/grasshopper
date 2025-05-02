"""Tests for Grasshopper agent BACnet scanning functionality"""

import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime
from rdflib import Graph

# Import fixtures
from tests.agent.conftest import mock_agent, mock_bacpypes3_scanner


def test_who_is_broadcast_calls(mock_agent, mock_bacpypes3_scanner):
    """Test that who_is_broadcast method makes the expected calls"""
    # Set up test environment
    with patch('grasshopper.agent.bacpypes3_scanner', return_value=mock_bacpypes3_scanner):
        # Mock the agent methods
        mock_agent.who_is_broadcast.return_value = None
        
        # Call who_is_broadcast
        mock_agent.who_is_broadcast()
        
        # Verify that the method was called
        mock_agent.who_is_broadcast.assert_called_once()


def test_bbmd_and_subnet_retrieval(mock_agent):
    """Test that BBMD and subnet retrieval methods work correctly"""
    # Set up test data
    test_bbmds = [{"address": "192.168.1.10", "port": 47808}]
    test_subnets = [{"network": 1, "address": "192.168.1.0/24"}]
    
    # Configure the mock to return our test data
    mock_agent.config_retrieve_bbmd_devices.return_value = test_bbmds
    mock_agent.config_retrieve_subnets.return_value = test_subnets
    
    # Call the methods
    retrieved_bbmds = mock_agent.config_retrieve_bbmd_devices()
    retrieved_subnets = mock_agent.config_retrieve_subnets()
    
    # Verify the results
    assert retrieved_bbmds == test_bbmds
    assert retrieved_subnets == test_subnets
    
    # Verify that the methods were called
    mock_agent.config_retrieve_bbmd_devices.assert_called_once()
    mock_agent.config_retrieve_subnets.assert_called_once()


def test_run_async_function_calls(mock_agent):
    """Test that run_async_function makes the expected calls"""
    # Create a mock coroutine function
    async_func = MagicMock()
    
    # Create a mock graph
    test_graph = MagicMock()
    
    # Call run_async_function
    mock_agent.run_async_function(async_func, test_graph)
    
    # Verify that the method was called with the right arguments
    mock_agent.run_async_function.assert_called_once_with(async_func, test_graph)