"""Unit tests for RevolutPaymentService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from bson import ObjectId

from app.database.models.transaction import TransactionModel
from app.domains.revolut_payment import (
    PaymentStatus,
    PayoutStatus,
    RevolutOrderCreateRequest,
    RevolutOrderCreateResponse,
    RevolutOrderCreationError,
    RevolutPaymentService,
    RevolutPaymentValidationError,
    RevolutPayoutReleaseError,
    RevolutPayoutReleaseRequest,
    RevolutPayoutReleaseResponse,
    RevolutTransactionResponse,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_repository():
    """Mock RevolutPaymentRepository for testing."""
    # Create a sample TransactionModel for return values
    now = datetime.now(UTC)
    mock_transaction = TransactionModel(
        id=ObjectId(),
        revolut_order_id="ord_test_123456789",
        voya_booking_reference="VOYA-TEST123",
        user_id=ObjectId(),
        amount=10000,
        currency="usd",
        platform_fee=500,
        supplier_amount=9500,
        destination_account_id="merchant_test",
        status=PaymentStatus.PENDING,
        payment_provider="revolut",
        created_at=now,
        updated_at=now,
    )

    repo = Mock()
    repo.create_transaction = AsyncMock(return_value=mock_transaction)
    repo.update_transaction_status = AsyncMock()
    repo.get_transaction_by_order_id = AsyncMock()
    repo.get_transaction_by_voya_reference = AsyncMock()
    repo.get_all_transactions_by_voya_reference = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_revolut_order():
    """Mock Revolut order response."""
    return {
        "id": "ord_test_123456789",
        "token": "token_test_abcdef",
        "state": "pending",
        "amount": 10000,
        "currency": "USD",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_order_request():
    """Sample order creation request."""
    return RevolutOrderCreateRequest(
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
        revolut_order_id="ord_test_123456789",
        voya_booking_reference="VOYA-TEST123",
        user_id=ObjectId(),
        amount=10000,
        currency="usd",
        platform_fee=500,
        supplier_amount=9500,
        destination_account_id="merchant_test",
        status=PaymentStatus.SUCCEEDED,
        payout_status=None,
        payment_provider="revolut",
        booking_created=False,
        created_at=now,
        updated_at=now,
        paid_at=now,
        refunded_at=None,
        payout_released_at=None,
        payout_released_by=None,
        payout_notes=None,
    )


@pytest.fixture
def mock_current_user():
    """Mock current user object."""
    user = Mock()
    user.email = "test@example.com"
    user.first_name = "John"
    user.last_name = "Doe"
    return user


# ==============================================================================
# ORDER CREATION TESTS
# ==============================================================================


class TestCreatePaymentIntent:
    """Test RevolutPaymentService.create_payment_intent()."""

    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_success(
        self,
        mock_settings,
        mock_client_class,
        mock_repository,
        mock_revolut_order,
        sample_order_request,
    ):
        """Test successful order creation."""
        # Setup mocks
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client_class.return_value = mock_client

        # Create service and call method
        service = RevolutPaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository
        service.client = mock_client

        result = await service.create_payment_intent(sample_order_request)

        # Verify Revolut API was called correctly
        mock_client.create_order.assert_called_once()
        call_kwargs = mock_client.create_order.call_args[1]
        assert call_kwargs["amount"] == 10000
        assert call_kwargs["currency"] == "usd"
        assert call_kwargs["metadata"]["voya_booking_reference"] == "VOYA-TEST123"
        assert call_kwargs["industry_type"] == "airline"
        assert call_kwargs["booking_id"] == "VOYA-TEST123"

        # Verify transaction was created in MongoDB
        mock_repository.create_transaction.assert_called_once()
        transaction_data = mock_repository.create_transaction.call_args[0][0]
        assert transaction_data["revolut_order_id"] == "ord_test_123456789"
        assert transaction_data["amount"] == 10000
        assert transaction_data["platform_fee"] == 500
        assert transaction_data["supplier_amount"] == 9500
        assert transaction_data["status"] == PaymentStatus.PENDING
        assert transaction_data["payment_provider"] == "revolut"

        # Verify response
        assert isinstance(result, RevolutOrderCreateResponse)
        assert result.order_id == "ord_test_123456789"
        assert result.public_order_id == "token_test_abcdef"
        assert result.amount == 10000
        assert result.platform_fee == 500
        assert result.supplier_amount == 9500
        assert result.public_key == "pk_test_123"

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_create_payment_intent_revolut_error(
        self, mock_client_class, mock_repository, sample_order_request
    ):
        """Test order creation when Revolut API fails."""
        # Setup Revolut error
        mock_client = Mock()
        mock_client.create_order = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "API Error", request=Mock(), response=Mock(status_code=400)
            )
        )
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository
        service.client = mock_client

        # Should raise RevolutOrderCreationError
        with pytest.raises(RevolutOrderCreationError) as exc_info:
            await service.create_payment_intent(sample_order_request)

        assert "Failed to create Revolut order" in str(exc_info.value)
        # Transaction should not be created if Revolut fails
        mock_repository.create_transaction.assert_not_called()

    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_calculates_fees_correctly(
        self,
        mock_settings,
        mock_client_class,
        mock_repository,
        mock_revolut_order,
    ):
        """Test platform fee calculation (5% of booking amount)."""
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository
        service.client = mock_client

        # Test various amounts
        test_cases = [
            (10000, 500, 9500),  # $100.00 -> $5.00 fee, $95.00 supplier
            (25000, 1250, 23750),  # $250.00 -> $12.50 fee, $237.50 supplier
            (100, 5, 95),  # $1.00 -> $0.05 fee, $0.95 supplier
        ]

        for booking_amount, expected_fee, expected_supplier in test_cases:
            # Update mock order with new amount
            order_with_amount = {**mock_revolut_order, "amount": booking_amount}
            mock_client.create_order = AsyncMock(return_value=order_with_amount)
            mock_client.get_order = AsyncMock(return_value=order_with_amount)

            request = RevolutOrderCreateRequest(
                booking_amount=booking_amount,
                currency="usd",
                voya_booking_reference="VOYA-TEST",
            )

            result = await service.create_payment_intent(request)

            assert result.platform_fee == expected_fee
            assert result.supplier_amount == expected_supplier
            assert result.amount == booking_amount

    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_with_customer(
        self,
        mock_settings,
        mock_client_class,
        mock_repository,
        mock_revolut_order,
        sample_order_request,
        mock_current_user,
    ):
        """Test order creation with customer information from current_user."""
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(
            user_id=str(ObjectId()), current_user=mock_current_user
        )
        service.repository = mock_repository
        service.client = mock_client

        result = await service.create_payment_intent(sample_order_request)

        # Verify customer was passed to Revolut API
        call_kwargs = mock_client.create_order.call_args[1]
        assert "customer" in call_kwargs
        assert call_kwargs["customer"]["email"] == "test@example.com"
        assert call_kwargs["customer"]["full_name"] == "John Doe"

    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_missing_token(
        self,
        mock_settings,
        mock_client_class,
        mock_repository,
        sample_order_request,
    ):
        """Test order creation when token is missing from response."""
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_client = Mock()
        # Order response without token
        order_without_token = {
            "id": "ord_test_123456789",
            "state": "pending",
            "amount": 10000,
        }
        mock_client.create_order = AsyncMock(return_value=order_without_token)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id=str(ObjectId()))
        service.repository = mock_repository
        service.client = mock_client

        with pytest.raises(RevolutOrderCreationError) as exc_info:
            await service.create_payment_intent(sample_order_request)

        assert "missing token field" in str(exc_info.value).lower()

    @patch("app.database.dependencies.get_database", new_callable=AsyncMock)
    @patch(
        "app.domains.bookings.service.BookingService.create_pending_gds_event",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.reference_generator.VoyaReferenceGenerator.generate_unique",
        new_callable=AsyncMock,
    )
    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_gds_without_voya_ref_creates_pending_event(
        self,
        mock_settings,
        mock_client_class,
        mock_generate_unique,
        mock_create_pending,
        mock_get_database,
        mock_repository,
        mock_revolut_order,
        mock_current_user,
    ):
        """GDS create-order: no voya ref in request → generate ref + PENDING booking event after Revolut order."""
        mock_get_database.return_value = MagicMock()
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_generate_unique.return_value = "VOYA-GDS-GENERATED-1"
        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client_class.return_value = mock_client

        uid = str(ObjectId())
        service = RevolutPaymentService(user_id=uid, current_user=mock_current_user)
        service.repository = mock_repository
        service.client = mock_client

        request = RevolutOrderCreateRequest(
            booking_amount=10000,
            currency="usd",
            voya_booking_reference=None,
            order_type="flight",
        )

        result = await service.create_payment_intent(request)

        mock_generate_unique.assert_called_once()
        mock_create_pending.assert_called_once_with(
            user_id=uid,
            voya_booking_reference="VOYA-GDS-GENERATED-1",
            payment_intent_id="ord_test_123456789",
            contact_email="test@example.com",
            amount=100.0,
            voucher_redemption_id=None,
        )
        assert result.voya_booking_reference == "VOYA-GDS-GENERATED-1"
        meta = mock_client.create_order.call_args[1]["metadata"]
        assert meta["voya_booking_reference"] == "VOYA-GDS-GENERATED-1"

    @patch("app.database.dependencies.get_database", new_callable=AsyncMock)
    @patch(
        "app.domains.bookings.service.BookingService.create_pending_gds_event",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.reference_generator.VoyaReferenceGenerator.generate_unique",
        new_callable=AsyncMock,
    )
    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_gds_pending_event_failure_cancels_revolut_order(
        self,
        mock_settings,
        mock_client_class,
        mock_generate_unique,
        mock_create_pending,
        mock_get_database,
        mock_repository,
        mock_revolut_order,
        mock_current_user,
    ):
        """If PENDING GDS event creation fails, cancel Revolut order and mark txn cancelled."""
        mock_get_database.return_value = MagicMock()
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_generate_unique.return_value = "VOYA-GDS-GENERATED-1"
        mock_create_pending.side_effect = RuntimeError("db unavailable")

        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.cancel_order = AsyncMock(
            return_value={**mock_revolut_order, "state": "cancelled"}
        )
        mock_client_class.return_value = mock_client

        uid = str(ObjectId())
        service = RevolutPaymentService(user_id=uid, current_user=mock_current_user)
        service.repository = mock_repository
        service.client = mock_client

        request = RevolutOrderCreateRequest(
            booking_amount=10000,
            currency="usd",
            voya_booking_reference=None,
            order_type="flight",
        )

        with pytest.raises(RevolutOrderCreationError) as exc_info:
            await service.create_payment_intent(request)

        assert "booking record" in str(exc_info.value).lower()
        mock_client.cancel_order.assert_called_once_with("ord_test_123456789")
        mock_repository.update_transaction_status.assert_called_once_with(
            order_id="ord_test_123456789",
            status=PaymentStatus.CANCELLED,
        )

    @patch("app.database.dependencies.get_database", new_callable=AsyncMock)
    @patch(
        "app.domains.bookings.service.BookingService.create_pending_gds_event",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.service.BookingService.update_payment_intent_id",
        new_callable=AsyncMock,
    )
    @patch("app.domains.revolut_payment.service.RevolutClient")
    @patch("app.domains.revolut_payment.service.settings")
    async def test_create_payment_intent_lcc_with_valid_voya_skips_pending_gds_event(
        self,
        mock_settings,
        mock_client_class,
        mock_update_payment_intent,
        mock_create_pending,
        mock_get_database,
        mock_repository,
        mock_revolut_order,
        mock_current_user,
    ):
        """LCC + valid VOYA (voucher checkout): no PENDING GDS row; only store order id if booking exists."""
        mock_get_database.return_value = MagicMock()
        mock_settings.REVOLUT_PUBLIC_KEY = "pk_test_123"
        mock_client = Mock()
        mock_client.create_order = AsyncMock(return_value=mock_revolut_order)
        mock_client.get_order = AsyncMock(return_value=mock_revolut_order)
        mock_client_class.return_value = mock_client

        uid = str(ObjectId())
        service = RevolutPaymentService(user_id=uid, current_user=mock_current_user)
        service.repository = mock_repository
        service.client = mock_client

        request = RevolutOrderCreateRequest(
            booking_amount=10000,
            currency="usd",
            voya_booking_reference="VOYA-VOUCHER1",
            order_type="flight",
            carrier_type="LCC",
        )

        result = await service.create_payment_intent(request)

        mock_create_pending.assert_not_called()
        # LCC: order id is set on /flights/book, not in create_order (avoids duplicating LCC events).
        mock_update_payment_intent.assert_not_called()
        assert result.voya_booking_reference == "VOYA-VOUCHER1"


# ==============================================================================
# PAYMENT VALIDATION TESTS
# ==============================================================================


class TestValidatePaymentSucceeded:
    """Test RevolutPaymentService.validate_payment_succeeded()."""

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_validate_payment_succeeded_success(
        self, mock_client_class, mock_repository
    ):
        """Test successful payment validation."""
        # Mock Revolut API response with COMPLETED state
        mock_order = {
            "id": "ord_test_123456789",
            "state": "COMPLETED",
            "amount": 10000,
            "currency": "USD",
        }
        mock_client = Mock()
        mock_client.get_order = AsyncMock(return_value=mock_order)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository
        service.client = mock_client

        # Should not raise exception
        await service.validate_payment_succeeded("ord_test_123456789")

        mock_client.get_order.assert_called_once_with("ord_test_123456789")

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_validate_payment_not_found(self, mock_client_class, mock_repository):
        """Test payment validation when order not found."""
        # Mock Revolut API error
        mock_client = Mock()
        mock_client.get_order = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=Mock(), response=Mock(status_code=404)
            )
        )
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository
        service.client = mock_client

        with pytest.raises(RevolutPaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("ord_nonexistent")

        assert "Payment validation failed" in str(exc_info.value)

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_validate_payment_not_completed(
        self, mock_client_class, mock_repository
    ):
        """Test payment validation when payment is pending."""
        # Mock Revolut API response with PENDING state
        mock_order = {
            "id": "ord_test_123456789",
            "state": "PENDING",
            "amount": 10000,
        }
        mock_client = Mock()
        mock_client.get_order = AsyncMock(return_value=mock_order)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository
        service.client = mock_client

        with pytest.raises(RevolutPaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("ord_test_123456789")

        assert "Payment not completed" in str(exc_info.value)
        assert "PENDING" in str(exc_info.value)

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_validate_payment_failed(self, mock_client_class, mock_repository):
        """Test payment validation when payment failed."""
        # Mock Revolut API response with FAILED state
        mock_order = {
            "id": "ord_test_123456789",
            "state": "FAILED",
            "amount": 10000,
        }
        mock_client = Mock()
        mock_client.get_order = AsyncMock(return_value=mock_order)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository
        service.client = mock_client

        with pytest.raises(RevolutPaymentValidationError) as exc_info:
            await service.validate_payment_succeeded("ord_test_123456789")

        assert "Payment not completed" in str(exc_info.value)
        assert "FAILED" in str(exc_info.value)


# ==============================================================================
# IDEMPOTENCY TESTS
# ==============================================================================


class TestCheckPaymentNotUsed:
    """Test RevolutPaymentService.check_payment_not_used()."""

    async def test_check_payment_not_used_success(self, mock_repository):
        """Test idempotency check when payment not used."""
        # Transaction exists but booking_created is False
        now = datetime.now(UTC)
        transaction = TransactionModel(
            id=ObjectId(),
            revolut_order_id="ord_test_123",
            voya_booking_reference="VOYA-TEST",
            amount=10000,
            platform_fee=500,
            supplier_amount=9500,
            status=PaymentStatus.PENDING,
            booking_created=False,
            payment_provider="revolut",
            created_at=now,
            updated_at=now,
        )
        mock_repository.get_transaction_by_order_id = AsyncMock(
            return_value=transaction
        )

        service = RevolutPaymentService()
        service.repository = mock_repository

        # Should not raise
        await service.check_payment_not_used("ord_test_123")

    async def test_check_payment_not_used_already_used(self, mock_repository):
        """Test idempotency check when payment already used."""
        # Transaction exists with booking_created = True
        now = datetime.now(UTC)
        transaction = TransactionModel(
            id=ObjectId(),
            revolut_order_id="ord_test_123",
            voya_booking_reference="VOYA-TEST",
            amount=10000,
            platform_fee=500,
            supplier_amount=9500,
            status=PaymentStatus.PENDING,
            booking_created=True,
            payment_provider="revolut",
            created_at=now,
            updated_at=now,
        )
        mock_repository.get_transaction_by_order_id = AsyncMock(
            return_value=transaction
        )

        service = RevolutPaymentService()
        service.repository = mock_repository

        with pytest.raises(RevolutPaymentValidationError) as exc_info:
            await service.check_payment_not_used("ord_test_123")

        assert "already been used" in str(exc_info.value).lower()

    async def test_check_payment_not_used_not_found(self, mock_repository):
        """Test idempotency check when transaction not found."""
        mock_repository.get_transaction_by_order_id = AsyncMock(return_value=None)

        service = RevolutPaymentService()
        service.repository = mock_repository

        # Should not raise (transaction might be delayed)
        await service.check_payment_not_used("ord_test_123")


class TestMarkPaymentUsedForBooking:
    """Test RevolutPaymentService.mark_payment_used_for_booking()."""

    async def test_mark_payment_used_success(self, mock_repository):
        """Test marking payment as used."""
        service = RevolutPaymentService()
        service.repository = mock_repository

        await service.mark_payment_used_for_booking("ord_test_123")

        mock_repository.update_transaction_status.assert_called_once()
        call_kwargs = mock_repository.update_transaction_status.call_args[1]
        assert call_kwargs["order_id"] == "ord_test_123"
        assert call_kwargs["status"] == PaymentStatus.SUCCEEDED
        assert call_kwargs["booking_created"] is True


# ==============================================================================
# GET TRANSACTION TESTS
# ==============================================================================


class TestGetTransactionByPaymentIntent:
    """Test RevolutPaymentService.get_transaction_by_payment_intent()."""

    async def test_get_transaction_success(
        self, mock_repository, sample_transaction_doc
    ):
        """Test successfully retrieving transaction."""
        # Create transaction with matching user_id
        user_id = ObjectId()
        transaction_with_user = TransactionModel(
            **{**sample_transaction_doc.model_dump(), "user_id": user_id}
        )
        mock_repository.get_transaction_by_order_id.return_value = transaction_with_user

        service = RevolutPaymentService(user_id=str(user_id))
        service.repository = mock_repository

        result = await service.get_transaction_by_payment_intent("ord_test_123456789")

        assert isinstance(result, RevolutTransactionResponse)
        assert result.revolut_order_id == "ord_test_123456789"
        assert result.amount == 10000
        assert result.platform_fee == 500
        assert result.supplier_amount == 9500
        assert result.status == PaymentStatus.SUCCEEDED

    async def test_get_transaction_not_found(self, mock_repository):
        """Test transaction retrieval when not found."""
        mock_repository.get_transaction_by_order_id.return_value = None

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(ValueError) as exc_info:
            await service.get_transaction_by_payment_intent("ord_nonexistent")

        assert "Transaction not found" in str(exc_info.value)

    async def test_get_transaction_user_mismatch(
        self, mock_repository, sample_transaction_doc
    ):
        """Test transaction retrieval when user doesn't match."""
        # Transaction belongs to different user
        other_user_id = ObjectId()
        transaction_with_other_user = TransactionModel(
            **{**sample_transaction_doc.model_dump(), "user_id": other_user_id}
        )
        mock_repository.get_transaction_by_order_id.return_value = (
            transaction_with_other_user
        )

        service = RevolutPaymentService(user_id="user_123")
        service.repository = mock_repository

        with pytest.raises(ValueError) as exc_info:
            await service.get_transaction_by_payment_intent("ord_test_123456789")

        assert "Transaction not found" in str(exc_info.value)


# ==============================================================================
# PAYOUT RELEASE TESTS
# ==============================================================================


class TestReleasePayout:
    """Test RevolutPaymentService.release_payout()."""

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_release_payout_success(
        self,
        mock_client_class,
        mock_repository,
        sample_transaction_doc,
    ):
        """Test successful payout release."""
        # Setup mocks
        mock_repository.get_transaction_by_voya_reference.return_value = (
            sample_transaction_doc
        )
        mock_payout = {"id": "payout_test_123456789", "status": "completed"}
        mock_client = Mock()
        mock_client.create_payout = AsyncMock(return_value=mock_payout)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService()
        service.repository = mock_repository
        service.client = mock_client

        request = RevolutPayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        result = await service.release_payout(request, admin_user_id="admin_123")

        # Verify Revolut payout was created
        mock_client.create_payout.assert_called_once()
        payout_kwargs = mock_client.create_payout.call_args[1]
        assert payout_kwargs["amount"] == 9500  # supplier_amount
        assert payout_kwargs["currency"] == "usd"
        assert payout_kwargs["metadata"]["voya_booking_reference"] == "VOYA-TEST123"

        # Verify transaction was updated
        mock_repository.update_transaction_status.assert_called_once()
        update_kwargs = mock_repository.update_transaction_status.call_args[1]
        assert update_kwargs["revolut_payout_id"] == "payout_test_123456789"
        assert update_kwargs["payout_status"] == PayoutStatus.PAID.value

        # Verify response
        assert isinstance(result, RevolutPayoutReleaseResponse)
        assert result.payout_id == "payout_test_123456789"
        assert result.amount == 9500

    async def test_release_payout_payment_not_found(self, mock_repository):
        """Test payout release when payment not found."""
        mock_repository.get_transaction_by_voya_reference.return_value = None

        service = RevolutPaymentService()
        service.repository = mock_repository

        request = RevolutPayoutReleaseRequest(voya_booking_reference="VOYA-NONEXISTENT")

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

        service = RevolutPaymentService()
        service.repository = mock_repository

        request = RevolutPayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        with pytest.raises(RevolutPayoutReleaseError) as exc_info:
            await service.release_payout(request, admin_user_id="admin_123")

        assert "payment status" in str(exc_info.value).lower()

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_release_payout_revolut_error(
        self, mock_client_class, mock_repository, sample_transaction_doc
    ):
        """Test payout release when Revolut payout fails."""
        mock_repository.get_transaction_by_voya_reference.return_value = (
            sample_transaction_doc
        )
        mock_client = Mock()
        mock_client.create_payout = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Payout failed", request=Mock(), response=Mock(status_code=400)
            )
        )
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService()
        service.repository = mock_repository
        service.client = mock_client

        request = RevolutPayoutReleaseRequest(voya_booking_reference="VOYA-TEST123")

        with pytest.raises(RevolutPayoutReleaseError) as exc_info:
            await service.release_payout(request, admin_user_id="admin_123")

        assert "Failed to create payout" in str(exc_info.value)


# ==============================================================================
# REFUND TESTS
# ==============================================================================


class TestRefundPayment:
    """Test RevolutPaymentService.refund_payment()."""

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_refund_payment_success(self, mock_client_class, mock_repository):
        """Test successful payment refund."""
        mock_refund = {"id": "refund_test_123", "status": "completed"}
        mock_client = Mock()
        mock_client.create_refund = AsyncMock(return_value=mock_refund)
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService()
        service.repository = mock_repository
        service.client = mock_client

        refund_id = await service.refund_payment(
            "ord_test_123", reason="booking_failed"
        )

        # Verify Revolut refund was created
        mock_client.create_refund.assert_called_once()
        refund_kwargs = mock_client.create_refund.call_args[1]
        assert refund_kwargs["order_id"] == "ord_test_123"
        assert "booking_failed" in refund_kwargs["description"]

        # Verify transaction was updated
        mock_repository.update_transaction_status.assert_called_once()
        update_kwargs = mock_repository.update_transaction_status.call_args[1]
        assert update_kwargs["order_id"] == "ord_test_123"
        assert update_kwargs["status"] == PaymentStatus.REFUNDED
        assert update_kwargs["refund_id"] == "refund_test_123"

        assert refund_id == "refund_test_123"

    @patch("app.domains.revolut_payment.service.RevolutClient")
    async def test_refund_payment_revolut_error(
        self, mock_client_class, mock_repository
    ):
        """Test refund when Revolut API fails."""
        mock_client = Mock()
        mock_client.create_refund = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Refund failed", request=Mock(), response=Mock(status_code=400)
            )
        )
        mock_client_class.return_value = mock_client

        service = RevolutPaymentService()
        service.repository = mock_repository
        service.client = mock_client

        with pytest.raises(RevolutPaymentValidationError) as exc_info:
            await service.refund_payment("ord_test_123")

        assert "Failed to refund payment" in str(exc_info.value)
