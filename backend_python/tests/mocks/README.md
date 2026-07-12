# Mock Servers

This directory contains mock server implementations for external APIs used in testing and development.

## Available Mocks

### FlightLogic Mock Server (`flightlogic/`)

A lightweight FastAPI-based mock server that simulates the FlightLogic API for local development and testing.

**Purpose**:
- Test flight booking flow without hitting production FlightLogic API
- Reproduce and debug booking issues locally
- Validate request/response formats
- Run integration tests in CI/CD without external dependencies

**Usage**:
```bash
# Start mock server
cd backend_python
python -m tests.mocks.flightlogic.server

# Configure app to use mock
# In .env:
FLIGHTLOGIC_API_URL=http://localhost:8002/api/aeroVE5
```

## Adding New Mocks

When adding a new mock server:

1. Create a subdirectory: `tests/mocks/service_name/`
2. Add `server.py` with FastAPI endpoints
3. Add `mock_data.py` with sample responses
4. Add `README.md` with usage instructions
5. Update this README with the new mock

## Best Practices

- ✅ Use existing DTOs from `integrations/` for validation
- ✅ Keep mock data realistic and based on actual API responses
- ✅ Log all requests/responses for debugging
- ✅ Support easy toggling between mock and real API
- ✅ Document any deviations from real API behavior
- ❌ Don't commit mock servers to production builds
- ❌ Don't use mock servers in production environment
