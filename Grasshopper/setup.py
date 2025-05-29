import os
import re

from setuptools import find_packages, setup

MAIN_MODULE = "agent"

# Find the agent package that contains the main module
packages = find_packages(".")
agent_package = "grasshopper"
agent_module = agent_package + "." + MAIN_MODULE

# Get version from version.py file
version_file = os.path.join(os.path.dirname(__file__), "grasshopper", "version.py")
with open(version_file, "r") as f:
    version_content = f.read()
    version_match = re.search(
        r'^__version__ = ["\']([^"\']*)["\']', version_content, re.M
    )
    if version_match:
        __version__ = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string in %s" % version_file)

# Setup
setup(
    include_package_data=True,
    name=agent_package,
    version=__version__,
    author="Justice Lee",
    author_email="justice@aceiotsolutions.com",
    description="Network Device monitoring using Bacnet Broadcast",
    install_requires=["volttron"],
    packages=packages,
    package_data={
        "grasshopper": ["py.typed"],
    },
    entry_points={
        "setuptools.installation": [
            "eggsecutable = " + agent_module + ":main",
        ]
    },
)
