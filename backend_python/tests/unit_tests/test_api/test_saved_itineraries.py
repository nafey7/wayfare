"""Unit tests for saved itineraries API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.saved_itineraries import (
    delete_itinerary,
    get_itinerary,
    list_itineraries,
    save_itinerary,
)
from app.domains.common.enums import AuthProvider
from app.domains.saved_itinerary import (
    LinkedBookings,
    SavedItineraryCreate,
    SavedItineraryResponse,
)
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

# Test ID for non-existent itinerary (ObjectId format, not a real secret)
TEST_ITINERARY_ID = "507f1f77bcf86cd799439022"  # pragma: allowlist secret


@pytest.fixture
def current_user() -> UserPublic:
    """Authenticated user for itinerary endpoints."""
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
def saved_itinerary_create() -> SavedItineraryCreate:
    """Valid create payload."""
    return SavedItineraryCreate(
        structured_itinerary={
            "itineraryItems": [{"day": 1, "title": "Day 1", "description": "First day"}]
        },
        trip_meta={"destination": "Paris", "departure_date": "2025-06-01"},
    )


@pytest.fixture
def saved_itinerary_response() -> SavedItineraryResponse:
    """Mock response for saved itinerary."""
    now = datetime.now(UTC)
    return SavedItineraryResponse(
        id="507f1f77bcf86cd799439022",  # pragma: allowlist secret
        structured_itinerary={
            "itineraryItems": [{"day": 1, "title": "Day 1", "description": "First day"}]
        },
        trip_meta={"destination": "Paris", "departure_date": "2025-06-01"},
        created_at=now,
        updated_at=now,
    )


class TestSaveItinerary:
    """Tests for POST /itineraries."""

    @pytest.mark.asyncio
    async def test_save_success(
        self, current_user, saved_itinerary_create, saved_itinerary_response
    ):
        """Successful save returns saved itinerary."""
        with patch(
            "app.api.saved_itineraries.create_saved_itinerary",
            new_callable=AsyncMock,
            return_value=saved_itinerary_response,
        ) as mock_create:
            result = await save_itinerary(saved_itinerary_create, current_user)
            mock_create.assert_called_once_with(
                str(current_user.id), saved_itinerary_create
            )
            assert result.id == saved_itinerary_response.id
            assert (
                result.structured_itinerary
                == saved_itinerary_response.structured_itinerary
            )


class TestListItineraries:
    """Tests for GET /itineraries."""

    @pytest.mark.asyncio
    async def test_list_success(self, current_user, saved_itinerary_response):
        """Successful list returns itineraries."""
        with patch(
            "app.api.saved_itineraries.get_saved_itineraries_for_user",
            new_callable=AsyncMock,
            return_value=[saved_itinerary_response],
        ) as mock_list:
            result = await list_itineraries(current_user)
            mock_list.assert_called_once_with(str(current_user.id))
            assert len(result) == 1
            assert result[0].id == saved_itinerary_response.id

    @pytest.mark.asyncio
    async def test_list_includes_linked_bookings_when_enriched(
        self, current_user, saved_itinerary_response
    ):
        """List passes through linked_bookings from domain (Phase 4+)."""
        enriched = saved_itinerary_response.model_copy(
            update={
                "linked_bookings": LinkedBookings(
                    flight_voya_references=["VOYA-F1"],
                    hotel_voya_references=["VOYA-H1"],
                )
            }
        )
        with patch(
            "app.api.saved_itineraries.get_saved_itineraries_for_user",
            new_callable=AsyncMock,
            return_value=[enriched],
        ):
            result = await list_itineraries(current_user)
            assert result[0].linked_bookings.flight_voya_references == ["VOYA-F1"]
            assert result[0].linked_bookings.hotel_voya_references == ["VOYA-H1"]


class TestSavedItineraryCreatePayloadLimits:
    """SavedItineraryCreate rejects oversized or excessively nested JSON."""

    def test_rejects_structured_itinerary_over_max_json_bytes(self) -> None:
        big = "x" * (512 * 1024 + 1)
        with pytest.raises(ValidationError) as exc:
            SavedItineraryCreate(structured_itinerary={"blob": big})
        assert (
            "structured_itinerary" in str(exc.value).lower()
            or "bytes" in str(exc.value).lower()
        )

    def test_rejects_trip_meta_over_max_json_bytes(self) -> None:
        big = "x" * (128 * 1024 + 1)
        with pytest.raises(ValidationError) as exc:
            SavedItineraryCreate(
                structured_itinerary={"ok": True},
                trip_meta={"blob": big},
            )
        assert (
            "trip_meta" in str(exc.value).lower() or "bytes" in str(exc.value).lower()
        )

    def test_rejects_excessive_nesting(self) -> None:
        nested: dict = {"k": True}
        cur = nested
        for _ in range(40):
            cur["n"] = {}
            cur = cur["n"]
        with pytest.raises(ValidationError) as exc:
            SavedItineraryCreate(structured_itinerary=nested)
        assert "depth" in str(exc.value).lower()


class TestGetItinerary:
    """Tests for GET /itineraries/:id."""

    @pytest.mark.asyncio
    async def test_get_success(self, current_user, saved_itinerary_response):
        """Successful get returns itinerary."""
        with patch(
            "app.api.saved_itineraries.get_saved_itinerary_by_id",
            new_callable=AsyncMock,
            return_value=saved_itinerary_response,
        ) as mock_get:
            result = await get_itinerary(saved_itinerary_response.id, current_user)
            mock_get.assert_called_once_with(
                saved_itinerary_response.id, str(current_user.id)
            )
            assert result.id == saved_itinerary_response.id

    @pytest.mark.asyncio
    async def test_get_not_found(self, current_user):
        """Get returns 404 when itinerary not found."""
        with patch(
            "app.api.saved_itineraries.get_saved_itinerary_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_itinerary(TEST_ITINERARY_ID, current_user)
            assert exc_info.value.status_code == 404


class TestDeleteItinerary:
    """Tests for DELETE /itineraries/:id."""

    @pytest.mark.asyncio
    async def test_delete_success(self, current_user):
        """Successful delete returns 204."""
        with patch(
            "app.api.saved_itineraries.delete_saved_itinerary",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            await delete_itinerary(TEST_ITINERARY_ID, current_user)
            mock_delete.assert_called_once_with(TEST_ITINERARY_ID, str(current_user.id))

    @pytest.mark.asyncio
    async def test_delete_not_found(self, current_user):
        """Delete returns 404 when itinerary not found."""
        with patch(
            "app.api.saved_itineraries.delete_saved_itinerary",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_itinerary(TEST_ITINERARY_ID, current_user)
            assert exc_info.value.status_code == 404
