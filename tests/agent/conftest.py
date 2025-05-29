"""Configuration and fixtures for Grasshopper agent tests"""

import os
import sys
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

import pytest

# Add the Grasshopper directory to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grasshopper"))
)


# Create mock classes for grasshopper tests
class MockCore:
    """Mock Core class for testing"""
    def __init__(self):
        self.identity = "grasshopper_test"
        self.periodic = MagicMock()


class MockVIP:
    """Mock VIP class for testing"""
    def __init__(self):
        self.rpc = MagicMock()
        self.pubsub = MagicMock()
        self.health = MagicMock()
        self.config = MagicMock()
        # Setup config methods
        self.config.set = MagicMock()
        self.config.get = MagicMock(return_value={})
        self.config.list = MagicMock(return_value=[])
        self.config.set_default = MagicMock()
        self.config.subscribe = MagicMock()


class MockAgent:
    """Mock Agent class for testing"""
    def __init__(self, **kwargs):
        self.core = MockCore()
        self.vip = MockVIP()
        
        # Store test values
        self.scan_interval_secs = kwargs.get('scan_interval_secs', 86400)
        self.low_limit = kwargs.get('low_limit', 0)
        self.high_limit = kwargs.get('high_limit', 4194303)
        self.device_broadcast_full_step_size = kwargs.get('device_broadcast_full_step_size', 100)
        self.device_broadcast_empty_step_size = kwargs.get('device_broadcast_empty_step_size', 1000)
        self.bacpypes_settings = kwargs.get('bacpypes_settings', {
            "name": "TestDevice",
            "instance": 999,
            "network": 0,
            "address": "127.0.0.1/24:47808",
            "vendoridentifier": 999,
            "foreign": None,
            "ttl": 30,
            "bbmd": None,
        })
        self.webapp_settings = kwargs.get('webapp_settings', {
            "host": "0.0.0.0",
            "port": 5000,
            "certfile": None,
            "keyfile": None,
        })
        self.graph_store_limit = kwargs.get('graph_store_limit', None)
        
        # Agent-specific attributes
        self.bacnet_analysis = None
        self.app = None
        self.vendor_info = None
        self.agent_data_path = None
        self.http_server = None
        
        # Mocks for common methods
        self.who_is_broadcast = MagicMock()
        self.configure = MagicMock()
        self.config_store_bbmd_devices = MagicMock()
        self.config_retrieve_bbmd_devices = MagicMock(return_value=[])
        self.config_store_subnets = MagicMock()
        self.config_retrieve_subnets = MagicMock(return_value=[])
        self.run_async_function = MagicMock()
        self.configure_server_setup = MagicMock()
        self.setup_routes = MagicMock()
        self._start_server = MagicMock(return_value=0)
        
        # Set up for gevent mocking
        self.config_store_lock = MagicMock()


@pytest.fixture
def mock_agent():
    """Create a MockAgent instance for testing grasshopper functionality"""
    with TemporaryDirectory() as temp_dir:
        # Setup test directories in the temp dir
        os.makedirs(os.path.join(temp_dir, "ttl"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "compare"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "network_config"), exist_ok=True)
        
        # Create test config
        test_config = {
            "scan_interval_secs": 3600,  # 1 hour for testing
            "low_limit": 0,
            "high_limit": 100,  # Smaller range for testing
            "device_broadcast_full_step_size": 10,
            "device_broadcast_empty_step_size": 20,
            "bacpypes_settings": {
                "name": "TestDevice",
                "instance": 1234,
                "network": 0,
                "address": "127.0.0.1/24:47808",
                "vendoridentifier": 999,
                "foreign": None,
                "ttl": 30,
                "bbmd": None,
            },
            "webapp_settings": {
                "host": "127.0.0.1",
                "port": 8888,
                "certfile": None,
                "keyfile": None,
            }
        }
        
        # Create the agent
        agent = MockAgent(**test_config)
        
        # Set the test directory path
        agent.test_dir = temp_dir
        agent.agent_data_path = temp_dir
        
        yield agent


@pytest.fixture
def mock_bacpypes3_scanner():
    """Create a mock for the bacpypes3_scanner function"""
    mock_scanner = MagicMock()
    mock_scanner_instance = MagicMock()
    mock_scanner_instance.get_device_and_router = MagicMock()
    mock_scanner.return_value = mock_scanner_instance
    return mock_scanner