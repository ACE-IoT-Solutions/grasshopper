"""Module root for the Grasshopper package."""

from typing import List, Dict, Any, Optional, Union, Set, Callable, TypeVar, cast

# Import key modules and classes for easier access
from grasshopper.version import __version__

# Expose key modules
import grasshopper.agent
import grasshopper.api
import grasshopper.bacpypes3_scanner
import grasshopper.parser
import grasshopper.rdf_components
import grasshopper.serializers
import grasshopper.web_app

# Define what's available for "from grasshopper import *"
__all__: List[str] = [
    "agent",
    "api",
    "bacpypes3_scanner",
    "parser",
    "rdf_components",
    "serializers",
    "web_app",
    "__version__",
]
