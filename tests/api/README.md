# API Testing for Grasshopper

These tests validate the FastAPI endpoints of the Grasshopper application without requiring a full Volttron agent instance.

## Test Structure

- `test_api_endpoints.py`: Tests for basic API functionality
- `test_models.py`: Tests for Pydantic model validation
- `test_complex_endpoints.py`: Tests for endpoints with complex logic and dependencies

## Running Tests

To run the tests, use pytest from the project root:

```bash
cd /path/to/grasshopper
pytest tests/api
```

## Test Coverage

These tests cover:

1. Basic CRUD operations for TTL files, comparison files, and network configuration files
2. Model validation for all Pydantic models
3. Queue management for TTL file comparisons
4. Network visualization generation
5. CSV export functionality

## Dependencies

- pytest
- fastapi
- httpx (used by TestClient)
- tempfile (for temporary directory creation)
- pytest-cov (optional, for coverage reports)

## Adding New Tests

When adding new API endpoints, please add corresponding tests in the appropriate file, or create a new file if needed.