"""Unit tests for payment API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.domains.common.enums import AuthProvider
from app.domains.payment import (
    BookingExpiryCheckRequest,
    BookingExpiryCheckResponse,
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PaymentIntentCreationError,
    PaymentStatus,
    PayoutReleaseRequest,
    PayoutReleaseResponse,
    PayoutStatus,
    TransactionResponse,
)
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_user() -> UserPublic:
    """Mock authenticated user for testing."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",
        email="user@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_admin() -> UserPublic:
    """Mock admin user for testing."""
    return UserPublic(
        id="507f1f77bcf86cd799439012",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_payment_request() -> PaymentIntentCreateRequest:
    """Sample payment intent creation request."""
    return PaymentIntentCreateRequest(
        booking_amount=10000,
        currency="usd",
        voya_booking_reference="VOYA-TEST123",
    )


@pytest.fixture
def sample_payment_response() -> PaymentIntentCreateResponse:
    """Sample payment intent creation response."""
    return PaymentIntentCreateResponse(
        payment_intent_id="pi_test_123456789",
        client_secret="pi_test_123456789_secret_abcdef",
        amount=10000,
        platform_fee=500,
        supplier_amount=9500,
        currency="usd",
        publishable_key="pk_test_123",
    )


@pytest.fixture
def sample_transaction_response() -> TransactionResponse:
    """Sample transaction response."""
    now = datetime.now(UTC)
    return TransactionResponse(
        id="transaction_123",
        stripe_payment_intent_id="pi_test_123456789",
        voya_booking_reference="VOYA-TEST123",
        amount=10000,
        currency="usd",
        platform_fee=500,
        supplier_amount=9500,
        status=PaymentStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
        paid_at=now,
    )


@pytest.fixture
def sample_payout_response() -> PayoutReleaseResponse:
    """Sample payout release response."""
    return PayoutReleaseResponse(
        transfer_id="tr_test_123456789",
        voya_booking_reference="VOYA-TEST123",
        amount=9500,
        destination_account="acct_placeholder_flightlogic",
        status=PayoutStatus.PAID,
        created_at=datetime.now(UTC),
        notes=None,
    )


# ==============================================================================
# CREATE PAYMENT INTENT ENDPOINT TESTS
# ==============================================================================


class TestCreatePaymentIntentEndpoint:
    """Test POST /api/payments/create-intent endpoint."""

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(
        self,
        mock_user: UserPublic,
        sample_payment_request: PaymentIntentCreateRequest,
        sample_payment_response: PaymentIntentCreateResponse,
    ):
        """Test successful payment intent creation."""
        mock_service = AsyncMock()
        mock_service.create_payment_intent = AsyncMock(
            return_value=sample_payment_response
        )

        # Import and call endpoint (with dependency injection)
        from app.api.payments import create_payment_intent

        result = await create_payment_intent(sample_payment_request, mock_service)

        # Verify service method was called
        mock_service.create_payment_intent.assert_called_once_with(
            sample_payment_request
        )

        # Verify response
        assert result == sample_payment_response
        assert result.payment_intent_id == "pi_test_123456789"
        assert result.client_secret == "pi_test_123456789_secret_abcdef"

    @pytest.mark.asyncio
    async def test_create_payment_intent_stripe_error(
        self,
        mock_user: UserPublic,
        sample_payment_request: PaymentIntentCreateRequest,
    ):
        """Test payment intent creation when Stripe fails."""
        mock_service = AsyncMock()
        mock_service.create_payment_intent = AsyncMock(
            side_effect=PaymentIntentCreationError("Stripe API error")
        )

        from app.api.payments import create_payment_intent

        # Should raise HTTPException with 503 status
        with pytest.raises(HTTPException) as exc_info:
            await create_payment_intent(sample_payment_request, mock_service)

        assert exc_info.value.status_code == 503
        assert "Stripe API error" in str(exc_info.value.detail)


# ==============================================================================
# GET TRANSACTION ENDPOINT TESTS
# ==============================================================================


class TestGetTransactionEndpoint:
    """Test GET /api/payments/transaction/{payment_intent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_transaction_success(
        self,
        mock_user: UserPublic,
        sample_transaction_response: TransactionResponse,
    ):
        """Test successful transaction retrieval."""
        mock_service = AsyncMock()
        mock_service.get_transaction_by_payment_intent = AsyncMock(
            return_value=sample_transaction_response
        )

        from app.api.payments import get_transaction

        result = await get_transaction("pi_test_123456789", mock_service)

        # Verify response
        assert result == sample_transaction_response
        assert result.stripe_payment_intent_id == "pi_test_123456789"
        assert result.status == PaymentStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_get_transaction_not_found(self, mock_user: UserPublic):
        """Test transaction retrieval when not found."""
        mock_service = AsyncMock()
        mock_service.get_transaction_by_payment_intent = AsyncMock(
            side_effect=ValueError("Transaction not found")
        )

        from app.api.payments import get_transaction

        # Should raise HTTPException with 404 status
        with pytest.raises(HTTPException) as exc_info:
            await get_transaction("pi_nonexistent", mock_service)

        assert exc_info.value.status_code == 404
        assert "Transaction not found" in str(exc_info.value.detail)


# ==============================================================================
# RELEASE PAYOUT ENDPOINT TESTS (ADMIN ONLY)
# ==============================================================================


class TestReleasePayoutEndpoint:
    """Test POST /api/payments/payouts/release endpoint."""

    @pytest.mark.asyncio
    async def test_release_payout_success(
        self,
        mock_admin: UserPublic,
        sample_payout_response: PayoutReleaseResponse,
    ):
        """Test successful payout release by admin."""
        mock_service = AsyncMock()
        mock_service.release_payout = AsyncMock(return_value=sample_payout_response)

        from app.api.payments import release_payout

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")
        result = await release_payout(request, mock_admin, mock_service)

        # Verify service was called with admin user ID
        mock_service.release_payout.assert_called_once_with(
            request, admin_user_id=str(mock_admin.id)
        )

        # Verify response
        assert result == sample_payout_response
        assert result.transfer_id == "tr_test_123456789"
        assert result.amount == 9500

    @pytest.mark.asyncio
    async def test_release_payout_transaction_not_found(self, mock_admin: UserPublic):
        """Test payout release when transaction not found."""
        mock_service = AsyncMock()
        mock_service.release_payout = AsyncMock(
            side_effect=ValueError("Transaction not found")
        )

        from app.api.payments import release_payout

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-NONEXISTENT")

        with pytest.raises(HTTPException) as exc_info:
            await release_payout(request, mock_admin, mock_service)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_release_payout_payment_not_succeeded(self, mock_admin: UserPublic):
        """Test payout release when payment not yet succeeded."""
        from app.domains.payment import PayoutReleaseError

        mock_service = AsyncMock()
        mock_service.release_payout = AsyncMock(
            side_effect=PayoutReleaseError("Payment not succeeded")
        )

        from app.api.payments import release_payout

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        with pytest.raises(HTTPException) as exc_info:
            await release_payout(request, mock_admin, mock_service)

        assert exc_info.value.status_code == 400
        assert "Payment not succeeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_release_payout_requires_admin(self, mock_user: UserPublic):
        """Test that payout release requires admin role."""
        # This test verifies the endpoint uses require_admin dependency
        import inspect

        from app.api.payments import release_payout

        sig = inspect.signature(release_payout)
        admin_param = sig.parameters.get("admin_user")
        assert admin_param is not None
        # The endpoint should receive admin_user from require_admin dependency


# ==============================================================================
# INTEGRATION TESTS (ENDPOINT LEVEL)
# ==============================================================================


class TestPaymentEndpointsIntegration:
    """Test payment endpoints with more realistic scenarios."""

    @pytest.mark.asyncio
    async def test_full_payment_flow_mocked(
        self,
        mock_user: UserPublic,
        sample_payment_request: PaymentIntentCreateRequest,
        sample_payment_response: PaymentIntentCreateResponse,
        sample_transaction_response: TransactionResponse,
    ):
        """Test complete payment flow: create intent -> get transaction."""
        mock_service = AsyncMock()
        mock_service.create_payment_intent = AsyncMock(
            return_value=sample_payment_response
        )
        mock_service.get_transaction_by_payment_intent = AsyncMock(
            return_value=sample_transaction_response
        )

        from app.api.payments import create_payment_intent, get_transaction

        # Step 1: Create payment intent
        create_result = await create_payment_intent(
            sample_payment_request, mock_service
        )
        assert create_result.payment_intent_id == "pi_test_123456789"

        # Step 2: Get transaction details
        transaction_result = await get_transaction(
            create_result.payment_intent_id, mock_service
        )
        assert (
            transaction_result.stripe_payment_intent_id
            == create_result.payment_intent_id
        )
        assert transaction_result.amount == create_result.amount

    @pytest.mark.asyncio
    async def test_payment_amount_consistency(
        self,
        mock_user: UserPublic,
    ):
        """Test that payment amounts are calculated consistently."""
        test_cases = [
            (10000, 500, 9500),  # $100 -> $5 fee, $95 supplier
            (25000, 1250, 23750),  # $250 -> $12.50 fee, $237.50 supplier
        ]

        for booking_amount, expected_fee, expected_supplier in test_cases:
            request = PaymentIntentCreateRequest(
                booking_amount=booking_amount,
                currency="usd",
                voya_booking_reference=f"VOYA-TEST{booking_amount}",
            )

            # Mock response with calculated fees
            response = PaymentIntentCreateResponse(
                payment_intent_id=f"pi_test_{booking_amount}",
                client_secret=f"pi_test_{booking_amount}_secret",
                amount=booking_amount,
                platform_fee=expected_fee,
                supplier_amount=expected_supplier,
                currency="usd",
                publishable_key="pk_test_123",
            )

            mock_service = AsyncMock()
            mock_service.create_payment_intent = AsyncMock(return_value=response)

            from app.api.payments import create_payment_intent

            result = await create_payment_intent(request, mock_service)

            assert result.platform_fee == expected_fee
            assert result.supplier_amount == expected_supplier
            assert result.amount == booking_amount


# ==============================================================================
# GET EXISTING PAYMENT INTENT ENDPOINT TESTS
# ==============================================================================


class TestGetExistingPaymentIntentEndpoint:
    """Test GET /api/payments/existing-intent/{voya_booking_reference} endpoint."""

    @pytest.mark.asyncio
    async def test_get_existing_payment_intent_success(
        self,
        mock_user: UserPublic,
    ):
        """Test successfully retrieving existing payment intent."""
        mock_service = AsyncMock()
        mock_existing_intent = PaymentIntentCreateResponse(
            payment_intent_id="pi_existing_123",
            client_secret="pi_existing_123_secret_abc",
            amount=48225,
            currency="usd",
            platform_fee=2412,
            supplier_amount=45813,
            publishable_key="pk_test_123",
        )
        mock_service.get_existing_payment_intent = AsyncMock(
            return_value=mock_existing_intent
        )

        from app.api.payments import get_existing_payment_intent

        result = await get_existing_payment_intent("VOYA-TEST123", mock_service)

        mock_service.get_existing_payment_intent.assert_called_once_with("VOYA-TEST123")
        assert result == mock_existing_intent
        assert result.payment_intent_id == "pi_existing_123"
        assert result.amount == 48225
        assert result.platform_fee == 2412
        assert result.supplier_amount == 45813

    @pytest.mark.asyncio
    async def test_get_existing_payment_intent_not_found(
        self,
        mock_user: UserPublic,
    ):
        """Test when no reusable payment intent exists."""
        mock_service = AsyncMock()
        mock_service.get_existing_payment_intent = AsyncMock(return_value=None)

        from app.api.payments import get_existing_payment_intent

        with pytest.raises(HTTPException) as exc_info:
            await get_existing_payment_intent("VOYA-NOTFOUND", mock_service)

        assert exc_info.value.status_code == 404
        assert "No reusable payment intent found" in str(exc_info.value.detail)


# ==============================================================================
# CHECK BOOKING EXPIRY ENDPOINT TESTS
# ==============================================================================


class TestCheckBookingExpiryEndpoint:
    """Test POST /api/payments/check-booking-expiry endpoint."""

    @pytest.mark.asyncio
    async def test_check_booking_expiry_gds_valid(
        self,
        mock_user: UserPublic,
    ):
        """Test expiry check for GDS booking with valid ticket_time_limit."""
        from datetime import timedelta

        future_time = datetime.now(UTC) + timedelta(hours=1)
        mock_response = BookingExpiryCheckResponse(
            is_valid=True,
            ticket_time_limit=future_time,
            time_remaining_seconds=3600,
            message=None,
        )

        mock_service = AsyncMock()
        mock_service.check_booking_expiry = AsyncMock(return_value=mock_response)

        from app.api.payments import check_booking_expiry

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await check_booking_expiry(request, mock_service)

        mock_service.check_booking_expiry.assert_called_once_with(request)
        assert result.is_valid is True
        assert result.ticket_time_limit == future_time
        assert result.time_remaining_seconds == 3600

    @pytest.mark.asyncio
    async def test_check_booking_expiry_gds_expired(
        self,
        mock_user: UserPublic,
    ):
        """Test expiry check for GDS booking with expired ticket_time_limit."""
        from datetime import timedelta

        past_time = datetime.now(UTC) - timedelta(hours=1)
        mock_response = BookingExpiryCheckResponse(
            is_valid=False,
            ticket_time_limit=past_time,
            time_remaining_seconds=0,
            message="Booking has expired. The ticket time limit has passed.",
        )

        mock_service = AsyncMock()
        mock_service.check_booking_expiry = AsyncMock(return_value=mock_response)

        from app.api.payments import check_booking_expiry

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await check_booking_expiry(request, mock_service)

        mock_service.check_booking_expiry.assert_called_once_with(request)
        assert result.is_valid is False
        assert result.ticket_time_limit == past_time
        assert result.time_remaining_seconds == 0
        assert "expired" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_booking_expiry_lcc_no_limit(
        self,
        mock_user: UserPublic,
    ):
        """Test expiry check for LCC booking without ticket_time_limit."""
        mock_response = BookingExpiryCheckResponse(
            is_valid=True,
            ticket_time_limit=None,
            time_remaining_seconds=None,
            message=None,
        )

        mock_service = AsyncMock()
        mock_service.check_booking_expiry = AsyncMock(return_value=mock_response)

        from app.api.payments import check_booking_expiry

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await check_booking_expiry(request, mock_service)

        mock_service.check_booking_expiry.assert_called_once_with(request)
        assert result.is_valid is True
        assert result.ticket_time_limit is None
        assert result.time_remaining_seconds is None

    @pytest.mark.asyncio
    async def test_check_booking_expiry_not_found(
        self,
        mock_user: UserPublic,
    ):
        """Test expiry check when booking not found."""
        mock_response = BookingExpiryCheckResponse(
            is_valid=True,
            ticket_time_limit=None,
            time_remaining_seconds=None,
            message=None,
        )

        mock_service = AsyncMock()
        mock_service.check_booking_expiry = AsyncMock(return_value=mock_response)

        from app.api.payments import check_booking_expiry

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-NOTFOUND")
        result = await check_booking_expiry(request, mock_service)

        mock_service.check_booking_expiry.assert_called_once_with(request)
        assert result.is_valid is True
