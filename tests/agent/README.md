# Grasshopper Agent Tests

These tests validate the functionality of the Grasshopper agent, including its configuration, lifecycle, BACnet scanning capabilities, and web server integration.

## Test Structure

- `test_agent_config.py`: Tests for agent initialization, configuration, and config store methods
- `test_agent_bacnet.py`: Tests for BACnet network scanning functionality
- `test_agent_webserver.py`: Tests for web server and API setup

## Running Tests

To run the agent tests, use pytest from the project root:

```bash
cd /path/to/grasshopper
pytest tests/agent
```

## Test Coverage

These tests cover:

1. Agent initialization and configuration
2. BBMD and subnet configuration methods
3. BACnet network scanning functionality
4. Web server setup and API integration

## Dependencies

- pytest
- unittest.mock (for mocking Volttron platform and BACnet functionality)
- rdflib (for testing RDF graph functionality)

## Adding New Tests

When extending the agent's functionality, please add corresponding tests to maintain test coverage.