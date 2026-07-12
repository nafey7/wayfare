"""Unit tests for profile aggregate and preferences API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.user import (
    get_me_profile,
    update_me_preferences,
)
from app.domains.common.enums import AuthProvider
from app.domains.passenger.schemas import PassengerMasked
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import ProfileAggregateResponse
from app.domains.user_preferences import (
    FlightsPreferences,
    FlightsPreferencesUpdate,
    HotelsPreferences,
    PreferencesUpdateRequest,
    TravelStylePreferences,
    UserPreferencesResponse,
)


@pytest.fixture
def current_user():
    """Authenticated user for profile endpoints."""
    from app.domains.user.schemas import UserPublic

    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="John",
        last_name="Doe",
        profile_image="https://example.com/avatar.png",
        mobile="+15551234567",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_preferences():
    """Sample preferences response."""
    return UserPreferencesResponse(
        preference_chips=["Business Class", "4+ Hotel"],
        travel_style=TravelStylePreferences(
            travel_pace="relaxed",
            budget_mindset="bestValue",
            accommodation="noPref",
            activity_density="freeTime",
            primary_goals=["culture", "nature"],
            getting_around=["rideshare", "walking"],
        ),
        flights=FlightsPreferences(
            seat_preference="window",
            max_stops="nonstop",
            preferred_airlines=["British Airways"],
            departure_window=["00:00", "23:59"],
        ),
        hotels=HotelsPreferences(
            bed_type="king",
            room_type="standard",
            amenities=["breakfast", "gym"],
            hotel_style=[],
            location_preference=["cityCenter"],
            cancellation=["freeOnly"],
        ),
    )


@pytest.fixture
def sample_passengers(current_user):
    """Sample passengers with primary first."""
    now = datetime.now(UTC)
    return [
        PassengerMasked(
            id="p1",
            user_id=current_user.id,
            is_primary=True,
            title="Mr",
            hotel_title="Mr",
            type_hotel="adult",
            first_name="John",
            last_name="Doe",
            date_of_birth="1987-05-16",
            nationality="US",
            passport_number="****4589",
            passport_expiry="2028-**-**",
            passport_country="ES",
            created_at=now,
            updated_at=now,
        ),
        PassengerMasked(
            id="p2",
            user_id=current_user.id,
            is_primary=False,
            title="Mrs",
            hotel_title="Mrs",
            type_hotel="adult",
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1990-01-01",
            nationality="US",
            passport_number=None,
            passport_expiry=None,
            passport_country=None,
            created_at=now,
            updated_at=now,
        ),
    ]


class TestGetMeProfile:
    """Tests for GET /me/profile aggregate endpoint."""

    @pytest.mark.asyncio
    async def test_returns_full_profile(
        self, current_user, sample_preferences, sample_passengers
    ):
        """Returns user + preferences + passengers in one response."""
        user_model = MagicMock()
        user_model.id = current_user.id
        user_model.email = current_user.email
        user_model.first_name = current_user.first_name
        user_model.last_name = current_user.last_name
        user_model.profile_image = current_user.profile_image
        user_model.mobile = current_user.mobile
        user_model.status = "active"
        user_model.role = "user"
        user_model.email_verified = True
        user_model.auth_provider = "local"
        user_model.created_at = current_user.created_at
        user_model.updated_at = current_user.updated_at
        user_model.address = None  # Avoid Address validation in from_model
        user_model.timezone = None
        user_model.last_login = None
        user_model.is_tester = False
        user_model.photo_key = None

        with (
            patch("app.domains.user.service.repository") as mock_repo,
            patch(
                "app.domains.user_preferences.repository.get_preferences",
                new_callable=AsyncMock,
                return_value=sample_preferences,
            ),
            patch(
                "app.domains.passenger.repository.get_passengers_for_user",
                new_callable=AsyncMock,
                return_value=sample_passengers,
            ),
        ):
            mock_repo.get_user_by_id = AsyncMock(return_value=user_model)

            result = await get_me_profile(current_user)

        assert isinstance(result, ProfileAggregateResponse)
        assert result.user.id == current_user.id
        assert result.user.email == current_user.email
        assert result.user.first_name == "John"
        assert result.preferences.preference_chips == ["Business Class", "4+ Hotel"]
        assert result.preferences.flights.seat_preference == "window"
        assert len(result.passengers) == 2
        assert result.passengers[0].is_primary is True
        assert result.passengers[1].is_primary is False

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self, current_user):
        """Raises when user not found."""
        from app.domains.user.exceptions import UserNotFoundError

        with (
            patch("app.domains.user.service.repository") as mock_repo,
            patch(
                "app.domains.user_preferences.repository.get_preferences",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.passenger.repository.get_passengers_for_user",
                new_callable=AsyncMock,
            ),
        ):
            mock_repo.get_user_by_id = AsyncMock(return_value=None)

            with pytest.raises(UserNotFoundError) as exc_info:
                await get_me_profile(current_user)

        assert "not found" in str(exc_info.value).lower()


class TestUpdateMePreferences:
    """Tests for PUT /me/preferences endpoint."""

    @pytest.mark.asyncio
    async def test_upsert_preferences_partial(self, current_user, sample_preferences):
        """Partial update merges with existing."""
        request = PreferencesUpdateRequest(
            flights=FlightsPreferencesUpdate(seat_preference="aisle")
        )

        with patch(
            "app.api.user.upsert_preferences", new_callable=AsyncMock
        ) as mock_upsert:
            mock_upsert.return_value = sample_preferences

            result = await update_me_preferences(request, current_user)

        assert result.flights.seat_preference == "window"
        mock_upsert.assert_called_once_with(
            current_user.id,
            {"flights": {"seat_preference": "aisle"}},
        )

    @pytest.mark.asyncio
    async def test_empty_request_returns_current_preferences(
        self, current_user, sample_preferences
    ):
        """Empty body returns current preferences without update."""
        request = PreferencesUpdateRequest()

        with (
            patch(
                "app.api.user.get_preferences",
                new_callable=AsyncMock,
            ) as mock_get,
            patch(
                "app.api.user.upsert_preferences", new_callable=AsyncMock
            ) as mock_upsert,
        ):
            mock_get.return_value = sample_preferences

            result = await update_me_preferences(request, current_user)

        assert result == sample_preferences
        mock_get.assert_called_once_with(current_user.id)
        mock_upsert.assert_not_called()
