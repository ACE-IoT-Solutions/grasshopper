"""Test file to verify type checking with mypy."""
from typing import Any, Dict, List, Optional

# Import from grasshopper
from grasshopper import __version__
from grasshopper.agent import DEVICE_STATE_CONFIG, Grasshopper, seconds_in_day
from grasshopper.api import api_router


def test_function(config_path: str) -> Grasshopper:
    """Test function with type annotations."""
    gh = Grasshopper(
        scan_interval_secs=seconds_in_day,
        low_limit=0,
        high_limit=4194303,
    )
    
    # Test handling dict with proper type annotations
    config: Dict[str, Any] = {
        "scan_interval_secs": 3600,
        "low_limit": 100,
        "high_limit": 1000,
    }
    
    # Test using optional types
    bbmd_devices: Optional[List[Dict[str, Any]]] = gh.config_retrieve_bbmd_devices()
    
    return gh