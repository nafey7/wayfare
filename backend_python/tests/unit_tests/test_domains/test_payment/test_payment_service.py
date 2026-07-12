"""Unit tests for PaymentService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import stripe
from bson import ObjectId

from app.database.models.transaction import TransactionModel
from app.domains.payment import (
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PaymentIntentCreationError,
    PaymentService,
    PaymentStatus,
    PaymentValidationError,
    PayoutReleaseError,
    PayoutReleaseRequest,
    PayoutReleaseResponse,
    PayoutStatus,
    TransactionResponse,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_repository():
    """Mock PaymentRepository for testing."""
    # Create a sample TransactionModel for return values
    now = datetime.now(UTC)
    mock_transaction = TransactionModel(
        id=ObjectId(),
        stripe_payment_intent_id="pi_test_123456789",
        voya_booking_reference="VOYA-TEST123",
        user_id=ObjectId(),
        amount=10000,
        currency="usd",
        platform_fee=500,
        supplier_amount=9500,
        destination_account_id="acct_test",
        status=PaymentStatus.PENDING,
        created_at=now,
        updated_at=now,
    )

    repo = Mock()
    repo.create_transaction = AsyncMock(return_value=mock_transaction)
    repo.update_transaction_status = AsyncMock()
    repo.get_transaction_by_payment_intent = AsyncMock()
    repo.get_transaction_by_voya_reference = AsyncMock()
    return repo


@pytest.fixture
def mock_stripe_payment_intent():
    """Mock Stripe payment intent response."""
    return Mock(
        id="pi_test_123456789",
        client_secret="pi_test_123456789_secret_abcdef",
        amount=10000,
        currency="usd",
        status="requires_payment_method",
        metadata={
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": "user_123",
            "platform_fee": 500,
            "supplier_amount": 9500,
        },
    )


@pytest.fixture
def mock_stripe_transfer():
    """Mock Stripe transfer response."""
    return Mock(
        id="tr_test_123456789",
        amount=9500,
        currency="usd",
        destination="acct_1RnLvfPOhOFPCIcC",  # Voya test Connect account
        status="pending",
    )


@pytest.fixture
def sample_payment_request():
    """Sample payment intent creation request."""
    return PaymentIntentCreateRequest(
        booking_amount=10000,
        currency="usd",
        voya_booking_reference="VOYA-TEST123",
    )


@pytest.fixture
def sample_transaction_doc():
    """Sample transaction model."""
    now = datetime.now(UTC)
    return TransactionModel(
        id=ObjectId(),
        stripe_payment_intent_id="pi_test_123456789",
        stripe_charge_id="ch_test_123",
        stripe_transfer_id=None,
        refund_id=None,
        voya_booking_reference="VOYA-TEST123",
        user_id=ObjectId(),
        amount=10000,
        currency="usd",
        platform_fee=500,
        supplier_amount=9500,
        destination_account_id="acct_test",
        status=PaymentStatus.SUCCEEDED,
        payout_status=None,
        booking_created=False,
        created_at=now,
        updated_at=now,
        paid_at=now,
        refunded_at=None,
        payout_released_at=None,
        payout_released_by=None,
        payout_notes=None,
    )


# ==============================================================================
# PAYMENT INTENT CREATION TESTS
# ==============================================================================


class TestCreatePaymentIntent:
    """Test PaymentService.create_payment_intent()."""

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    @patch("app.domains.bookings.BookingService.update_payment_intent_id")
    async def test_create_payment_intent_success(
        self,
        mock_update_payment_intent_id,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
        sample_payment_request,
    ):
        """Test successful payment intent creation."""
        # Setup mocks
        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent
        # Mock LCC booking (no ticket_time_limit) - validation should be skipped
        mock_get_booking.return_value = None
        mock_update_payment_intent_id.return_value = None

        # Create service and call method
        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        result = await service.create_payment_intent(sample_payment_request)

        # Verify Stripe API was called correctly
        mock_stripe_create.assert_called_once()
        call_kwargs = mock_stripe_create.call_args[1]
        assert call_kwargs["amount"] == 10000
        assert call_kwargs["currency"] == "usd"
        # Note: application_fee_amount calculation changed - now extracted from total
        assert "application_fee_amount" in call_kwargs or "transfer_data" in call_kwargs
        assert call_kwargs["metadata"]["voya_booking_reference"] == "VOYA-TEST123"
        assert "user_id" in call_kwargs["metadata"]  # ObjectId will vary

        # Verify transaction was created in MongoDB
        mock_repository.create_transaction.assert_called_once()
        transaction_data = mock_repository.create_transaction.call_args[0][0]
        assert transaction_data["stripe_payment_intent_id"] == "pi_test_123456789"
        assert transaction_data["amount"] == 10000
        # Platform fee calculation changed: supplier = total * 0.95, fee = total - supplier
        # For 10000: supplier = 9500, fee = 500
        assert transaction_data["platform_fee"] == 500
        assert transaction_data["supplier_amount"] == 9500
        assert (
            transaction_data["status"] == PaymentStatus.PENDING
        )  # Now passes enum directly

        # Verify payment_intent_id is stored in booking event
        mock_update_payment_intent_id.assert_called_once_with(
            "VOYA-TEST123", "pi_test_123456789"
        )

        # Verify response
        assert isinstance(result, PaymentIntentCreateResponse)
        assert result.payment_intent_id == "pi_test_123456789"
        assert result.client_secret == "pi_test_123456789_secret_abcdef"
        assert result.amount == 10000
        assert result.platform_fee == 500
        assert result.supplier_amount == 9500
        assert result.publishable_key == "pk_test_123"

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_stripe_error(
        self,
        mock_get_booking,
        mock_stripe_create,
        mock_repository,
        sample_payment_request,
    ):
        """Test payment intent creation when Stripe API fails."""
        # Setup Stripe error
        mock_stripe_create.side_effect = stripe._error.StripeError("API Error")
        # Mock LCC booking (no ticket_time_limit) - validation should be skipped
        mock_get_booking.return_value = None

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        # Should raise PaymentIntentCreationError
        with pytest.raises(PaymentIntentCreationError) as exc_info:
            await service.create_payment_intent(sample_payment_request)

        assert "Failed to create payment intent" in str(exc_info.value)
        # Transaction should not be created if Stripe fails
        mock_repository.create_transaction.assert_not_called()

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    @patch("app.domains.bookings.BookingService.update_payment_intent_id")
    async def test_create_payment_intent_calculates_fees_correctly(
        self,
        mock_update_payment_intent_id,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
    ):
        """Test platform fee extraction from total_fare (which already includes platform fee).

        The new logic extracts supplier_amount and platform_fee from total_fare using
        Gross Margin Pricing: Supplier = Total * 0.95, Fee = Total - Supplier
        """
        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent
        # Mock LCC booking (no ticket_time_limit) - validation should be skipped
        mock_get_booking.return_value = None
        mock_update_payment_intent_id.return_value = None

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        # Test cases: (total_fare_with_fee, expected_supplier, expected_fee)
        # For flights: supplier = total * 0.95, fee = total - supplier
        test_cases = [
            (10500, 9975, 525),  # $105.00 total -> $99.75 supplier, $5.25 fee
            (26250, 24937, 1313),  # $262.50 total -> $249.37 supplier, $13.13 fee
            (105, 99, 6),  # $1.05 total -> $0.99 supplier, $0.06 fee
        ]

        for booking_amount, expected_supplier, expected_fee in test_cases:
            # Update mock to return correct amount
            mock_stripe_payment_intent.amount = booking_amount
            mock_stripe_payment_intent.id = f"pi_test_{booking_amount}"

            request = PaymentIntentCreateRequest(
                booking_amount=booking_amount,
                currency="usd",
                voya_booking_reference="VOYA-TEST",
            )

            result = await service.create_payment_intent(request)

            # Allow small rounding differences (within 1 cent)
            assert abs(result.platform_fee - expected_fee) <= 1, (
                f"Expected fee {expected_fee}, got {result.platform_fee} for amount {booking_amount}"
            )
            assert abs(result.supplier_amount - expected_supplier) <= 1, (
                f"Expected supplier {expected_supplier}, got {result.supplier_amount} for amount {booking_amount}"
            )
            assert result.amount == booking_amount

            # Verify payment_intent_id storage was attempted
            # (may fail if booking doesn't exist, which is OK)
            assert mock_update_payment_intent_id.called

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_without_user_id(
        self,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
        sample_payment_request,
    ):
        """Test payment intent creation without user_id (should still work)."""
        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent
        # Mock LCC booking (no ticket_time_limit) - validation should be skipped
        mock_get_booking.return_value = None

        # Service without user_id
        service = PaymentService()
        service.repository = mock_repository

        result = await service.create_payment_intent(sample_payment_request)

        # Should use "unknown" for user_id in metadata
        call_kwargs = mock_stripe_create.call_args[1]
        assert call_kwargs["metadata"]["user_id"] == "unknown"

        assert result.payment_intent_id == "pi_test_123456789"

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_gds_with_valid_ticket_time_limit(
        self,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
        sample_payment_request,
    ):
        """Test payment intent creation for GDS flight with valid ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse

        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent

        # Mock GDS booking with valid ticket_time_limit (future time)
        future_time = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=future_time,
            departure_airport_iata="JFK",
        )
        mock_get_booking.return_value = mock_gds_booking

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        result = await service.create_payment_intent(sample_payment_request)

        # Should succeed - ticket_time_limit is in the future
        assert result.payment_intent_id == "pi_test_123456789"
        mock_stripe_create.assert_called_once()

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_gds_with_expired_ticket_time_limit(
        self,
        mock_get_booking,
        mock_stripe_create,
        mock_repository,
        sample_payment_request,
    ):
        """Test payment intent creation for GDS flight with expired ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse

        # Mock GDS booking with expired ticket_time_limit (past time)
        past_time = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=past_time,
            departure_airport_iata="JFK",
        )
        mock_get_booking.return_value = mock_gds_booking

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        # Should raise PaymentIntentCreationError
        with pytest.raises(PaymentIntentCreationError) as exc_info:
            await service.create_payment_intent(sample_payment_request)

        assert "Booking has expired" in str(exc_info.value)
        assert "ticket time limit" in str(exc_info.value).lower()
        # Stripe should not be called if booking expired
        mock_stripe_create.assert_not_called()
        mock_repository.create_transaction.assert_not_called()

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_lcc_without_ticket_time_limit(
        self,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
        sample_payment_request,
    ):
        """Test payment intent creation for LCC flight without ticket_time_limit (validation skipped)."""
        from app.domains.bookings.schemas import BookingEventResponse

        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent

        # Mock LCC booking without ticket_time_limit (LCC flights don't have expiry)
        mock_lcc_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=None,  # LCC flights don't have ticket_time_limit
            departure_airport_iata=None,
        )
        mock_get_booking.return_value = mock_lcc_booking

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        result = await service.create_payment_intent(sample_payment_request)

        # Should succeed - validation is skipped when ticket_time_limit is None
        assert result.payment_intent_id == "pi_test_123456789"
        mock_stripe_create.assert_called_once()

    @patch("app.domains.payment.service.stripe.PaymentIntent.create")
    @patch("app.domains.payment.service.settings")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_create_payment_intent_non_flight_booking(
        self,
        mock_get_booking,
        mock_settings,
        mock_stripe_create,
        mock_repository,
        mock_stripe_payment_intent,
    ):
        """Test payment intent creation for non-flight booking (hotel) - validation skipped."""
        mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"
        mock_stripe_create.return_value = mock_stripe_payment_intent

        # Non-flight booking request
        hotel_request = PaymentIntentCreateRequest(
            booking_amount=10000,
            currency="usd",
            voya_booking_reference="VOYA-HOTEL123",
            booking_type="hotel",
        )

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        result = await service.create_payment_intent(hotel_request)

        # Should succeed - validation only applies to flight bookings
        assert result.payment_intent_id == "pi_test_123456789"
        # BookingService should not be called for non-flight bookings
        mock_get_booking.assert_not_called()


# ==============================================================================
# PAYMENT VALIDATION TESTS
# ==============================================================================


class TestValidatePaymentSucceeded:
    """Test PaymentService.validate_payment_succeeded()."""

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    async def test_validate_payment_succeeded_success(
        self, mock_stripe_retrieve, mock_repository, sample_transaction_doc
    ):
        """Test successful payment validation."""
        # Mock Stripe API response
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_123456789"
        mock_payment_intent.status = "succeeded"
        mock_stripe_retrieve.return_value = mock_payment_intent

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        # Should not raise exception
        await service.validate_payment_succeeded("pi_test_123456789")

        mock_stripe_retrieve.assert_called_once_with("pi_test_123456789")

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    async def test_validate_payment_not_found(
        self, mock_stripe_retrieve, mock_repository
    ):
        """Test payment validation when payment intent not found."""
        # Mock Stripe API error
        mock_stripe_retrieve.side_effect = stripe._error.InvalidRequestError(
            "No such payment_intent", "payment_intent"
        )

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(PaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("pi_nonexistent")

        assert "Payment validation failed" in str(exc_info.value)

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    async def test_validate_payment_not_succeeded(
        self, mock_stripe_retrieve, mock_repository, sample_transaction_doc
    ):
        """Test payment validation when payment is pending."""
        # Mock Stripe API response with pending status
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_123456789"
        mock_payment_intent.status = "pending"
        mock_stripe_retrieve.return_value = mock_payment_intent

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(PaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("pi_test_123456789")

        assert "Payment not completed" in str(exc_info.value)
        assert "pending" in str(exc_info.value)

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    async def test_validate_payment_failed(
        self, mock_stripe_retrieve, mock_repository, sample_transaction_doc
    ):
        """Test payment validation when payment failed."""
        # Mock Stripe API response with failed status
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test_123456789"
        mock_payment_intent.status = "failed"
        mock_stripe_retrieve.return_value = mock_payment_intent

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(PaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("pi_test_123456789")

        assert "Payment not completed" in str(exc_info.value)
        assert "failed" in str(exc_info.value)


# ==============================================================================
# PAYOUT RELEASE TESTS
# ==============================================================================


class TestReleasePayout:
    """Test PaymentService.release_payout()."""

    @patch("app.domains.payment.service.stripe.Transfer.create")
    async def test_release_payout_success(
        self,
        mock_stripe_transfer_create,
        mock_repository,
        sample_transaction_doc,
        mock_stripe_transfer,
    ):
        """Test successful payout release."""
        # Setup mocks
        mock_repository.get_transaction_by_voya_reference.return_value = (
            sample_transaction_doc
        )
        mock_stripe_transfer_create.return_value = mock_stripe_transfer

        service = PaymentService()
        service.repository = mock_repository

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        result = await service.release_payout(request, admin_user_id="admin_123")

        # Verify Stripe transfer was created
        mock_stripe_transfer_create.assert_called_once()
        transfer_kwargs = mock_stripe_transfer_create.call_args[1]
        assert transfer_kwargs["amount"] == 9500  # supplier_amount
        assert transfer_kwargs["currency"] == "usd"
        assert transfer_kwargs["destination"] == "acct_1RnLvfPOhOFPCIcC"
        assert transfer_kwargs["metadata"]["voya_booking_reference"] == "VOYA-TEST123"

        # Verify transaction was updated
        mock_repository.update_transaction_status.assert_called_once()
        update_kwargs = mock_repository.update_transaction_status.call_args[1]
        assert update_kwargs["payment_intent_id"] == "pi_test_123456789"
        assert update_kwargs["status"] == PaymentStatus.SUCCEEDED
        assert update_kwargs["stripe_transfer_id"] == "tr_test_123456789"
        assert update_kwargs["payout_status"] == PayoutStatus.PAID.value

        # Verify response
        assert isinstance(result, PayoutReleaseResponse)
        assert result.transfer_id == "tr_test_123456789"
        assert result.amount == 9500
        assert result.destination_account == "acct_1RnLvfPOhOFPCIcC"

    async def test_release_payout_payment_not_found(self, mock_repository):
        """Test payout release when payment not found."""
        mock_repository.get_transaction_by_voya_reference.side_effect = ValueError(
            "Transaction not found"
        )

        service = PaymentService()
        service.repository = mock_repository

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-NONEXISTENT")

        with pytest.raises(ValueError) as exc_info:
            await service.release_payout(request, admin_user_id="admin_123")

        assert "Transaction not found" in str(exc_info.value)

    async def test_release_payout_payment_not_succeeded(
        self, mock_repository, sample_transaction_doc
    ):
        """Test payout release when payment not yet succeeded."""
        # Create new transaction with PENDING status
        pending_transaction = TransactionModel(
            **{**sample_transaction_doc.model_dump(), "status": PaymentStatus.PENDING}
        )
        mock_repository.get_transaction_by_voya_reference.return_value = (
            pending_transaction
        )

        service = PaymentService()
        service.repository = mock_repository

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        with pytest.raises(PayoutReleaseError) as exc_info:
            await service.release_payout(request, admin_user_id="admin_123")

        assert "payment status" in str(exc_info.value).lower()

    @patch("app.domains.payment.service.stripe.Transfer.create")
    async def test_release_payout_stripe_error(
        self, mock_stripe_transfer_create, mock_repository, sample_transaction_doc
    ):
        """Test payout release when Stripe transfer fails."""
        mock_repository.get_transaction_by_voya_reference.return_value = (
            sample_transaction_doc
        )
        mock_stripe_transfer_create.side_effect = stripe._error.StripeError(
            "Transfer failed"
        )

        service = PaymentService()
        service.repository = mock_repository

        request = PayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        with pytest.raises(PayoutReleaseError) as exc_info:
            await service.release_payout(request, admin_user_id="admin_123")

        assert "Failed to create transfer" in str(exc_info.value)


# ==============================================================================
# GET TRANSACTION TESTS
# ==============================================================================


class TestGetTransaction:
    """Test PaymentService.get_transaction_by_payment_intent()."""

    async def test_get_transaction_success(
        self, mock_repository, sample_transaction_doc
    ):
        """Test successfully retrieving transaction."""
        # Create transaction with matching user_id
        user_id = ObjectId()
        transaction_with_user = TransactionModel(
            **{**sample_transaction_doc.model_dump(), "user_id": user_id}
        )
        mock_repository.get_transaction_by_payment_intent.return_value = (
            transaction_with_user
        )

        service = PaymentService(user_id=str(user_id))
        service.repository = mock_repository

        result = await service.get_transaction_by_payment_intent("pi_test_123456789")

        assert isinstance(result, TransactionResponse)
        assert result.stripe_payment_intent_id == "pi_test_123456789"
        assert result.amount == 10000
        assert result.platform_fee == 500
        assert result.supplier_amount == 9500
        assert result.status == PaymentStatus.SUCCEEDED

    async def test_get_transaction_not_found(self, mock_repository):
        """Test transaction retrieval when not found."""
        mock_repository.get_transaction_by_payment_intent.side_effect = ValueError(
            "Transaction not found"
        )

        service = PaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(ValueError) as exc_info:
            await service.get_transaction_by_payment_intent("pi_nonexistent")

        assert "Transaction not found" in str(exc_info.value)


# ==============================================================================
# BOOKING EXPIRY CHECK TESTS
# ==============================================================================


class TestCheckBookingExpiry:
    """Test PaymentService.check_booking_expiry()."""

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_check_booking_expiry_gds_valid(
        self, mock_get_booking, mock_repository
    ):
        """Test expiry check for GDS booking with valid ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse
        from app.domains.payment import BookingExpiryCheckRequest

        # Mock GDS booking with valid ticket_time_limit (future time)
        future_time = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=future_time,
            departure_airport_iata="JFK",
        )
        mock_get_booking.return_value = mock_gds_booking

        service = PaymentService()
        service.repository = mock_repository

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await service.check_booking_expiry(request)

        assert result.is_valid is True
        assert result.ticket_time_limit == future_time
        assert result.time_remaining_seconds > 0
        assert result.message is None

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_check_booking_expiry_gds_expired(
        self, mock_get_booking, mock_repository
    ):
        """Test expiry check for GDS booking with expired ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse
        from app.domains.payment import BookingExpiryCheckRequest

        # Mock GDS booking with expired ticket_time_limit (past time)
        past_time = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=past_time,
            departure_airport_iata="JFK",
        )
        mock_get_booking.return_value = mock_gds_booking

        service = PaymentService()
        service.repository = mock_repository

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await service.check_booking_expiry(request)

        assert result.is_valid is False
        assert result.ticket_time_limit == past_time
        assert result.time_remaining_seconds == 0
        assert result.message is not None
        assert "expired" in result.message.lower()

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_check_booking_expiry_lcc_no_limit(
        self, mock_get_booking, mock_repository
    ):
        """Test expiry check for LCC booking without ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse
        from app.domains.payment import BookingExpiryCheckRequest

        # Mock LCC booking without ticket_time_limit
        mock_lcc_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=None,  # LCC flights don't have ticket_time_limit
            departure_airport_iata=None,
        )
        mock_get_booking.return_value = mock_lcc_booking

        service = PaymentService()
        service.repository = mock_repository

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-TEST123")
        result = await service.check_booking_expiry(request)

        assert result.is_valid is True
        assert result.ticket_time_limit is None
        assert result.time_remaining_seconds is None
        assert result.message is None

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_check_booking_expiry_not_found(
        self, mock_get_booking, mock_repository
    ):
        """Test expiry check when booking not found."""
        from app.domains.payment import BookingExpiryCheckRequest

        # Mock booking not found
        mock_get_booking.return_value = None

        service = PaymentService()
        service.repository = mock_repository

        request = BookingExpiryCheckRequest(voya_booking_reference="VOYA-NOTFOUND")
        result = await service.check_booking_expiry(request)

        assert result.is_valid is True
        assert result.ticket_time_limit is None
        assert result.time_remaining_seconds is None
        assert result.message is None


# ==============================================================================
# GET EXISTING PAYMENT INTENT TESTS
# ==============================================================================


class TestGetExistingPaymentIntent:
    """Test PaymentService.get_existing_payment_intent()."""

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_get_existing_payment_intent_success(
        self,
        mock_get_booking,
        mock_stripe_retrieve,
        mock_repository,
    ):
        """Test successfully retrieving existing reusable payment intent."""
        from datetime import UTC, datetime

        from app.domains.bookings.schemas import BookingEventResponse

        # Mock booking event with payment_intent_id
        mock_booking = BookingEventResponse(
            id=str(ObjectId()),
            user_id=str(ObjectId()),
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            event_type="FLIGHT",
            payment_intent_id="pi_existing_123",
        )
        mock_get_booking.return_value = mock_booking

        # Mock Stripe payment intent (reusable status)
        mock_payment_intent = Mock(
            id="pi_existing_123",
            client_secret="pi_existing_123_secret_abc",
            amount=48225,  # $482.25
            currency="usd",
            status="requires_payment_method",
        )
        mock_stripe_retrieve.return_value = mock_payment_intent

        # Mock transaction
        now = datetime.now(UTC)
        mock_transaction = TransactionModel(
            id=ObjectId(),
            stripe_payment_intent_id="pi_existing_123",
            voya_booking_reference="VOYA-TEST123",
            user_id=ObjectId(),
            amount=48225,
            currency="usd",
            platform_fee=2412,  # $24.12
            supplier_amount=45813,  # $458.13
            destination_account_id="acct_test",
            status=PaymentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        mock_repository.get_transaction_by_payment_intent = AsyncMock(
            return_value=mock_transaction
        )

        service = PaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository

        result = await service.get_existing_payment_intent("VOYA-TEST123")

        assert result is not None
        assert result.payment_intent_id == "pi_existing_123"
        assert result.client_secret == "pi_existing_123_secret_abc"
        assert result.amount == 48225
        assert result.platform_fee == 2412
        assert result.supplier_amount == 45813
        mock_stripe_retrieve.assert_called_once_with("pi_existing_123")

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_get_existing_payment_intent_no_booking(
        self, mock_get_booking, mock_repository
    ):
        """Test when booking doesn't exist."""
        mock_get_booking.return_value = None

        service = PaymentService()
        service.repository = mock_repository

        result = await service.get_existing_payment_intent("VOYA-NOTFOUND")

        assert result is None

    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_get_existing_payment_intent_no_payment_intent_id(
        self, mock_get_booking, mock_repository
    ):
        """Test when booking exists but has no payment_intent_id."""
        from datetime import UTC, datetime

        from app.domains.bookings.schemas import BookingEventResponse

        mock_booking = BookingEventResponse(
            id=str(ObjectId()),
            user_id=str(ObjectId()),
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            event_type="FLIGHT",
            payment_intent_id=None,  # No payment intent
        )
        mock_get_booking.return_value = mock_booking

        service = PaymentService()
        service.repository = mock_repository

        result = await service.get_existing_payment_intent("VOYA-TEST123")

        assert result is None

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_get_existing_payment_intent_not_reusable_status(
        self,
        mock_get_booking,
        mock_stripe_retrieve,
        mock_repository,
    ):
        """Test when payment intent exists but is not in reusable status."""
        from datetime import UTC, datetime

        from app.domains.bookings.schemas import BookingEventResponse

        mock_booking = BookingEventResponse(
            id=str(ObjectId()),
            user_id=str(ObjectId()),
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            event_type="FLIGHT",
            payment_intent_id="pi_succeeded_123",
        )
        mock_get_booking.return_value = mock_booking

        # Mock Stripe payment intent (succeeded - not reusable)
        mock_payment_intent = Mock(
            id="pi_succeeded_123",
            client_secret="pi_succeeded_123_secret_abc",
            amount=48225,
            currency="usd",
            status="succeeded",  # Not reusable
        )
        mock_stripe_retrieve.return_value = mock_payment_intent

        service = PaymentService()
        service.repository = mock_repository

        result = await service.get_existing_payment_intent("VOYA-TEST123")

        assert result is None

    @patch("app.domains.payment.service.stripe.PaymentIntent.retrieve")
    @patch("app.domains.bookings.BookingService.get_latest_booking_by_voya_reference")
    async def test_get_existing_payment_intent_no_transaction_fallback(
        self,
        mock_get_booking,
        mock_stripe_retrieve,
        mock_repository,
    ):
        """Test when payment intent exists but transaction not found (fallback calculation)."""
        from datetime import UTC, datetime

        from app.domains.bookings.schemas import BookingEventResponse

        mock_booking = BookingEventResponse(
            id=str(ObjectId()),
            user_id=str(ObjectId()),
            voya_booking_reference="VOYA-TEST123",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            event_type="FLIGHT",
            payment_intent_id="pi_no_transaction_123",
        )
        mock_get_booking.return_value = mock_booking

        # Mock Stripe payment intent
        mock_payment_intent = Mock(
            id="pi_no_transaction_123",
            client_secret="pi_no_transaction_123_secret_abc",
            amount=48225,  # $482.25
            currency="usd",
            status="requires_payment_method",
        )
        mock_stripe_retrieve.return_value = mock_payment_intent

        # Mock transaction not found
        mock_repository.get_transaction_by_payment_intent = AsyncMock(return_value=None)

        service = PaymentService()
        service.repository = mock_repository

        result = await service.get_existing_payment_intent("VOYA-TEST123")

        assert result is not None
        assert result.payment_intent_id == "pi_no_transaction_123"
        assert result.amount == 48225
        # Should calculate fees from payment intent amount
        # fee = int(48225 * 0.05) = 2411, supplier = 48225 - 2411 = 45814
        assert result.supplier_amount == 45814
        assert result.platform_fee == 2411
