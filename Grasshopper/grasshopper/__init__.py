"""Module root for the Grasshopper package."""

from typing import List

# Import version directly
from .version import __version__

# Define what's available for "from grasshopper import *"
__all__: List[str] = [
    "__version__",
]
