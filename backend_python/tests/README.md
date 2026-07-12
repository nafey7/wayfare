# Test Structure

## Organization

Tests are organized to match the application structure:

```
tests/
├── unit_tests/          # Tests with mocked dependencies
│   ├── test_core/       # Tests for app/core/
│   ├── test_engines/    # Tests for app/engines/
│   ├── test_services/   # Tests for app/services/
│   └── test_main.py     # Tests for app/main.py
│
└── conftest.py          # Root pytest configuration (backwards compatibility)
```

## Running Tests

### All Tests
```powershell
# Run all tests
..\.venv\Scripts\pytest

# With coverage
..\.venv\Scripts\pytest --cov=app --cov-report=html
```

### Unit Tests Only
```powershell
# Run all unit tests (fast, with mocked dependencies)
..\.venv\Scripts\pytest tests/unit_tests/

# Run specific unit test
..\.venv\Scripts\pytest tests/unit_tests/test_services/test_auth_service.py

# Run tests for a specific service
..\.venv\Scripts\pytest tests/unit_tests/test_services/
```

## Test Types

### Unit Tests (`unit_tests/`)
- **Purpose**: Test individual components in isolation
- **Database**: Mocked
- **External APIs**: Mocked
- **Speed**: Fast
- **Folders**:
  - `test_core/` - Test utilities, config, and helper functions
  - `test_engines/` - Test engine logic (flight search, etc.)
  - `test_services/` - Test service logic with mocked database
- **Example**: Testing service methods, engine functionality, utility functions

## Writing Tests

### Unit Test Example
```python
# tests/unit_tests/test_services/test_user_service.py
from unittest.mock import patch, MagicMock
import pytest

@pytest.mark.asyncio
async def test_get_user_by_email():
    mock_db = MagicMock()
    with patch('app.database.mongodb.get_database', return_value=mock_db):
        # Test with mocked database
        result = await user_service.get_user_by_email("test@example.com")
        assert result is not None
```

### Engine Test Example
```python
# tests/unit_tests/test_engines/test_flight_engine.py
from unittest.mock import patch
import pytest

@pytest.mark.asyncio
async def test_search_flights():
    with patch('app.engines.flight_engine.FlightLogicEngine') as mock_engine:
        # Test engine with mocked external API
        flights = await search_flights("AMS", "CDG", "2025-01-01")
        assert len(flights) > 0
```

## Configuration Files

- `conftest.py` - Root pytest configuration (backwards compatibility)
- `unit_tests/conftest.py` - Fixtures for mocked unit tests

## Coverage

Minimum coverage requirement: 80% for new code

Check coverage:
```powershell
..\.venv\Scripts\pytest --cov=app --cov-report=term-missing
```

Generate HTML coverage report:
```powershell
..\.venv\Scripts\pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```
