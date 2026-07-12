"""Unit tests for ChatService auto-save itinerary on generation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.chat.service import ChatService
from app.domains.saved_itinerary import SavedItineraryCreate, SavedItineraryResponse
from app.domains.user.schemas import UserPublic


@pytest.fixture
def mock_user() -> UserPublic:
    """Create mock user for testing."""
    from app.domains.common.enums import AuthProvider
    from app.domains.user.enums import UserRole, UserStatus

    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def itinerary_results_response() -> dict:
    """Supervisor result that produces itinerary_results."""
    return {
        "agent": "itinerary",
        "type": "itinerary_results",
        "message": "Here's your 3-day trip to Paris!",
        "intent": "create_itinerary",
        "confidence": 0.95,
        "message_id": "msg-123",
        "metadata": {
            "structured_itinerary": {
                "itineraryItems": [
                    {"day": 1, "title": "Day 1", "description": "First day"}
                ]
            },
        },
        "origin": "LHR",
        "destination": "Paris",
        "departure_date": "2026-06-01",
        "return_date": "2026-06-05",
        "adults": 2,
    }


@pytest.fixture
def _patch_conversation_metadata():
    """Patch conversation metadata calls added for the multi-conversation feature.

    These hit MongoDB via `get_database()` which isn't connected in unit tests.
    Patched at a single place so every test in this module gets consistent
    behavior (no auto-naming side effects, no DB hits).
    """
    with (
        patch(
            "app.domains.chat.service.repository.update_conversation_on_message",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.chat.service.ChatService._get_conversation_doc",
            new_callable=AsyncMock,
            return_value=None,  # None → skips auto-naming branch
        ),
    ):
        yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_conversation_metadata")
class TestChatServiceAutoSaveItinerary:
    """Tests for auto-save when itinerary_results is returned."""

    async def test_creates_saved_itinerary_and_adds_id_to_response(
        self, mock_user: UserPublic, itinerary_results_response: dict
    ):
        """When itinerary_results returned, upsert_saved_itinerary_for_chat runs and saved_itinerary_id is in response."""
        now = datetime.now(UTC)
        saved_response = SavedItineraryResponse(
            id="507f1f77bcf86cd799439022",  # pragma: allowlist secret
            structured_itinerary={},
            trip_meta=None,
            created_at=now,
            updated_at=now,
        )

        with (
            patch(
                "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                new_callable=AsyncMock,
                return_value=itinerary_results_response,
            ),
            patch(
                "app.domains.chat.service.upsert_saved_itinerary_for_chat",
                new_callable=AsyncMock,
                return_value=saved_response,
            ) as mock_upsert,
            patch(
                "app.domains.chat.service.repository.get_or_create_chat_conversation",
                new_callable=AsyncMock,
                return_value="chat-123",
            ),
            patch(
                "app.domains.chat.service.repository.create_message",
                new_callable=AsyncMock,
            ),
        ):
            chat_service = ChatService()
            response = await chat_service.process_message(
                "Plan a trip to Paris",
                mock_user,
                chat_id="chat-123",
            )

            assert response.type == "itinerary_results"
            assert response.data is not None
            assert response.data.get("saved_itinerary_id") == saved_response.id

            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args
            assert call_args[0][0] == str(mock_user.id)
            assert call_args[0][1] == "chat-123"
            payload = call_args[0][2]
            assert isinstance(payload, SavedItineraryCreate)
            assert hasattr(payload, "structured_itinerary")
            assert payload.structured_itinerary["itineraryItems"] == [
                {"day": 1, "title": "Day 1", "description": "First day"}
            ]
            assert payload.trip_meta is not None
            assert payload.trip_meta.get("origin") == "LHR"
            assert payload.trip_meta.get("destination") == "Paris"

    async def test_returns_itinerary_without_id_when_save_fails(
        self, mock_user: UserPublic, itinerary_results_response: dict
    ):
        """On save failure, response still returned but without saved_itinerary_id."""
        with (
            patch(
                "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                new_callable=AsyncMock,
                return_value=itinerary_results_response,
            ),
            patch(
                "app.domains.chat.service.upsert_saved_itinerary_for_chat",
                new_callable=AsyncMock,
                side_effect=Exception("DB error"),
            ),
            patch(
                "app.domains.chat.service.repository.get_or_create_chat_conversation",
                new_callable=AsyncMock,
                return_value="chat-123",
            ),
            patch(
                "app.domains.chat.service.repository.create_message",
                new_callable=AsyncMock,
            ),
        ):
            chat_service = ChatService()
            response = await chat_service.process_message(
                "Plan a trip to Paris",
                mock_user,
                chat_id="chat-123",
            )

            assert response.type == "itinerary_results"
            assert response.data is not None
            assert response.data.get("saved_itinerary_id") is None
            assert response.data.get("structured_itinerary") is not None

    async def test_chain_only_itinerary_triggers_upsert_and_id_in_response(
        self, mock_user: UserPublic
    ):
        """When primary type is not itinerary_results but chain includes itinerary, still upsert."""
        now = datetime.now(UTC)
        saved_response = SavedItineraryResponse(
            id="507f1f77bcf86cd799439033",  # pragma: allowlist secret
            structured_itinerary={},
            trip_meta=None,
            created_at=now,
            updated_at=now,
        )
        supervisor_result = {
            "agent": "hotel",
            "type": "hotel_search_results",
            "message": "Hotels in Paris",
            "intent": "hotel_conversation",
            "confidence": 0.9,
            "message_id": "msg-chain",
            "chain_responses": [
                {
                    "type": "flight_search_results",
                    "message": "Flights",
                },
                {
                    "type": "itinerary_results",
                    "message": "Your plan",
                    "metadata": {
                        "structured_itinerary": {
                            "itineraryItems": [{"day": 1, "title": "Day 1"}],
                        },
                    },
                    "origin": "LHR",
                    "destination": "Paris",
                },
            ],
        }
        with (
            patch(
                "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                new_callable=AsyncMock,
                return_value=supervisor_result,
            ),
            patch(
                "app.domains.chat.service.upsert_saved_itinerary_for_chat",
                new_callable=AsyncMock,
                return_value=saved_response,
            ) as mock_upsert,
            patch(
                "app.domains.chat.service.repository.get_or_create_chat_conversation",
                new_callable=AsyncMock,
                return_value="chat-123",
            ),
            patch(
                "app.domains.chat.service.repository.create_message",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            chat_service = ChatService()
            response = await chat_service.process_message(
                "Book everything",
                mock_user,
                chat_id="chat-123",
            )

            assert response.type == "hotel_search_results"
            assert response.data is not None
            assert response.data.get("saved_itinerary_id") == saved_response.id
            mock_upsert.assert_called_once()

            # Persisted bot message action_data must include saved_itinerary_id (reload parity)
            create_calls = [
                c
                for c in mock_create.call_args_list
                if c.kwargs.get("content") == {"text": "Hotels in Paris"}
            ]
            assert len(create_calls) == 1
            assert (
                create_calls[0].kwargs.get("action_data", {}).get("saved_itinerary_id")
                == saved_response.id
            )

    async def test_two_chain_itineraries_uses_last_by_chain_index(
        self, mock_user: UserPublic
    ):
        """When chain has two top-level itinerary_results, auto-save uses the last by index."""
        now = datetime.now(UTC)
        saved_response = SavedItineraryResponse(
            id="507f1f77bcf86cd799439044",  # pragma: allowlist secret
            structured_itinerary={},
            trip_meta=None,
            created_at=now,
            updated_at=now,
        )
        supervisor_result = {
            "agent": "hotel",
            "type": "hotel_search_results",
            "message": "Hotels in Paris",
            "intent": "hotel_conversation",
            "confidence": 0.9,
            "message_id": "msg-chain-2",
            "chain_responses": [
                {
                    "type": "itinerary_results",
                    "message": "First plan",
                    "metadata": {
                        "structured_itinerary": {
                            "itineraryItems": [{"day": 1, "title": "Paris"}],
                        },
                    },
                    "origin": "LHR",
                    "destination": "Paris",
                },
                {
                    "type": "itinerary_results",
                    "message": "Second plan",
                    "metadata": {
                        "structured_itinerary": {
                            "itineraryItems": [{"day": 1, "title": "Rome"}],
                        },
                    },
                    "origin": "LHR",
                    "destination": "Rome",
                },
            ],
        }
        with (
            patch(
                "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                new_callable=AsyncMock,
                return_value=supervisor_result,
            ),
            patch(
                "app.domains.chat.service.upsert_saved_itinerary_for_chat",
                new_callable=AsyncMock,
                return_value=saved_response,
            ) as mock_upsert,
            patch(
                "app.domains.chat.service.repository.get_or_create_chat_conversation",
                new_callable=AsyncMock,
                return_value="chat-123",
            ),
            patch(
                "app.domains.chat.service.repository.create_message",
                new_callable=AsyncMock,
            ),
        ):
            chat_service = ChatService()
            await chat_service.process_message(
                "Book everything",
                mock_user,
                chat_id="chat-123",
            )

            mock_upsert.assert_called_once()
            payload = mock_upsert.call_args[0][2]
            assert isinstance(payload, SavedItineraryCreate)
            assert payload.structured_itinerary["itineraryItems"] == [
                {"day": 1, "title": "Rome"},
            ]
            assert payload.trip_meta is not None
            assert payload.trip_meta.get("destination") == "Rome"
