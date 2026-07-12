"""Unit tests for passenger API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.api.user import (
    get_passenger,
    list_passengers,
    remove_passenger,
    store_passenger,
    update_passenger_endpoint,
)
from app.domains.common.enums import AuthProvider
from app.domains.passenger import (
    PassengerCreate,
    PassengerMasked,
    PassengerResponse,
    PassengerUpdate,
)
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


@pytest.fixture
def current_user() -> UserPublic:
    """Authenticated user for passenger endpoints."""
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
def passenger_create() -> PassengerCreate:
    """Valid create payload."""
    return PassengerCreate(
        title="Mr",
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-15",
        nationality="US",
        passport_number="AB1234567",  # pragma: allowlist secret
        passport_expiry="2028-05-15",
    )


@pytest.fixture
def passenger_response() -> PassengerResponse:
    """Mock full (decrypted) response for include_sensitive=True."""
    now = datetime.now(UTC)
    return PassengerResponse(
        id="507f1f77bcf86cd799439022",  # pragma: allowlist secret
        user_id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        is_primary=True,
        title="Mr",
        hotel_title="Mr",
        type_hotel="adult",
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-15",
        nationality="US",
        email=None,
        phone=None,
        passport_number="AB1234567",  # pragma: allowlist secret
        passport_expiry="2028-05-15",
        passport_country="US",
        frequent_flyer_number=None,
        type=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def passenger_masked() -> PassengerMasked:
    """Mock masked response."""
    now = datetime.now(UTC)
    return PassengerMasked(
        id="507f1f77bcf86cd799439022",  # pragma: allowlist secret
        user_id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        is_primary=True,
        title="Mr",
        hotel_title="Mr",
        type_hotel="adult",
        first_name="John",
        last_name="Doe",
        date_of_birth="1990-01-15",
        nationality="US",
        email=None,
        phone=None,
        passport_number="****4567",
        passport_expiry="2028-**-**",
        passport_country=None,
        frequent_flyer_number=None,
        type=None,
        created_at=now,
        updated_at=now,
    )


class TestStorePassenger:
    """Tests for POST /me/passengers."""

    @pytest.mark.asyncio
    async def test_store_success(
        self, current_user, passenger_create, passenger_masked
    ):
        """Successful store returns masked passenger."""
        with patch(
            "app.api.user.create_passenger", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = passenger_masked
            result = await store_passenger(passenger_create, current_user)
        assert result.id == passenger_masked.id
        assert result.passport_number == "****4567"
        mock_create.assert_called_once_with(str(current_user.id), passenger_create)

    @pytest.mark.asyncio
    async def test_store_duplicate_key_returns_409(
        self, current_user, passenger_masked
    ):
        """DuplicateKeyError from unique partial index returns 409 Conflict."""
        with patch(
            "app.api.user.create_passenger", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = DuplicateKeyError("E11000 duplicate key")
            with pytest.raises(HTTPException) as exc_info:
                await store_passenger(
                    PassengerCreate(
                        title="Mr",
                        first_name="Jane",
                        last_name="Doe",
                        date_of_birth="1990-01-15",
                        nationality="US",
                        is_primary=True,
                    ),
                    current_user,
                )
        assert exc_info.value.status_code == 409
        assert "primary" in exc_info.value.detail.lower()


class TestListPassengers:
    """Tests for GET /me/passengers."""

    @pytest.mark.asyncio
    async def test_list_empty(self, current_user):
        """Empty list returns []."""
        with patch(
            "app.api.user.get_passengers_for_user", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []
            result = await list_passengers(current_user)
        assert result == []
        mock_get.assert_called_once_with(str(current_user.id))

    @pytest.mark.asyncio
    async def test_list_with_items(self, current_user, passenger_masked):
        """List returns masked passengers."""
        with patch(
            "app.api.user.get_passengers_for_user", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [passenger_masked]
            result = await list_passengers(current_user)
        assert len(result) == 1
        assert result[0].first_name == "John"


class TestGetPassenger:
    """Tests for GET /me/passengers/{id}."""

    @pytest.mark.asyncio
    async def test_get_not_found(self, current_user):
        """404 when passenger not found."""
        with patch(
            "app.api.user.get_passenger_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                await get_passenger(
                    "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                    current_user,
                    include_sensitive=False,
                    x_pii_view_token=None,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_success(self, current_user, passenger_masked):
        """Returns masked by default."""
        with patch(
            "app.api.user.get_passenger_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = passenger_masked
            result = await get_passenger(
                "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                current_user,
                include_sensitive=False,
                x_pii_view_token=None,
            )
        assert result.passport_number == "****4567"

    @pytest.mark.asyncio
    async def test_get_with_include_sensitive_returns_decrypted(
        self, current_user, passenger_response
    ):
        """include_sensitive=True returns PassengerResponse with a valid PII token."""
        with (
            patch(
                "app.api.user.get_passenger_by_id", new_callable=AsyncMock
            ) as mock_get,
            patch("app.api.user.verify_pii_view_token") as mock_verify_token,
        ):
            mock_get.return_value = passenger_response
            mock_verify_token.return_value = str(current_user.id)
            result = await get_passenger(
                "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                current_user,
                include_sensitive=True,
                x_pii_view_token="valid-pii-token",
            )
        assert isinstance(result, PassengerResponse)
        assert result.passport_number == "AB1234567"  # pragma: allowlist secret
        assert result.passport_expiry == "2028-05-15"
        mock_verify_token.assert_called_once_with("valid-pii-token")
        mock_get.assert_called_once_with(
            "507f1f77bcf86cd799439022",  # pragma: allowlist secret
            str(current_user.id),
            include_sensitive=True,
        )

    @pytest.mark.asyncio
    async def test_get_with_include_sensitive_invalid_token_returns_403(
        self, current_user
    ):
        """include_sensitive=True requires a valid PII token."""
        with patch("app.api.user.verify_pii_view_token") as mock_verify_token:
            mock_verify_token.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_passenger(
                    "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                    current_user,
                    include_sensitive=True,
                    x_pii_view_token="expired-token",
                )

        assert exc_info.value.status_code == 403
        assert "Invalid or expired verification" in exc_info.value.detail


class TestUpdatePassenger:
    """Tests for PUT /me/passengers/{id}."""

    @pytest.mark.asyncio
    async def test_update_not_found(self, current_user):
        """404 when passenger not found."""
        with patch(
            "app.api.user.update_passenger", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                await update_passenger_endpoint(
                    "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                    PassengerUpdate(first_name="Jane"),
                    current_user,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_success(self, current_user, passenger_masked):
        """Successful update returns masked passenger."""
        with patch(
            "app.api.user.update_passenger", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = passenger_masked
            result = await update_passenger_endpoint(
                "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                PassengerUpdate(first_name="Jane"),
                current_user,
            )
        assert result.id == passenger_masked.id
        assert result.first_name == "John"  # fixture has first_name
        assert result.passport_number == "****4567"
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_is_primary_forwards_to_repository(
        self, current_user, passenger_masked
    ):
        """Update with is_primary=True is passed to repository (clears others)."""
        with patch(
            "app.api.user.update_passenger", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = passenger_masked
            await update_passenger_endpoint(
                "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                PassengerUpdate(is_primary=True),
                current_user,
            )
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        update_data = call_args[0][2]
        assert update_data.is_primary is True


class TestRemovePassenger:
    """Tests for DELETE /me/passengers/{id}."""

    @pytest.mark.asyncio
    async def test_delete_not_found(self, current_user):
        """404 when passenger not found."""
        with patch(
            "app.api.user.delete_passenger", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = False
            with pytest.raises(HTTPException) as exc_info:
                await remove_passenger(
                    "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                    current_user,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_success(self, current_user):
        """Success returns message."""
        with patch(
            "app.api.user.delete_passenger", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True
            result = await remove_passenger(
                "507f1f77bcf86cd799439022",  # pragma: allowlist secret
                current_user,
            )
        assert result.message == "Passenger deleted"
