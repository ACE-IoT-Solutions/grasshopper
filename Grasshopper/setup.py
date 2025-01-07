from setuptools import setup, find_packages

MAIN_MODULE = 'agent'

# Find the agent package that contains the main module
packages = find_packages('.')
agent_package = 'grasshopper'

# Find the version number from the main module
agent_module = agent_package + '.' + MAIN_MODULE
_temp = __import__(agent_module, globals(), locals(), ['__version__'], 0)
__version__ = _temp.__version__

# Setup
setup(
    include_package_data=True,
    name=agent_package + 'agent',
    version=__version__,
    author="Justice Lee",
    author_email="justice@aceiotsolutions.com",
    description="Network Device monitoring using Bacnet Broadcast",
    install_requires=['volttron'],
    packages=packages,
    entry_points={
        'setuptools.installation': [
            'eggsecutable = ' + agent_module + ':main',
        ]
    }
)