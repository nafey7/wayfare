# Testing Standards & Best Practices

**Status**: 🚧 Active Development
**Last Updated**: April 10, 2026
**Purpose**: Establish consistent testing patterns for Voya backend to ensure reliable, maintainable tests

## 🎯 Testing Philosophy

**Goal**: Fast, reliable, isolated tests that can run anywhere without external dependencies.

**Key Principles**:
1. ✅ **Unit tests should be FAST** (<100ms per test)
2. ✅ **Mock ALL external dependencies** (DB, APIs, file system)
3. ✅ **Tests should be ISOLATED** (can run in any order)
4. ✅ **One concept per test** (focused, clear assertions)
5. ❌ **Never rely on external services** in unit tests

## 📁 Test Structure

```
tests/
├── unit_tests/           # Fast, isolated, mocked (PRIMARY)
│   ├── test_ai/         # AI & conversation logic
│   ├── test_api/        # FastAPI endpoints
│   ├── test_domains/    # Business logic
│   └── conftest.py      # Shared fixtures
├── integration_tests/    # Docker compose, real services
│   ├── test_database/   # MongoDB operations
│   ├── test_apis/       # External API integration
│   └── conftest.py      # Integration fixtures
└── README.md
```

## 🧪 Unit Testing Standards

### Rule 1: Mock External Dependencies

**❌ Bad Example** - Using real MongoDB:
```python
from motor.motor_asyncio import AsyncIOMotorClient

async def test_user_creation():
    # DON'T: Requires MongoDB running
    db = AsyncIOMotorClient("mongodb://localhost:27017")
    user_id = await create_user(db, {"name": "John"})
    assert user_id is not None
```

**✅ Good Example** - Mocked MongoDB:
```python
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def mock_db():
    """Mock MongoDB database for unit tests."""
    db = AsyncMock()
    db.users = AsyncMock()
    db.users.insert_one = AsyncMock(return_value=Mock(inserted_id="123"))
    return db

async def test_user_creation(mock_db):
    # DO: Fast, no external dependencies
    user_id = await create_user(mock_db, {"name": "John"})
    assert user_id == "123"
    mock_db.users.insert_one.assert_called_once()
```

### Rule 2: Mock External APIs

**❌ Bad Example** - Real HTTP calls:
```python
async def test_flight_search():
    # DON'T: Makes real API calls
    results = await flightlogic_client.search("AMS", "JFK")
    assert len(results) > 0
```

**✅ Good Example** - Mocked HTTP:
```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_flightlogic():
    """Mock FlightLogic API client."""
    client = AsyncMock()
    client.search = AsyncMock(return_value={
        "flights": [
            {"id": "FL001", "price": 299.00},
            {"id": "FL002", "price": 350.00}
        ]
    })
    return client

async def test_flight_search(mock_flightlogic):
    # DO: Fast, predictable, isolated
    results = await mock_flightlogic.search("AMS", "JFK")
    assert len(results["flights"]) == 2
    assert results["flights"][0]["price"] == 299.00
```

### Rule 3: Use Pytest Fixtures

**Standard Fixtures** (in `conftest.py`):

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.users = AsyncMock()
    db.sessions = AsyncMock()
    db.bookings = AsyncMock()
    return db

@pytest.fixture
def mock_flight_service(mock_db):
    """Mock flight service with database."""
    from app.domains.flight.service import FlightService
    service = FlightService(db=mock_db)
    return service

@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        "_id": "user_123",
        "email": "test@example.com",
        "name": "Test User",
        "created_at": "2025-01-01T00:00:00Z"
    }
```

### Rule 4: One Concept Per Test

**❌ Bad Example** - Testing multiple things:
```python
async def test_user_operations(mock_db):
    # DON'T: Tests creation, update, and deletion
    user_id = await create_user(mock_db, {"name": "John"})
    updated = await update_user(mock_db, user_id, {"name": "Jane"})
    deleted = await delete_user(mock_db, user_id)
    assert all([user_id, updated, deleted])
```

**✅ Good Example** - Focused tests:
```python
async def test_create_user_returns_id(mock_db):
    # DO: Tests one thing clearly
    user_id = await create_user(mock_db, {"name": "John"})
    assert user_id == "123"
    mock_db.users.insert_one.assert_called_once()

async def test_update_user_modifies_fields(mock_db):
    # DO: Separate test for updates
    mock_db.users.update_one = AsyncMock(return_value=Mock(modified_count=1))
    result = await update_user(mock_db, "123", {"name": "Jane"})
    assert result is True
    mock_db.users.update_one.assert_called_once()
```

### Database migration unit tests

Migrations in `app/database/migrations/` should have focused unit tests (mocked DB, no real MongoDB). **Assertions**: for `create_index`, check the **index key list** and kwargs, not only that `create_index` ran; for `down()`, cover both successful drops and intentional **error swallowing** (e.g. missing index). See **`MIGRATIONS.md`** → *Unit tests for migrations*.

## 🐳 Integration Testing Standards

**When to use integration tests**:
- Testing MongoDB operations end-to-end
- Testing external API integration (with real calls)
- Testing multi-service workflows

**Setup**: Use Docker Compose with isolated test environment

```yaml
# compose.test.yaml
services:
  mongodb-test:
    image: mongo:7.0
    environment:
      - MONGO_INITDB_DATABASE=voya_test
    ports:
      - "27018:27017"  # Different port than dev
```

**Integration Test Example**:
```python
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture
async def test_db():
    """Real MongoDB for integration tests."""
    client = AsyncIOMotorClient("mongodb://localhost:27018")
    db = client.voya_test
    yield db
    # Cleanup after test
    await client.drop_database("voya_test")
    client.close()

@pytest.mark.integration
async def test_user_creation_with_real_db(test_db):
    """Integration test with real MongoDB."""
    user_data = {"email": "test@example.com", "name": "Test User"}
    result = await test_db.users.insert_one(user_data)

    # Verify in database
    user = await test_db.users.find_one({"_id": result.inserted_id})
    assert user["email"] == "test@example.com"
```

## 🎭 Common Mocking Patterns

### Pattern 1: AsyncMock for Async Functions

```python
from unittest.mock import AsyncMock

# Mock async database call
mock_db = AsyncMock()
mock_db.users.find_one = AsyncMock(return_value={"_id": "123"})

# Usage
result = await mock_db.users.find_one({"email": "test@example.com"})
```

### Pattern 2: MagicMock for Sync Functions

```python
from unittest.mock import MagicMock

# Mock sync operations
mock_config = MagicMock()
mock_config.get_setting.return_value = "production"

# Usage
env = mock_config.get_setting("ENVIRONMENT")
```

### Pattern 3: Patch Decorators

```python
from unittest.mock import patch

@patch('app.domains.flight.service.FlightLogicClient')
async def test_with_patched_client(mock_client_class):
    """Patch class at import time."""
    mock_instance = AsyncMock()
    mock_client_class.return_value = mock_instance

    # Test code using the patched client
    service = FlightService()
    await service.search_flights("AMS", "JFK")

    mock_instance.search.assert_called_once()
```

### Pattern 4: httpx_mock for HTTP Calls

```python
import pytest
from pytest_httpx import HTTPXMock

async def test_api_call(httpx_mock: HTTPXMock):
    """Mock external API calls."""
    httpx_mock.add_response(
        url="https://api.flightlogic.com/search",
        json={"flights": [{"id": "FL001"}]},
        status_code=200
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.flightlogic.com/search")
        assert response.status_code == 200
```

## 🤝 Contract Testing Pattern

**Purpose**: Verify data structures are consistent between producers and consumers.

Contract tests catch bugs where:
- Endpoint A stores data in one format, Endpoint B expects another
- Backend returns `updated_pricing`, frontend expects `pricing`
- Required fields are missing in redirect URLs

### When to Write Contract Tests

Write contract tests when:
1. **Multi-endpoint flows**: Data passes between endpoints (e.g., `/select` → `/book-from-session`)
2. **Backend-Frontend boundaries**: API responses used by frontend
3. **External API integration**: Our code expects specific response structures

### Pattern: Producer-Consumer Contract

```python
class TestBookingSessionDataContract:
    """Contract: /api/flights/select → /api/flights/book-from-session"""

    @pytest.fixture
    def producer_output(self) -> dict:
        """Data structure created by producer (select endpoint)."""
        return {
            "selected_flight": {
                "itinerary": {"updated_pricing": {...}},
                "fare_source_code": "FARE_CODE",  # <-- Consumer needs this
            },
            "fl_session_id": "flightlogic-session",  # <-- Consumer needs this
        }

    def test_required_field_is_accessible(self, producer_output: dict):
        """Verify consumer can extract required field."""
        fare_code = producer_output["selected_flight"].get("fare_source_code")
        assert fare_code is not None, (
            "fare_source_code must be accessible for booking. "
            "Producer: /api/flights/select, Consumer: /api/flights/book-from-session"
        )
```

### Pattern: Priority-Based Extraction

When fields can be in multiple locations (legacy vs new):

```python
def test_extraction_handles_multiple_locations(self, session_data: dict):
    """Test extraction works for all supported data formats."""
    selected_flight = session_data["selected_flight"]
    itinerary = selected_flight.get("itinerary", {})

    # Priority order (matches actual endpoint logic)
    fare_source_code = (
        selected_flight.get("fare_source_code")  # Priority 1: api_select_v2
        or itinerary.get("updated_pricing", {}).get("updated_fare_source_code")  # Priority 2
        or itinerary.get("pricing", {}).get("fare_source_code")  # Priority 3: legacy
    )

    assert fare_source_code is not None
```

### Existing Contract Tests

- `tests/unit_tests/test_api/test_flight_booking_contracts.py` - Flight booking flow
- `tests/unit_tests/test_api/test_hotel_booking_contracts.py` - Hotel booking flow

## 🚀 Running Tests

### Unit Tests (Fast - Use These Daily)
```bash
# All unit tests
pytest tests/unit_tests/ -v

# Specific module
pytest tests/unit_tests/test_ai/ -v

# With coverage
pytest tests/unit_tests/ --cov=app --cov-report=term-missing

# Fast feedback (stop on first failure)
pytest tests/unit_tests/ -x
```

### Integration Tests (Slower - Use Before PR)
```bash
# Start test environment
docker compose -f compose.test.yaml up -d

# Run integration tests
pytest tests/integration_tests/ -m integration -v

# Cleanup
docker compose -f compose.test.yaml down -v
```

### Running Specific Tests
```bash
# By test name
pytest -k "test_user_creation"

# By marker
pytest -m "not slow"

# Verbose with captured output
pytest tests/unit_tests/test_ai/test_flight_booking_handler.py -v -s
```

## 📊 Coverage Requirements

| Category | Minimum Coverage | Target |
|----------|-----------------|--------|
| **Unit Tests** | 80% | 90% |
| **Critical Paths** | 100% | 100% |
| **New Code** | 80% | 95% |

**Critical Paths** (require 100% coverage):
- Authentication & Authorization
- Payment processing
- Booking creation & modification
- User data handling

## ✅ Test Checklist

Before committing tests, ensure:

- [ ] **No External Dependencies**: All databases/APIs mocked
- [ ] **Fast Execution**: Unit tests < 100ms each
- [ ] **Isolated**: Tests can run in any order
- [ ] **Descriptive Names**: Test names explain what they test
- [ ] **Assertions Clear**: Each test has clear pass/fail criteria
- [ ] **Coverage**: New code has 80%+ coverage
- [ ] **CI Passing**: Tests pass in CI environment

## 🐛 Debugging Failed Tests

### Common Issues

**Issue 1: Test works locally but fails in CI**
```bash
# Likely cause: External dependency not mocked
# Solution: Add mocks for all external services
```

**Issue 2: Intermittent failures**
```bash
# Likely cause: Tests depend on execution order
# Solution: Make each test fully isolated with proper fixtures
```

**Issue 3: Slow tests**
```bash
# Likely cause: Using real database/API calls
# Solution: Replace with mocks for unit tests
```

### Debug Commands
```bash
# Run with print statements visible
pytest tests/unit_tests/ -v -s

# Run single test with debugging
pytest tests/unit_tests/test_ai/test_booking.py::test_create_booking -v -s

# Show locals on failure
pytest tests/unit_tests/ -l

# Enter debugger on failure
pytest tests/unit_tests/ --pdb
```

## 📚 Additional Resources

### Internal Docs
- **CI/CD Guide**: `docs/CI_CD.md`
- **Code Quality**: `docs/CODE_QUALITY.md`
- **Architecture**: `docs/ARCHITECTURE.md`

### External Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [AsyncMock Examples](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)

## 🔄 Continuous Improvement

This is a living document. As we identify new patterns or issues:
1. Update this guide
2. Add examples from real tests
3. Share learnings with the team
4. Iterate on best practices

**Questions or Suggestions?** Create an issue with label `testing-standards`.
