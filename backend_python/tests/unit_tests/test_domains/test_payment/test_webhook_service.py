"""Tests for PaymentWebhookService.

Tests webhook business logic with clean dependency injection - no HTTP mocking needed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.payment import PaymentStatus, PayoutStatus
from app.domains.payment.webhook_service import PaymentWebhookService

# ==============================================================================
# PAYMENT INTENT HANDLERS
# ==============================================================================


class TestPaymentIntentHandlers:
    """Test payment intent webhook handlers."""

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_complete_flow(self):
        """Should update transaction and trigger payment confirmation email."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "amount": 10000,
            "currency": "usd",
            "status": "succeeded",
            "created": int(datetime.now(UTC).timestamp()),
            "latest_charge": "ch_test_123",
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        with (
            patch(
                "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.payment.webhook_service.BookingService.get_latest_booking_by_voya_reference"
            ) as mock_get_booking,
            patch(
                "app.domains.payment.webhook_service.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            # Mock LCC booking (no ticket_time_limit) - validation should be skipped
            mock_get_booking.return_value = None

            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - Transaction updated
            mock_repo.update_transaction_status.assert_called_once_with(
                payment_intent_id="pi_test_123",
                status=PaymentStatus.SUCCEEDED,
                stripe_charge_id="ch_test_123",
                paid_at=datetime.fromtimestamp(payment_intent["created"], UTC),
            )

            # Assert - Event handler called
            mock_event.assert_called_once_with(
                user_id="user123",
                voya_booking_reference="VOYA-TEST-001",
                amount=100.0,  # Converted from cents
                currency="usd",
                transaction_id="pi_test_123",
                payment_method="Credit Card",
            )

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_missing_booking_reference(self):
        """Should log warning and return early if voya_booking_reference missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "metadata": {"user_id": "user123"},  # Missing voya_booking_reference
        }

        with patch(
            "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
        ) as mock_event:
            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - No repository calls
            mock_repo.update_transaction_status.assert_not_called()
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_gds_valid(self):
        """Should process payment for GDS booking with valid ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse

        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "amount": 10000,
            "currency": "usd",
            "status": "succeeded",
            "created": int(datetime.now(UTC).timestamp()),
            "latest_charge": "ch_test_123",
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        # Mock GDS booking with valid ticket_time_limit (future time)
        future_time = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST-001",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=future_time,
            departure_airport_iata="JFK",
        )

        with (
            patch(
                "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.payment.webhook_service.BookingService.get_latest_booking_by_voya_reference"
            ) as mock_get_booking,
            patch(
                "app.domains.payment.webhook_service.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_booking.return_value = mock_gds_booking

            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - Transaction updated (validation passed)
            mock_repo.update_transaction_status.assert_called_once_with(
                payment_intent_id="pi_test_123",
                status=PaymentStatus.SUCCEEDED,
                stripe_charge_id="ch_test_123",
                paid_at=datetime.fromtimestamp(payment_intent["created"], UTC),
            )

            # Assert - Event handler called
            mock_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_gds_expired(self):
        """Should block payment for GDS booking with expired ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse

        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "amount": 10000,
            "currency": "usd",
            "status": "succeeded",
            "created": int(datetime.now(UTC).timestamp()),
            "latest_charge": "ch_test_123",
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        # Mock GDS booking with expired ticket_time_limit (past time)
        past_time = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
        mock_gds_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST-001",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=past_time,
            departure_airport_iata="JFK",
        )

        with (
            patch(
                "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.payment.webhook_service.BookingService.get_latest_booking_by_voya_reference"
            ) as mock_get_booking,
            patch(
                "app.domains.payment.webhook_service.BookingService.release_voucher_for_booking_if_any",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_booking.return_value = mock_gds_booking

            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - Transaction status updated to FAILED (not SUCCEEDED)
            assert mock_repo.update_transaction_status.called
            call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
            assert call_kwargs["payment_intent_id"] == "pi_test_123"
            assert call_kwargs["status"] == PaymentStatus.FAILED
            assert "expired" in call_kwargs["failure_reason"].lower()

            # Assert - Event handler NOT called (payment blocked)
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_lcc_no_limit(self):
        """Should process payment for LCC booking without ticket_time_limit."""
        from app.domains.bookings.schemas import BookingEventResponse

        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "amount": 10000,
            "currency": "usd",
            "status": "succeeded",
            "created": int(datetime.now(UTC).timestamp()),
            "latest_charge": "ch_test_123",
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        # Mock LCC booking without ticket_time_limit
        mock_lcc_booking = BookingEventResponse(
            id="booking_123",
            user_id="user_123",
            voya_booking_reference="VOYA-TEST-001",
            external_booking_reference="EXT123",
            action="BOOKED",
            timestamp=datetime.now(UTC),
            event_type="FLIGHT",
            ticket_time_limit=None,  # LCC flights don't have ticket_time_limit
            departure_airport_iata=None,
        )

        with (
            patch(
                "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.payment.webhook_service.BookingService.get_latest_booking_by_voya_reference"
            ) as mock_get_booking,
            patch(
                "app.domains.payment.webhook_service.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_booking.return_value = mock_lcc_booking

            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - Transaction updated (validation skipped for LCC)
            mock_repo.update_transaction_status.assert_called_once_with(
                payment_intent_id="pi_test_123",
                status=PaymentStatus.SUCCEEDED,
                stripe_charge_id="ch_test_123",
                paid_at=datetime.fromtimestamp(payment_intent["created"], UTC),
            )

            # Assert - Event handler called
            mock_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_payment_succeeded_missing_user_id(self):
        """Should log warning and return early if user_id missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_123",
            "metadata": {"voya_booking_reference": "VOYA-TEST-001"},  # Missing user_id
        }

        with patch(
            "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
        ) as mock_event:
            # Act
            await service.process_payment_succeeded(payment_intent)

            # Assert - No event triggered
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_payment_failed(self):
        """Should update transaction status to FAILED."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_failed",
            "amount": 5000,
            "currency": "usd",
            "status": "failed",
            "last_payment_error": {"message": "Card declined", "code": "card_declined"},
            "metadata": {"voya_booking_reference": "VOYA-TEST-002"},
        }
        mock_repo.get_transaction_by_voya_reference = AsyncMock(return_value=None)

        # Act
        await service.process_payment_failed(payment_intent)

        # Assert - Check that update_transaction_status was called
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["payment_intent_id"] == "pi_test_failed"
        assert call_kwargs["status"] == PaymentStatus.FAILED
        assert "Card declined" in call_kwargs["failure_reason"]

    @pytest.mark.asyncio
    async def test_process_payment_failed_missing_booking_reference(self):
        """Should log warning and return early if booking reference missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        payment_intent = {
            "id": "pi_test_failed",
            "metadata": {},  # Missing voya_booking_reference
        }

        # Act
        await service.process_payment_failed(payment_intent)

        # Assert - No repository calls
        mock_repo.update_transaction_status.assert_not_called()


# ==============================================================================
# CHARGE HANDLERS
# ==============================================================================


class TestChargeHandlers:
    """Test charge webhook handlers."""

    @pytest.mark.asyncio
    async def test_process_charge_succeeded(self):
        """Should log charge success information."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        charge = {
            "id": "ch_test_123",
            "amount": 10000,
            "currency": "usd",
            "status": "succeeded",
            "payment_intent": "pi_test_123",
        }

        # Act - should not raise
        await service.process_charge_succeeded(charge)

    @pytest.mark.asyncio
    async def test_process_charge_failed(self):
        """Should update transaction with charge failure details."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        charge = {
            "id": "ch_test_failed",
            "amount": 5000,
            "currency": "usd",
            "status": "failed",
            "failure_message": "Insufficient funds",
            "payment_intent": "pi_test_failed",
        }
        mock_repo.get_transaction_by_payment_intent = AsyncMock(return_value=None)

        # Act
        await service.process_charge_failed(charge)

        # Assert
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["payment_intent_id"] == "pi_test_failed"
        assert call_kwargs["status"] == PaymentStatus.FAILED
        assert call_kwargs["stripe_charge_id"] == "ch_test_failed"

    @pytest.mark.asyncio
    async def test_process_charge_failed_missing_payment_intent(self):
        """Should log warning and return early if payment_intent missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        charge = {
            "id": "ch_test_failed",
            "failure_message": "Card declined",
            # Missing payment_intent
        }

        # Act
        await service.process_charge_failed(charge)

        # Assert - No repository calls
        mock_repo.update_transaction_status.assert_not_called()


# ==============================================================================
# TRANSFER HANDLERS
# ==============================================================================


class TestTransferHandlers:
    """Test transfer webhook handlers."""

    @pytest.mark.asyncio
    async def test_process_transfer_created(self):
        """Should update payout status when transfer is created."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.id = "transaction_123"
        mock_transaction.stripe_payment_intent_id = "pi_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = PaymentWebhookService(repository=mock_repo)

        transfer = {
            "id": "tr_test_123",
            "amount": 9500,
            "currency": "usd",
            "destination": "acct_supplier",
            "transfer_group": "VOYA-TEST-001",
        }

        # Act
        await service.process_transfer_created(transfer)

        # Assert - Transaction lookup
        mock_repo.get_transaction_by_voya_reference.assert_called_once_with(
            "VOYA-TEST-001"
        )

        # Assert - Payout status updated via update_transaction_status
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["payment_intent_id"] == "pi_test_123"
        assert call_kwargs["payout_status"] == PayoutStatus.SCHEDULED.value
        assert call_kwargs["stripe_transfer_id"] == "tr_test_123"

    @pytest.mark.asyncio
    async def test_process_transfer_created_missing_transfer_group(self):
        """Should log warning and return early if transfer_group missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        transfer = {
            "id": "tr_test_123",
            # Missing transfer_group
        }

        # Act
        await service.process_transfer_created(transfer)

        # Assert - No repository calls
        mock_repo.get_transaction_by_voya_reference.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_transfer_created_transaction_not_found(self):
        """Should log warning and return early if transaction not found."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_transaction_by_voya_reference = AsyncMock(return_value=None)
        service = PaymentWebhookService(repository=mock_repo)

        transfer = {
            "id": "tr_test_123",
            "transfer_group": "VOYA-UNKNOWN",
        }

        # Act
        await service.process_transfer_created(transfer)

        # Assert - Update not called
        mock_repo.update_transaction_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_transfer_updated_succeeded(self):
        """Should update payout status when transfer succeeds."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.id = "transaction_123"
        mock_transaction.stripe_payment_intent_id = "pi_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = PaymentWebhookService(repository=mock_repo)

        transfer = {
            "id": "tr_test_123",
            "status": "paid",
            "transfer_group": "VOYA-TEST-001",
        }

        # Act
        await service.process_transfer_updated(transfer)

        # Assert
        mock_repo.get_transaction_by_voya_reference.assert_called_once_with(
            "VOYA-TEST-001"
        )
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["payment_intent_id"] == "pi_test_123"
        assert call_kwargs["payout_status"] == PayoutStatus.PAID.value

    @pytest.mark.asyncio
    async def test_process_transfer_updated_failed(self):
        """Should update payout status when transfer fails."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.id = "transaction_123"
        mock_transaction.stripe_payment_intent_id = "pi_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = PaymentWebhookService(repository=mock_repo)

        transfer = {
            "id": "tr_test_failed",
            "status": "failed",
            "failure_message": "Account closed",
            "transfer_group": "VOYA-TEST-002",
        }

        # Act
        await service.process_transfer_updated(transfer)

        # Assert
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["payout_status"] == PayoutStatus.FAILED.value


# ==============================================================================
# ACCOUNT HANDLERS
# ==============================================================================


class TestAccountHandlers:
    """Test Stripe Connect account webhook handlers."""

    @pytest.mark.asyncio
    async def test_process_account_updated(self):
        """Should log account update information."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        account = {
            "id": "acct_test_123",
            "charges_enabled": True,
            "payouts_enabled": True,
            "requirements": {"currently_due": []},
        }

        # Act - should not raise
        await service.process_account_updated(account)

    @pytest.mark.asyncio
    async def test_process_account_deauthorized(self):
        """Should log account deauthorization."""
        # Arrange
        mock_repo = AsyncMock()
        service = PaymentWebhookService(repository=mock_repo)

        account = {"id": "acct_test_123", "business_profile": {"name": "Test Supplier"}}

        # Act - should not raise
        await service.process_account_deauthorized(account)
