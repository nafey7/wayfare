"""Unit tests for user discount eligibility API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.user import (
    DISCOUNT_AMOUNT,
    MIN_BOOKING_AMOUNT,
    PROMOTION_END_DATE,
    UseDiscountRequest,
    check_discount_eligibility,
    use_discount,
)
from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def eligible_user() -> UserPublic:
    """Mock new user eligible for discount (signed up after feature launch)."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,  # Set to True during signup for new users
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def ineligible_user() -> UserPublic:
    """Mock user who has already used the discount or is an existing user."""
    return UserPublic(
        id="507f1f77bcf86cd799439012",  # pragma: allowlist secret
        email="used@example.com",
        first_name="Used",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=False,  # Default False for existing users or after discount used
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def existing_user_no_field() -> UserPublic:
    """Mock existing user who doesn't have the discount_eligible field (pre-feature)."""
    # This simulates existing users in DB who don't have the field - defaults to False
    return UserPublic(
        id="507f1f77bcf86cd799439013",  # pragma: allowlist secret
        email="existing@example.com",
        first_name="Existing",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        # discount_eligible defaults to False in schema for existing users
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ==============================================================================
# DISCOUNT ELIGIBILITY CHECK TESTS
# ==============================================================================


class TestCheckDiscountEligibility:
    """Tests for the discount eligibility check endpoint."""

    @pytest.mark.asyncio
    async def test_eligible_user_returns_eligible(self, eligible_user: UserPublic):
        """Test that eligible user receives eligible response."""
        # Mock datetime to be before promotion end date
        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            response = await check_discount_eligibility(eligible_user)

        assert response.eligible is True
        assert response.discount_amount == DISCOUNT_AMOUNT
        assert response.min_booking_amount == MIN_BOOKING_AMOUNT
        assert "Eligible" in response.reason

    @pytest.mark.asyncio
    async def test_ineligible_user_returns_ineligible(
        self, ineligible_user: UserPublic
    ):
        """Test that user who already used discount is ineligible."""
        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            response = await check_discount_eligibility(ineligible_user)

        assert response.eligible is False
        assert "already been used" in response.reason

    @pytest.mark.asyncio
    async def test_promotion_ended_returns_ineligible(self, eligible_user: UserPublic):
        """Test that user is ineligible after promotion end date."""
        # Mock datetime to be after April 1, 2026
        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 2, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            response = await check_discount_eligibility(eligible_user)

        assert response.eligible is False
        assert "ended" in response.reason

    @pytest.mark.asyncio
    async def test_existing_user_defaults_to_ineligible(
        self, existing_user_no_field: UserPublic
    ):
        """Test that existing users (without field) default to ineligible."""
        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            response = await check_discount_eligibility(existing_user_no_field)

        # Existing users default to discount_eligible=False
        assert response.eligible is False
        assert "already been used" in response.reason


# ==============================================================================
# USE DISCOUNT TESTS
# ==============================================================================


class TestUseDiscount:
    """Tests for the use discount endpoint."""

    @pytest.mark.asyncio
    async def test_use_discount_success(self, eligible_user: UserPublic):
        """Test successful discount usage (atomic update)."""
        request = UseDiscountRequest(booking_amount=700.0)

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch("app.domains.user.repository") as mock_repo:
                mock_repo.use_discount_atomic = AsyncMock(return_value=eligible_user)

                response = await use_discount(request, eligible_user)

        assert response.message == "$50 discount applied successfully"
        mock_repo.use_discount_atomic.assert_called_once_with(eligible_user.id)

    @pytest.mark.asyncio
    async def test_use_discount_already_used(self, ineligible_user: UserPublic):
        """Test discount usage when already used."""
        request = UseDiscountRequest(booking_amount=700.0)

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with pytest.raises(HTTPException) as exc_info:
                await use_discount(request, ineligible_user)

        assert exc_info.value.status_code == 400
        assert "already been used" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_use_discount_booking_too_small(self, eligible_user: UserPublic):
        """Test discount usage with booking amount below minimum."""
        request = UseDiscountRequest(booking_amount=500.0)  # Below $600 minimum

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with pytest.raises(HTTPException) as exc_info:
                await use_discount(request, eligible_user)

        assert exc_info.value.status_code == 400
        assert "at least $600" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_use_discount_promotion_ended(self, eligible_user: UserPublic):
        """Test discount usage after promotion end date."""
        request = UseDiscountRequest(booking_amount=700.0)

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 2, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with pytest.raises(HTTPException) as exc_info:
                await use_discount(request, eligible_user)

        assert exc_info.value.status_code == 400
        assert "ended" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_use_discount_exact_minimum_amount(self, eligible_user: UserPublic):
        """Test discount usage with exactly the minimum booking amount."""
        request = UseDiscountRequest(booking_amount=600.0)  # Exactly $600 minimum

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch("app.domains.user.repository") as mock_repo:
                mock_repo.use_discount_atomic = AsyncMock(return_value=eligible_user)

                response = await use_discount(request, eligible_user)

        assert response.message == "$50 discount applied successfully"

    @pytest.mark.asyncio
    async def test_use_discount_atomic_returns_none(self, eligible_user: UserPublic):
        """Test discount usage when atomic update returns None (already used or race)."""
        request = UseDiscountRequest(booking_amount=700.0)

        with patch("app.api.user.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch("app.domains.user.repository") as mock_repo:
                mock_repo.use_discount_atomic = AsyncMock(return_value=None)

                with pytest.raises(HTTPException) as exc_info:
                    await use_discount(request, eligible_user)

        assert exc_info.value.status_code == 400
        assert "already been used or user not found" in exc_info.value.detail


# ==============================================================================
# CONSTANTS TESTS
# ==============================================================================


class TestDiscountConstants:
    """Tests for discount-related constants."""

    def test_discount_amount_is_50(self):
        """Verify discount amount is $50."""
        assert DISCOUNT_AMOUNT == 50.0

    def test_min_booking_amount_is_600(self):
        """Verify minimum booking amount is $600."""
        assert MIN_BOOKING_AMOUNT == 600.0

    def test_promotion_end_date_is_april_2026(self):
        """Verify promotion ends on April 1, 2026."""
        assert PROMOTION_END_DATE.year == 2026
        assert PROMOTION_END_DATE.month == 4
        assert PROMOTION_END_DATE.day == 1
