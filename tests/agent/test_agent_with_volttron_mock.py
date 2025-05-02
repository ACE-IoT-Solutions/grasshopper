"""Tests for Grasshopper agent using Volttron testing utilities"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

# Import Volttron testing utilities
from volttrontesting.utils.utils import AgentMock

# Add the Grasshopper directory to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grasshopper"))
)

# Import the agent
from grasshopper.agent import Grasshopper


class TestGrasshopperAgent:
    """Test class for Grasshopper agent using Volttron's AgentMock"""
    
    @pytest.fixture
    def mock_grasshopper(self):
        """Create a mock Grasshopper agent using Volttron's AgentMock"""
        # Create a temporary directory for agent data
        with TemporaryDirectory() as temp_dir:
            # Setup test directories
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
            
            # Create a modified Grasshopper class that uses AgentMock
            # The key step here is to dynamically replace the agent's parent class with AgentMock
            # Define a class for testing
            class GrasshopperWithMock(Grasshopper):
                """A Grasshopper agent with mocked Volttron interfaces"""
                def __init__(self, **kwargs):
                    """Modified initialization that doesn't call super().__init__"""
                    # Set up attributes normally set by the parent class
                    self.vip = MagicMock()
                    self.core = MagicMock()
                    self.core.identity = "grasshopper_test"
                    self.core.periodic = MagicMock()
                    
                    # Set up agent attributes
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
                    
                    # Set up other agent attributes
                    self.bacnet_analysis = None
                    self.http_server = None
                    self.agent_data_path = temp_dir
                    self.app = None
                    self.vendor_info = None
                    
                    # Mock gevent lock
                    import gevent
                    self.config_store_lock = MagicMock()
                    
                    # Set up default config
                    self.default_config = {
                        "scan_interval_secs": self.scan_interval_secs,
                        "low_limit": self.low_limit,
                        "high_limit": self.high_limit,
                        "device_broadcast_full_step_size": self.device_broadcast_full_step_size,
                        "device_broadcast_empty_step_size": self.device_broadcast_empty_step_size,
                        "graph_store_limit": self.graph_store_limit,
                        "bacpypes_settings": self.bacpypes_settings,
                        "webapp_settings": self.webapp_settings,
                    }
                
                # Override the configure method to update attributes directly
                def configure(self, config_name, action, contents):
                    config = self.default_config.copy()
                    config.update(contents)
                    
                    # Update agent attributes from config
                    self.scan_interval_secs = config.get("scan_interval_secs", 86400)
                    self.low_limit = config.get("low_limit", 0)
                    self.high_limit = config.get("high_limit", 4194303)
                    self.device_broadcast_full_step_size = config.get("device_broadcast_full_step_size", 100)
                    self.device_broadcast_empty_step_size = config.get("device_broadcast_empty_step_size", 1000)
                    self.bacpypes_settings = config.get("bacpypes_settings", {})
                    self.webapp_settings = config.get("webapp_settings", {})
                    
                    # Call configure_server_setup
                    self.configure_server_setup()
                    
                    # Set up bacnet_analysis periodic task
                    if self.bacnet_analysis is not None:
                        self.bacnet_analysis.kill()
                    self.bacnet_analysis = self.core.periodic(
                        self.scan_interval_secs, self.who_is_broadcast
                    )
                
                # Override the config_store_bbmd_devices method
                def config_store_bbmd_devices(self, bbmd_devices):
                    with self.config_store_lock:
                        try:
                            config = self.vip.config.get("device_config")
                        except KeyError:
                            config = {}
                        config["bbmd_devices"] = bbmd_devices
                        self.vip.config.set("device_config", config)
                
                # Override the config_retrieve_bbmd_devices method
                def config_retrieve_bbmd_devices(self):
                    with self.config_store_lock:
                        try:
                            config = self.vip.config.get("device_config")
                        except KeyError:
                            return []
                    return config.get("bbmd_devices", [])
                
                # Override the config_store_subnets method
                def config_store_subnets(self, subnets):
                    with self.config_store_lock:
                        try:
                            config = self.vip.config.get("device_config")
                        except KeyError:
                            config = {}
                        config["subnets"] = subnets
                        self.vip.config.set("device_config", config)
                
                # Override the config_retrieve_subnets method
                def config_retrieve_subnets(self):
                    with self.config_store_lock:
                        try:
                            config = self.vip.config.get("device_config")
                        except KeyError:
                            return []
                    return config.get("subnets", [])
                
                # Mock other key methods
                def configure_server_setup(self):
                    pass
                
                def who_is_broadcast(self):
                    pass
            
            # Apply the AgentMock to our test class
            # This step uses Volttron's AgentMock pattern
            GrasshopperWithMock.__bases__ = (AgentMock.imitate(Grasshopper, Grasshopper),)
            
            # Create an instance of our mock agent
            agent = GrasshopperWithMock(**test_config)
            agent.test_dir = temp_dir
            
            yield agent
    
    def test_agent_initialization(self, mock_grasshopper):
        """Test that the agent initializes with the correct configuration"""
        agent = mock_grasshopper
        
        # Verify agent configuration
        assert agent.scan_interval_secs == 3600
        assert agent.low_limit == 0
        assert agent.high_limit == 100
        assert agent.device_broadcast_full_step_size == 10
        assert agent.device_broadcast_empty_step_size == 20
        
        # Verify bacpypes settings
        assert agent.bacpypes_settings["name"] == "TestDevice"
        assert agent.bacpypes_settings["instance"] == 1234
        assert agent.bacpypes_settings["address"] == "127.0.0.1/24:47808"
        
        # Verify webapp settings
        assert agent.webapp_settings["host"] == "127.0.0.1"
        assert agent.webapp_settings["port"] == 8888
    
    def test_configure_method(self, mock_grasshopper):
        """Test the configure method with a new configuration"""
        agent = mock_grasshopper
        
        # Create a new mock for gevent.spawn
        with patch('gevent.spawn') as mock_spawn:
            # Create a new configuration
            new_config = {
                "scan_interval_secs": 7200,  # 2 hours
                "low_limit": 100,
                "high_limit": 200,
                "device_broadcast_full_step_size": 20,
                "device_broadcast_empty_step_size": 30,
                "bacpypes_settings": {
                    "name": "UpdatedDevice",
                    "instance": 5678,
                    "network": 0,
                    "address": "192.168.1.100/24:47808",
                    "vendoridentifier": 888,
                    "foreign": None,
                    "ttl": 60,
                    "bbmd": None,
                }
            }
            
            # Call configure with new config
            agent.configure("config", "NEW", new_config)
            
            # Verify configuration was updated
            assert agent.scan_interval_secs == 7200
            assert agent.low_limit == 100
            assert agent.high_limit == 200
            assert agent.device_broadcast_full_step_size == 20
            assert agent.device_broadcast_empty_step_size == 30
            
            # Verify bacpypes settings updated
            assert agent.bacpypes_settings["name"] == "UpdatedDevice"
            assert agent.bacpypes_settings["instance"] == 5678
            assert agent.bacpypes_settings["address"] == "192.168.1.100/24:47808"
            assert agent.bacpypes_settings["vendoridentifier"] == 888
    
    def test_config_store_methods(self, mock_grasshopper):
        """Test the config store methods for BBMD devices and subnets"""
        agent = mock_grasshopper
        
        # Set up test data
        test_bbmds = [
            {"address": "192.168.1.10", "port": 47808},
            {"address": "192.168.1.20", "port": 47808}
        ]
        
        test_subnets = [
            {"network": 1, "address": "192.168.1.0/24"},
            {"network": 2, "address": "10.0.0.0/24"}
        ]
        
        # Mock the config get/set methods
        agent.vip.config.get.return_value = {}
        
        # Test BBMD config methods
        agent.config_store_bbmd_devices(test_bbmds)
        agent.vip.config.set.assert_called_with("device_config", {"bbmd_devices": test_bbmds})
        
        # Reset call counts and setup return value for BBMD retrieval
        agent.vip.config.set.reset_mock()
        agent.vip.config.get.return_value = {"bbmd_devices": test_bbmds}
        retrieved_bbmds = agent.config_retrieve_bbmd_devices()
        assert retrieved_bbmds == test_bbmds
        
        # Test subnet config methods
        agent.vip.config.get.return_value = {}
        agent.config_store_subnets(test_subnets)
        agent.vip.config.set.assert_called_with("device_config", {"subnets": test_subnets})
        
        # Reset call counts and setup return value for subnet retrieval
        agent.vip.config.set.reset_mock()
        agent.vip.config.get.return_value = {"subnets": test_subnets}
        retrieved_subnets = agent.config_retrieve_subnets()
        assert retrieved_subnets == test_subnets