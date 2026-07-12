"""Unit tests for SessionState model."""

from app.ai.base.session_state import SessionState, SessionType


class TestSessionState:
    """Tests for SessionState Pydantic model."""

    def test_create_flight_session(self) -> None:
        """Test creating a flight session state."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
        )

        assert state.session_id == "chat_123"
        assert state.user_id == "user_456"
        assert state.session_type == SessionType.FLIGHT
        assert state.collected == {}
        assert state.waiting_for_field is None
        assert state.booking_stage is None

    def test_create_hotel_session(self) -> None:
        """Test creating a hotel session state."""
        state = SessionState(
            session_id="chat_789",
            user_id="user_101",
            session_type=SessionType.HOTEL,
        )

        assert state.session_type == SessionType.HOTEL
        assert state.pending_disambiguation is None

    def test_create_with_collected_data(self) -> None:
        """Test creating session with initial collected data."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
            collected={
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "2025-01-15",
            },
        )

        assert state.collected["origin"] == "LHR"
        assert state.collected["destination"] == "CDG"
        assert state.collected["departure_date"] == "2025-01-15"

    def test_update_collected(self) -> None:
        """Test updating collected fields."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
            collected={"origin": "LHR"},
        )

        original_updated = state.updated_at
        state.update_collected(destination="CDG", passengers=2)

        assert state.collected["origin"] == "LHR"
        assert state.collected["destination"] == "CDG"
        assert state.collected["passengers"] == 2
        assert state.updated_at > original_updated

    def test_update_collected_filters_none(self) -> None:
        """Test that update_collected filters out None values."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
            collected={"origin": "LHR"},
        )

        state.update_collected(destination="CDG", return_date=None)

        assert state.collected["destination"] == "CDG"
        assert "return_date" not in state.collected

    def test_clear_collector_state(self) -> None:
        """Test clearing collector state."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
            waiting_for_field="destination",
            waiting_for_airport_selection="origin",
            pending_date_range={"start": "2025-01-15"},
            last_question="Where are you flying to?",
        )

        state.clear_collector_state()

        assert state.waiting_for_field is None
        assert state.waiting_for_airport_selection is None
        assert state.pending_date_range is None
        assert state.last_question is None
        # collected should remain unchanged
        assert state.collected == {}

    def test_to_mongo_dict(self) -> None:
        """Test conversion to MongoDB document."""
        state = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT,
            collected={"origin": "LHR"},
            waiting_for_field="destination",
        )

        doc = state.to_mongo_dict()

        assert doc["session_id"] == "chat_123"
        assert doc["user_id"] == "user_456"
        assert doc["session_type"] == "flight"
        assert doc["collected"] == {"origin": "LHR"}
        assert doc["waiting_for_field"] == "destination"
        assert "created_at" in doc
        assert "updated_at" in doc

    def test_from_mongo_dict(self) -> None:
        """Test creation from MongoDB document."""
        doc = {
            "session_id": "chat_123",
            "user_id": "user_456",
            "session_type": "flight",
            "collected": {"origin": "LHR", "destination": "CDG"},
            "waiting_for_field": None,
            "waiting_for_airport_selection": None,
            "pending_date_range": None,
            "pending_disambiguation": None,
            "last_question": None,
            "booking_stage": "search",
            "selected_option_index": None,
            "context": {},
            "created_at": "2025-01-01T12:00:00+00:00",
            "updated_at": "2025-01-01T12:30:00+00:00",
        }

        state = SessionState.from_mongo_dict(doc)

        assert state.session_id == "chat_123"
        assert state.session_type == SessionType.FLIGHT
        assert state.collected["origin"] == "LHR"
        assert state.booking_stage == "search"

    def test_roundtrip_serialization(self) -> None:
        """Test that to_mongo_dict and from_mongo_dict are inverse operations."""
        original = SessionState(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.HOTEL,
            collected={"city": "Paris", "check_in": "2025-02-01"},
            waiting_for_field="check_out",
            booking_stage="field_collection",
            context={"source": "chat"},
        )

        doc = original.to_mongo_dict()
        restored = SessionState.from_mongo_dict(doc)

        assert restored.session_id == original.session_id
        assert restored.user_id == original.user_id
        assert restored.session_type == original.session_type
        assert restored.collected == original.collected
        assert restored.waiting_for_field == original.waiting_for_field
        assert restored.booking_stage == original.booking_stage
        assert restored.context == original.context


class TestSessionType:
    """Tests for SessionType enum."""

    def test_flight_value(self) -> None:
        """Test FLIGHT enum value."""
        assert SessionType.FLIGHT.value == "flight"

    def test_hotel_value(self) -> None:
        """Test HOTEL enum value."""
        assert SessionType.HOTEL.value == "hotel"

    def test_from_string(self) -> None:
        """Test creating enum from string."""
        assert SessionType("flight") == SessionType.FLIGHT
        assert SessionType("hotel") == SessionType.HOTEL
