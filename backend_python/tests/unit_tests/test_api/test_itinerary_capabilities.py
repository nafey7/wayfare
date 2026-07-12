"""Unit tests for Itinerary Capabilities API endpoints.

Tests the /api/itinerary/capabilities/* endpoints that provide
airport resolution, date parsing, and flight search for n8n integration.

Note: These tests use a fixture-based approach to mock dependencies,
avoiding module-level sys.modules manipulation which can pollute
other tests in the pytest session.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ==============================================================================
# FIXTURES - Mock dependencies within test scope only
# ==============================================================================


@pytest.fixture
def mock_modules():
    """
    Mock external dependencies within test scope.

    Uses patch.dict to temporarily modify sys.modules only during the test,
    ensuring no pollution of global state for other tests.
    """
    mock_google = MagicMock()
    mock_llm_module = MagicMock()
    mock_llm_module.get_llm_service = MagicMock(return_value=MagicMock())
    mock_llm_module.GeminiLLMService = MagicMock()

    modules_to_mock = {
        "google": mock_google,
        "google.genai": MagicMock(),
        "google.generativeai": MagicMock(),
        "google.auth": MagicMock(),
        "google.auth.transport": MagicMock(),
        "google.auth.transport.requests": MagicMock(),
        "google.oauth2": MagicMock(),
        "google.oauth2.id_token": MagicMock(),
        "integrations.llm": mock_llm_module,
        "integrations.llm.gemini": MagicMock(),
    }

    with patch.dict(sys.modules, modules_to_mock):
        yield modules_to_mock


@pytest.fixture
def capabilities_module(mock_modules):
    """
    Load the capabilities module with mocked dependencies.

    This fixture depends on mock_modules to ensure dependencies are mocked
    before loading the module.
    """
    backend_path = Path(__file__).parent.parent.parent.parent

    # Load schemas
    schemas_spec = importlib.util.spec_from_file_location(
        "app.api.itinerary.schemas",
        str(backend_path / "app" / "api" / "itinerary" / "schemas.py"),
    )
    schemas_module = importlib.util.module_from_spec(schemas_spec)
    sys.modules["app.api.itinerary.schemas"] = schemas_module
    schemas_spec.loader.exec_module(schemas_module)

    # Load capabilities
    capabilities_spec = importlib.util.spec_from_file_location(
        "app.api.itinerary.capabilities",
        str(backend_path / "app" / "api" / "itinerary" / "capabilities.py"),
    )
    capabilities = importlib.util.module_from_spec(capabilities_spec)
    sys.modules["app.api.itinerary.capabilities"] = capabilities
    capabilities_spec.loader.exec_module(capabilities)

    yield capabilities

    # Cleanup: remove loaded modules to avoid affecting other tests
    sys.modules.pop("app.api.itinerary.schemas", None)
    sys.modules.pop("app.api.itinerary.capabilities", None)


@pytest.fixture
def auth_headers() -> dict:
    """Headers with valid API key for testing."""
    return {"X-API-Key": "test-api-key"}


# ==============================================================================
# AUTHENTICATION TESTS
# ==============================================================================


class TestAuthentication:
    """Tests for API key authentication."""

    def test_missing_api_key_returns_401_in_production(self, capabilities_module):
        """Test that missing API key returns 401 in production."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.N8N_CAPABILITIES_API_KEY = (
            "test-api-key"  # pragma: allowlist secret
        )

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/resolve-location",
                json={"query": "London"},
            )

            assert response.status_code == 401
            assert "Missing API key" in response.json()["detail"]

    def test_invalid_api_key_returns_401(self, capabilities_module):
        """Test that invalid API key returns 401."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.N8N_CAPABILITIES_API_KEY = (
            "correct-key"  # pragma: allowlist secret
        )

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/resolve-location",
                json={"query": "London"},
                headers={"X-API-Key": "wrong-key"},
            )

            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]

    def test_missing_api_key_on_parse_dates_returns_401(self, capabilities_module):
        """Test that missing API key on parse-dates returns 401."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.N8N_CAPABILITIES_API_KEY = (
            "test-api-key"  # pragma: allowlist secret
        )

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/parse-dates",
                json={"expression": "next week"},
            )

            assert response.status_code == 401

    def test_missing_api_key_on_search_flights_returns_401(self, capabilities_module):
        """Test that missing API key on search-flights returns 401."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.N8N_CAPABILITIES_API_KEY = (
            "test-api-key"  # pragma: allowlist secret
        )

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-flights",
                json={
                    "origin_iata": "LHR",
                    "destination_iata": "CDG",
                    "departure_date": "2025-12-20",
                    "adults": 1,
                },
            )

            assert response.status_code == 401

    def test_missing_api_key_on_search_hotels_returns_401(self, capabilities_module):
        """Test that missing API key on search-hotels returns 401."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.N8N_CAPABILITIES_API_KEY = (
            "test-api-key"  # pragma: allowlist secret
        )

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-hotels",
                json={
                    "city": "Paris",
                    "country": "France",
                    "check_in": "2025-12-20",
                    "check_out": "2025-12-27",
                    "rooms": 1,
                    "adults": 2,
                },
            )

            assert response.status_code == 401


# ==============================================================================
# SEARCH FLIGHTS TESTS (success path)
# ==============================================================================


class TestSearchFlightsSuccess:
    """Tests for the n8n /search-flights endpoint success path.

    Regression coverage for issue #1034: the endpoint must call the internal
    ``_do_flight_search`` helper (returns full dict) rather than the @tool
    wrapper (returns only LLM-facing content with no flights / search_params).
    """

    def test_success_returns_populated_curated_best_value(
        self, capabilities_module
    ) -> None:
        """A successful flight search must surface a curated.best_value flight."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        # Mimic ``_do_flight_search``'s return shape — full dict (pre-split),
        # so the endpoint sees flights + summary + session_id.
        mock_search_result = {
            "status": "success",
            "session_id": "SESS_OK",
            "search_params": {
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "2026-06-20",
                "return_date": None,
                "journey_type": "OneWay",
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "summary": {
                "total_found": 3,
                "direct_flights": 1,
                "price_range": {"min": 120.0, "max": 540.0, "currency": "EUR"},
            },
            "flights": [
                {
                    "id": "f1",
                    "departure_time": "08:00",
                    "departure_date": "2026-06-20",
                    "arrival_time": "10:30",
                    "arrival_date": "2026-06-20",
                    "origin_code": "LHR",
                    "destination_code": "CDG",
                    "duration": "2h 30m",
                    "duration_minutes": 150,
                    "stops": 0,
                    "price": 120.0,
                    "currency": "EUR",
                    "airline": "British Airways",
                    "airline_code": "BA",
                    "flight_number": "BA304",
                },
                {
                    "id": "f2",
                    "price": 245.0,
                    "currency": "EUR",
                    "airline": "Air France",
                },
                {
                    "id": "f3",
                    "price": 540.0,
                    "currency": "EUR",
                    "airline": "Lufthansa",
                },
            ],
            "instruction": "Present these options to the user.",
        }

        # Pre-inject a fake ``app.ai.graph.tools.flights`` so the endpoint's
        # inline ``from app.ai.graph.tools.flights import _do_flight_search``
        # resolves to the mock without loading the real LangGraph module tree.
        fake_flights_module = MagicMock()
        fake_flights_module._do_flight_search = AsyncMock(
            return_value=mock_search_result
        )
        modules_patch = {
            "app.ai": MagicMock(),
            "app.ai.graph": MagicMock(),
            "app.ai.graph.tools": MagicMock(),
            "app.ai.graph.tools.flights": fake_flights_module,
        }

        with (
            patch.object(capabilities_module, "settings", mock_settings),
            patch.dict(sys.modules, modules_patch),
        ):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-flights",
                json={
                    "origin_iata": "LHR",
                    "destination_iata": "CDG",
                    "departure_date": "2026-06-20",
                    "adults": 1,
                },
                headers={"X-API-Key": "test-key"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_found"] == 3
        # Crucial: curated.best_value must be populated. Pre-fix the endpoint
        # called the @tool wrapper which returned only summary+instruction;
        # `flights` was always [] and `curated` came back as None.
        assert data["curated"] is not None
        assert "best_value" in data["curated"]
        assert data["curated"]["best_value"]["flight"]["id"] == "f1"
        assert data["curated"]["best_value"]["flight"]["airline"] == "British Airways"


# ==============================================================================
# SEARCH HOTELS TESTS
# ==============================================================================


class TestSearchHotels:
    """Tests for /search-hotels endpoint."""

    def test_search_hotels_not_implemented(self, capabilities_module):
        """Test that hotel search returns not implemented error."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-hotels",
                json={
                    "city": "Paris",
                    "country": "France",
                    "check_in": "2025-12-20",
                    "check_out": "2025-12-27",
                    "rooms": 1,
                    "adults": 2,
                },
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "not yet implemented" in data["error"]


# ==============================================================================
# INPUT VALIDATION TESTS
# ==============================================================================


class TestInputValidation:
    """Tests for request validation."""

    def test_empty_query_rejected(self, capabilities_module):
        """Test that empty query is rejected."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/resolve-location",
                json={"query": ""},
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422

    def test_empty_date_expression_rejected(self, capabilities_module):
        """Test that empty date expression is rejected."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/parse-dates",
                json={"expression": ""},
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422

    def test_invalid_passenger_count_rejected(self, capabilities_module):
        """Test that invalid passenger counts are rejected."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-flights",
                json={
                    "origin_iata": "AMS",
                    "destination_iata": "CDG",
                    "departure_date": "2025-12-20",
                    "adults": 0,  # Invalid - must be >= 1
                },
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422

    def test_missing_required_fields_rejected(self, capabilities_module):
        """Test that missing required fields are rejected."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            # Missing origin_iata
            response = client.post(
                "/search-flights",
                json={
                    "destination_iata": "CDG",
                    "departure_date": "2025-12-20",
                    "adults": 1,
                },
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422

    def test_invalid_iata_length_rejected(self, capabilities_module):
        """Test that IATA codes must be exactly 3 characters."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-flights",
                json={
                    "origin_iata": "AB",  # Invalid - must be 3 chars
                    "destination_iata": "CDG",
                    "departure_date": "2025-12-20",
                    "adults": 1,
                },
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422

    def test_hotel_search_invalid_room_count_rejected(self, capabilities_module):
        """Test that invalid room count for hotels is rejected."""
        mock_settings = MagicMock()
        mock_settings.ENVIRONMENT = "development"
        mock_settings.N8N_CAPABILITIES_API_KEY = "test-key"  # pragma: allowlist secret

        with patch.object(capabilities_module, "settings", mock_settings):
            app = FastAPI()
            app.include_router(capabilities_module.router)
            client = TestClient(app)

            response = client.post(
                "/search-hotels",
                json={
                    "city": "Paris",
                    "country": "France",
                    "check_in": "2025-12-20",
                    "check_out": "2025-12-27",
                    "rooms": 0,  # Invalid
                    "adults": 2,
                },
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 422


__all__ = [
    "TestAuthentication",
    "TestInputValidation",
    "TestSearchHotels",
]
