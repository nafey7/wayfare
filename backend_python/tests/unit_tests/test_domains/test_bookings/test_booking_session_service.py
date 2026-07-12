"""Unit tests for BookingSessionService MongoDB persistence."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.domains.booking_sessions.service import BookingSessionService


class SampleEnum(Enum):
    """Sample enum for serialization testing."""

    ECONOMY = "economy"
    BUSINESS = "business"


class TestEnum(Enum):
    """Test enum for complex serialization testing."""

    ECONOMY = "economy"
    BUSINESS = "business"


class MockPydanticModel:
    """Mock Pydantic model for testing serialization."""

    def __init__(self, name: str, price: Decimal):
        self.name = name
        self.price = price

    def model_dump(self) -> dict[str, Any]:
        return {"name": self.name, "price": self.price}


class TestBookingSessionServiceSerialization:
    """Test MongoDB serialization of complex objects."""

    def test_serialize_primitives(self):
        """Test serialization of primitive types."""
        data = {
            "string": "test",
            "int": 123,
            "float": 45.67,
            "bool": True,
            "none": None,
        }

        result = BookingSessionService._serialize_for_mongo(data)

        assert result == data
        assert isinstance(result["string"], str)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["bool"], bool)
        assert result["none"] is None

    def test_serialize_decimal(self):
        """Test Decimal serialization to float."""
        data = {"price": Decimal("50.62"), "tax": Decimal("15.50")}

        result = BookingSessionService._serialize_for_mongo(data)

        assert result["price"] == 50.62
        assert result["tax"] == 15.50
        assert isinstance(result["price"], float)
        assert isinstance(result["tax"], float)

    def test_serialize_nested_decimal(self):
        """Test nested Decimal serialization."""
        data = {
            "flight": {
                "price": Decimal("500.00"),
                "fees": {"booking": Decimal("25.00"), "service": Decimal("10.50")},
                "segments": [{"cost": Decimal("250.00")}, {"cost": Decimal("250.00")}],
            }
        }

        result = BookingSessionService._serialize_for_mongo(data)

        assert result["flight"]["price"] == 500.00
        assert result["flight"]["fees"]["booking"] == 25.00
        assert result["flight"]["fees"]["service"] == 10.50
        assert result["flight"]["segments"][0]["cost"] == 250.00
        assert result["flight"]["segments"][1]["cost"] == 250.00

        # Verify all are floats
        assert isinstance(result["flight"]["price"], float)
        assert isinstance(result["flight"]["fees"]["booking"], float)
        assert isinstance(result["flight"]["segments"][0]["cost"], float)

    def test_serialize_enum(self):
        """Test Enum serialization to value."""
        data = {
            "class": SampleEnum.BUSINESS,
            "options": [SampleEnum.ECONOMY, SampleEnum.BUSINESS],
        }

        result = BookingSessionService._serialize_for_mongo(data)

        assert result["class"] == "business"
        assert result["options"] == ["economy", "business"]
        assert isinstance(result["class"], str)

    def test_serialize_dates(self):
        """Test date and datetime serialization."""
        test_date = date(2025, 3, 15)
        test_datetime = datetime(2025, 3, 15, 14, 30, 0)

        data = {"departure_date": test_date, "created_at": test_datetime}

        result = BookingSessionService._serialize_for_mongo(data)

        assert result["departure_date"] == "2025-03-15"
        assert result["created_at"] == "2025-03-15T14:30:00"
        assert isinstance(result["departure_date"], str)
        assert isinstance(result["created_at"], str)

    def test_serialize_pydantic_model(self):
        """Test Pydantic model serialization."""
        model = MockPydanticModel("Test Flight", Decimal("100.50"))
        data = {"flight_info": model}

        result = BookingSessionService._serialize_for_mongo(data)

        assert result["flight_info"]["name"] == "Test Flight"
        assert result["flight_info"]["price"] == 100.50
        assert isinstance(result["flight_info"]["price"], float)

    def test_serialize_complex_nested_structure(self):
        """Test complex nested structure with multiple types."""
        data = {
            "booking_id": "BK123",
            "status": TestEnum.ECONOMY,
            "flight_data": {
                "price": Decimal("450.75"),
                "departure": date(2025, 6, 1),
                "segments": [
                    {
                        "cost": Decimal("225.00"),
                        "class": TestEnum.BUSINESS,
                        "time": datetime(2025, 6, 1, 9, 30),
                    }
                ],
            },
            "metadata": {
                "created": datetime.now(),
                "fees": [Decimal("10.00"), Decimal("5.50")],
            },
        }

        result = BookingSessionService._serialize_for_mongo(data)

        # Verify all types are properly serialized
        assert isinstance(result["booking_id"], str)
        assert isinstance(result["status"], str)
        assert isinstance(result["flight_data"]["price"], float)
        assert isinstance(result["flight_data"]["departure"], str)
        assert isinstance(result["flight_data"]["segments"][0]["cost"], float)
        assert isinstance(result["flight_data"]["segments"][0]["class"], str)
        assert isinstance(result["flight_data"]["segments"][0]["time"], str)
        assert isinstance(result["metadata"]["created"], str)
        assert isinstance(result["metadata"]["fees"][0], float)
        assert isinstance(result["metadata"]["fees"][1], float)

    def test_serialize_object_with_dict(self):
        """Test object with __dict__ serialization."""

        class TestObject:
            def __init__(self):
                self.name = "test"
                self.price = Decimal("50.00")
                self.nested = {"value": Decimal("25.00")}

        obj = TestObject()
        result = BookingSessionService._serialize_for_mongo(obj)

        assert result["name"] == "test"
        assert result["price"] == 50.00
        assert result["nested"]["value"] == 25.00
        assert isinstance(result["price"], float)


class TestBookingSessionServiceCRUD:
    """Test CRUD operations for BookingSessionService."""

    @pytest.fixture
    def mock_collection(self):
        """Mock MongoDB collection."""
        collection = Mock()
        collection.update_one = AsyncMock()
        collection.find_one = AsyncMock()
        collection.delete_one = AsyncMock()
        collection.delete_many = AsyncMock()
        collection.count_documents = AsyncMock()
        collection.find = Mock()
        return collection

    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "selected_flight": {"flight_id": "FL123"},
            "search_params": {"origin": "AMS", "destination": "LHR"},
            "selected_option": 1,
            "price": Decimal("299.99"),
            "class": TestEnum.ECONOMY,
            "timestamp": datetime.now(),
        }

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_store_session_success(
        self, mock_get_connection, mock_collection, sample_session_data
    ):
        """Test successful session storage."""
        # Setup mocks
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db
        mock_collection.update_one.return_value = Mock(upserted_id="new_id")

        # Test store_session
        result = await BookingSessionService.store_session(
            session_id="test_session",
            user_id="test_user",
            session_data=sample_session_data,
            ttl_hours=2,
        )

        assert result is True
        mock_collection.update_one.assert_called_once()

        # Verify the call arguments
        call_args = mock_collection.update_one.call_args
        filter_arg, update_arg = call_args[0]

        assert filter_arg == {"session_id": "test_session"}
        assert update_arg["$set"]["session_id"] == "test_session"
        assert update_arg["$set"]["user_id"] == "test_user"
        assert isinstance(
            update_arg["$set"]["data"]["price"], float
        )  # Decimal converted
        assert update_arg["$set"]["data"]["class"] == "economy"  # Enum converted

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_store_session_failure(self, mock_get_connection, mock_collection):
        """Test session storage failure."""
        # Setup mocks to raise exception
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db
        mock_collection.update_one.side_effect = Exception("Database error")

        result = await BookingSessionService.store_session(
            session_id="test_session",
            user_id="test_user",
            session_data={"test": "data"},
        )

        assert result is False

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_get_session_success(self, mock_get_connection, mock_collection):
        """Test successful session retrieval."""
        # Setup mocks
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db

        mock_session_doc = {
            "session_id": "test_session",
            "user_id": "test_user",
            "data": {"flight_id": "FL123"},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_collection.find_one.return_value = mock_session_doc

        result = await BookingSessionService.get_session("test_session")

        assert result is not None
        assert result["session_id"] == "test_session"
        assert result["user_id"] == "test_user"
        assert result["data"]["flight_id"] == "FL123"

        # Verify query includes expiry check
        call_args = mock_collection.find_one.call_args[0][0]
        assert call_args["session_id"] == "test_session"
        assert "$gt" in call_args["expires_at"]

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_get_session_not_found(self, mock_get_connection, mock_collection):
        """Test session not found."""
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db
        mock_collection.find_one.return_value = None

        result = await BookingSessionService.get_session("nonexistent_session")

        assert result is None

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_update_session_data_success(
        self, mock_get_connection, mock_collection
    ):
        """Test successful session data update."""
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db

        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        updates = {"booking_stage": "passenger_details", "price": Decimal("350.00")}

        result = await BookingSessionService.update_session_data(
            "test_session", updates
        )

        assert result is True

        # Verify update query
        call_args = mock_collection.update_one.call_args
        filter_arg, update_arg = call_args[0]

        assert filter_arg["session_id"] == "test_session"
        assert "$gt" in filter_arg["expires_at"]
        assert update_arg["$set"]["data.booking_stage"] == "passenger_details"
        assert update_arg["$set"]["data.price"] == 350.00  # Decimal converted

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_delete_session_success(self, mock_get_connection, mock_collection):
        """Test successful session deletion."""
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db

        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        result = await BookingSessionService.delete_session("test_session")

        assert result is True
        mock_collection.delete_one.assert_called_once_with(
            {"session_id": "test_session"}
        )

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_cleanup_expired_sessions(self, mock_get_connection, mock_collection):
        """Test cleanup of expired sessions."""
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db

        mock_result = Mock()
        mock_result.deleted_count = 5
        mock_collection.delete_many.return_value = mock_result

        result = await BookingSessionService.cleanup_expired_sessions()

        assert result == 5

        # Verify cleanup query
        call_args = mock_collection.delete_many.call_args[0][0]
        assert "$lte" in call_args["expires_at"]

    @patch("app.domains.booking_sessions.service.get_connection")
    async def test_get_session_stats(self, mock_get_connection, mock_collection):
        """Test session statistics retrieval."""
        mock_db = Mock()
        mock_db.booking_sessions = mock_collection
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Mock count queries
        mock_collection.count_documents.side_effect = [10, 7]  # total, active

        result = await BookingSessionService.get_session_stats()

        assert result["total_sessions"] == 10
        assert result["active_sessions"] == 7
        assert result["expired_sessions"] == 3

        # Verify both count queries were called
        assert mock_collection.count_documents.call_count == 2


class TestBookingSessionServiceEdgeCases:
    """Test edge cases and error conditions."""

    def test_serialize_empty_data(self):
        """Test serialization of empty/null data."""
        assert BookingSessionService._serialize_for_mongo({}) == {}
        assert BookingSessionService._serialize_for_mongo([]) == []
        assert BookingSessionService._serialize_for_mongo(None) is None
        assert BookingSessionService._serialize_for_mongo("") == ""

    def test_serialize_circular_reference_protection(self):
        """Test that circular references don't cause infinite loops."""
        # Create circular reference
        data = {"self": None}
        data["self"] = data

        # This should not hang or crash
        with pytest.raises((RecursionError, ValueError)):
            BookingSessionService._serialize_for_mongo(data)

    def test_serialize_very_nested_structure(self):
        """Test deeply nested structure serialization."""
        # Create 10-level nested structure with Decimals
        data = {"level": Decimal("1.0")}
        current = data

        for i in range(2, 11):
            current["nested"] = {"level": Decimal(f"{i}.0")}
            current = current["nested"]

        result = BookingSessionService._serialize_for_mongo(data)

        # Verify all levels serialized properly
        current_result = result
        for i in range(1, 11):
            assert current_result["level"] == float(i)
            if i < 10:
                current_result = current_result["nested"]
