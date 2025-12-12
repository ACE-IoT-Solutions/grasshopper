# Grasshopper Testing Guide

This document outlines the testing approach for the Grasshopper project, including both API and Agent testing.

## Testing Approach

The Grasshopper testing strategy consists of two main components:

1. **API Testing**: Tests that verify the FastAPI endpoints work correctly
2. **Agent Testing**: Tests that verify the Volttron agent's functionality

## API Testing

API tests are located in the `tests/api` directory and use the FastAPI TestClient to verify the functionality of API endpoints.

### Running API Tests

```bash
cd /path/to/grasshopper
python -m pytest tests/api
```

## Agent Testing

Agent tests are located in the `tests/agent` directory and use mock objects to test the Volttron agent's functionality without requiring a running Volttron platform.

### Running Agent Tests

```bash
cd /path/to/grasshopper
python -m pytest tests/agent
```

### Agent Test Structure

The agent tests are structured as follows:

- **conftest.py**: Contains fixtures for testing, including the `mock_agent` fixture
- **test_agent_config.py**: Tests for agent configuration and config store methods
- **test_agent_bacnet.py**: Tests for BACnet scanning functionality
- **test_agent_webserver.py**: Tests for web server setup and API integration
- **test_agent_with_volttron_mock.py**: Tests using Volttron's AgentMock utility

### Mocking Approaches

The agent tests use two different mocking strategies:

#### 1. Custom Mock Objects

These tests use custom mock classes to simulate the Grasshopper agent's interface:

- `MockAgent`: A class that simulates the Grasshopper agent's interface
- `MockVIP`: Mocks for the Volttron VIP interfaces (config, pubsub, etc.)
- `MockCore`: Simulates the agent's core functionality

This approach is used in the basic test files and is simpler to understand and maintain.

#### 2. Volttron AgentMock

These tests use Volttron's built-in `AgentMock` utility to create a test harness:

```python
from volttrontesting.utils.utils import AgentMock

# Replace the agent's parent class with AgentMock
TestAgentClass.__bases__ = (AgentMock.imitate(Agent, Agent),)
```

This approach is more aligned with how Volttron agents are typically tested in the Volttron ecosystem and is used in `test_agent_with_volttron_mock.py`.

### Writing New Agent Tests

When writing new agent tests:

1. Decide which mocking approach to use (custom mocks or AgentMock)
2. For custom mocks: Use the `mock_agent` fixture
3. For AgentMock: Create a new test class that extends the agent class and modify its base class
4. Override methods as needed for your test
5. Verify method calls and assertions on the mock objects
6. Check both functionality and edge cases

## Integration Testing

For future integration testing that requires a running Volttron instance:

1. Set up a test Volttron instance
2. Install the Grasshopper agent in the test instance
3. Use the VIP interface to interact with the agent
4. Verify the agent's behavior through its API and VIP methods

## BACnet Testing

For testing BACnet functionality:

1. Use the mock BACnet scanner to simulate network responses
2. Create test TTL files to represent BACnet device data
3. Verify the agent processes and stores the data correctly

## Test Coverage

To check test coverage:

```bash
cd /path/to/grasshopper
python -m pytest --cov=Grasshopper tests/
```

## Dependency Requirements

The agent tests require the following packages:

- pytest
- mock
- volttrontesting (from Volttron)

Install them with:

```bash
pip install pytest mock
```

---

This testing approach allows for comprehensive testing of the Grasshopper agent without requiring a full Volttron environment, making tests faster and more reliable.