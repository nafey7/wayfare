"""Tests for RevolutWebhookService.

Tests webhook business logic with clean dependency injection - no HTTP mocking needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.domains.revolut_payment.webhook_service import RevolutWebhookService

# ==============================================================================
# ORDER COMPLETED HANDLER TESTS
# ==============================================================================


class TestOrderCompletedHandler:
    """Test order completed webhook handler."""

    @pytest.mark.asyncio
    async def test_process_order_completed_complete_flow(self):
        """Should update transaction and trigger payment confirmation email."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_123",
            "amount": {"value": 10000, "currency": "usd"},
            "state": "COMPLETED",
            "created_at": "2024-01-01T00:00:00Z",
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            # Act
            await service.process_order_completed(order)

            # Assert - Transaction updated
            mock_repo.update_transaction_status.assert_called_once()
            call_kwargs = mock_repo.update_transaction_status.call_args[1]
            assert call_kwargs["order_id"] == "ord_test_123"
            assert call_kwargs["status"] == PaymentStatus.SUCCEEDED
            assert "paid_at" in call_kwargs

            # Assert - Event handler called
            mock_event.assert_called_once_with(
                user_id="user123",
                voya_booking_reference="VOYA-TEST-001",
                amount=100.0,  # Converted from minor units
                currency="usd",
                transaction_id="ord_test_123",
                payment_method="Revolut",
            )

    @pytest.mark.asyncio
    async def test_process_order_completed_with_direct_amount(self):
        """Should handle amount as direct integer (not dict)."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_123",
            "amount": 10000,  # Direct integer
            "currency": "usd",
            "state": "COMPLETED",
            "created_at": 1704067200,  # Unix timestamp
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            # Act
            await service.process_order_completed(order)

            # Assert - Transaction updated
            mock_repo.update_transaction_status.assert_called_once()
            # Assert - Event handler called with correct amount
            mock_event.assert_called_once()
            call_kwargs = mock_event.call_args[1]
            assert call_kwargs["amount"] == 100.0  # 10000 / 100

    @pytest.mark.asyncio
    async def test_process_order_completed_skips_when_amount_null(self):
        """Must not mark booking paid when amount is null or non-positive."""
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)
        order = {
            "id": "ord_test_123",
            "amount": None,
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }
        with patch(
            "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
        ) as mock_event:
            await service.process_order_completed(order)
            mock_repo.update_transaction_status.assert_not_called()
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_order_completed_skips_when_dict_amount_value_invalid(self):
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)
        order = {
            "id": "ord_test_123",
            "amount": {"value": None, "currency": "usd"},
            "metadata": {
                "voya_booking_reference": "VOYA-TEST-001",
                "user_id": "user123",
            },
        }
        with patch(
            "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
        ) as mock_event:
            await service.process_order_completed(order)
            mock_repo.update_transaction_status.assert_not_called()
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_order_completed_missing_booking_reference(self):
        """Should log warning and return early if voya_booking_reference missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_123",
            "amount": 10000,
            "metadata": {"user_id": "user123"},  # Missing voya_booking_reference
        }
        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=None)

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.get_voya_reference_by_payment_intent_id",
                AsyncMock(return_value=None),
            ),
        ):
            # Act
            await service.process_order_completed(order)

            # Assert - No repository calls
            mock_repo.update_transaction_status.assert_not_called()
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_order_completed_missing_user_id(self):
        """Should log warning and return early if user_id missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_123",
            "amount": 10000,
            "metadata": {"voya_booking_reference": "VOYA-TEST-001"},  # Missing user_id
        }
        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=None)

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.get_latest_booking_by_voya_reference",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.domains.bookings.BookingService.get_latest_booking_by_parent_voya_reference",
                AsyncMock(return_value=None),
            ),
        ):
            # Act
            await service.process_order_completed(order)

            # Assert - No event triggered
            mock_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_order_completed_lookup_from_transaction(self):
        """Should lookup missing metadata from transaction in database."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        # Transaction with missing metadata
        mock_transaction = MagicMock()
        mock_transaction.voya_booking_reference = "VOYA-TEST-001"
        mock_transaction.user_id = "user123"
        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=mock_transaction)

        order = {
            "id": "ord_test_123",
            "amount": 10000,
            "metadata": {},  # Missing both
        }

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            # Act
            await service.process_order_completed(order)

            # Assert - Transaction lookup was called
            mock_repo.get_transaction_by_order_id.assert_called_once_with(
                "ord_test_123"
            )
            # Assert - Event handler called with data from transaction
            mock_event.assert_called_once()
            call_kwargs = mock_event.call_args[1]
            assert call_kwargs["voya_booking_reference"] == "VOYA-TEST-001"
            assert call_kwargs["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_process_order_completed_resolves_user_via_parent_group(self):
        """Multicity: metadata uses parent VOYA-MC-…; resolve user_id from any leg row."""
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)
        owner = ObjectId()
        mock_booking = MagicMock()
        mock_booking.user_id = owner

        order = {
            "id": "ord_test_123",
            "amount": 10000,
            "metadata": {"voya_booking_reference": "VOYA-MC-GROUP-1"},
        }

        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=None)

        with (
            patch(
                "app.domains.revolut_payment.webhook_service.PaymentEventHandler.handle_payment_succeeded"
            ) as mock_event,
            patch(
                "app.domains.bookings.BookingService.update_booking_dates_and_flags",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.bookings.BookingService.get_latest_booking_by_voya_reference",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.domains.bookings.BookingService.get_latest_booking_by_parent_voya_reference",
                new_callable=AsyncMock,
                return_value=mock_booking,
            ),
            patch(
                "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
                new_callable=AsyncMock,
            ),
        ):
            await service.process_order_completed(order)

        mock_event.assert_called_once()
        assert mock_event.call_args[1]["user_id"] == str(owner)
        assert mock_event.call_args[1]["voya_booking_reference"] == "VOYA-MC-GROUP-1"


# ==============================================================================
# ORDER FAILED HANDLER TESTS
# ==============================================================================


class TestOrderFailedHandler:
    """Test order failed webhook handler."""

    @pytest.mark.asyncio
    async def test_process_order_failed(self):
        """Should update transaction status to FAILED."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_failed",
            "amount": {"value": 5000, "currency": "usd"},
            "state": "FAILED",
            "metadata": {"voya_booking_reference": "VOYA-TEST-002"},
        }
        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=None)

        # Act
        await service.process_order_failed(order)

        # Assert - Check that update_transaction_status was called
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["order_id"] == "ord_test_failed"
        assert call_kwargs["status"] == PaymentStatus.FAILED
        assert "FAILED" in call_kwargs["failure_reason"]

    @pytest.mark.asyncio
    async def test_process_order_failed_with_direct_amount(self):
        """Should handle amount as direct integer."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_failed",
            "amount": 5000,  # Direct integer
            "state": "CANCELLED",
            "metadata": {"voya_booking_reference": "VOYA-TEST-002"},
        }
        mock_repo.get_transaction_by_order_id = AsyncMock(return_value=None)

        # Act
        await service.process_order_failed(order)

        # Assert
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["status"] == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_order_failed_missing_booking_reference(self):
        """Should log warning and return early if booking reference missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        order = {
            "id": "ord_test_failed",
            "amount": 5000,
            "metadata": {},  # Missing voya_booking_reference
        }

        # Act
        await service.process_order_failed(order)

        # Assert - No repository calls
        mock_repo.update_transaction_status.assert_not_called()


# ==============================================================================
# REFUND HANDLER TESTS
# ==============================================================================


class TestRefundCompletedHandler:
    """Test refund completed webhook handler."""

    @pytest.mark.asyncio
    async def test_process_refund_completed(self):
        """Should update transaction with refund information."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        refund = {
            "id": "refund_test_123",
            "order_id": "ord_test_123",
            "amount": {"value": 10000, "currency": "usd"},
            "created_at": "2024-01-01T00:00:00Z",
        }

        # Act
        await service.process_refund_completed(refund)

        # Assert
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["order_id"] == "ord_test_123"
        assert call_kwargs["status"] == PaymentStatus.REFUNDED
        assert call_kwargs["refund_id"] == "refund_test_123"
        assert "refunded_at" in call_kwargs

    @pytest.mark.asyncio
    async def test_process_refund_completed_with_direct_amount(self):
        """Should handle amount as direct integer."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        refund = {
            "id": "refund_test_123",
            "order_id": "ord_test_123",
            "amount": 10000,  # Direct integer
            "created_at": 1704067200,  # Unix timestamp
        }

        # Act
        await service.process_refund_completed(refund)

        # Assert
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["status"] == PaymentStatus.REFUNDED

    @pytest.mark.asyncio
    async def test_process_refund_completed_missing_order_id(self):
        """Should log warning and return early if order_id missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        refund = {
            "id": "refund_test_123",
            "amount": 10000,
            # Missing order_id
        }

        # Act
        await service.process_refund_completed(refund)

        # Assert - No repository calls
        mock_repo.update_transaction_status.assert_not_called()


# ==============================================================================
# PAYOUT HANDLER TESTS
# ==============================================================================


class TestPayoutCompletedHandler:
    """Test payout completed webhook handler."""

    @pytest.mark.asyncio
    async def test_process_payout_completed(self):
        """Should update payout status when payout is completed."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.id = "transaction_123"
        mock_transaction.revolut_order_id = "ord_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = RevolutWebhookService(repository=mock_repo)

        payout = {
            "id": "payout_test_123",
            "amount": {"value": 9500, "currency": "usd"},
            "completed_at": "2024-01-01T00:00:00Z",
            "metadata": {"voya_booking_reference": "VOYA-TEST-001"},
        }

        # Act
        await service.process_payout_completed(payout)

        # Assert - Transaction lookup
        mock_repo.get_transaction_by_voya_reference.assert_called_once_with(
            "VOYA-TEST-001"
        )

        # Assert - Payout status updated
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["order_id"] == "ord_test_123"
        assert call_kwargs["payout_status"] == PayoutStatus.PAID.value
        assert call_kwargs["revolut_payout_id"] == "payout_test_123"

    @pytest.mark.asyncio
    async def test_process_payout_completed_with_direct_amount(self):
        """Should handle amount as direct integer."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        mock_transaction.revolut_order_id = "ord_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = RevolutWebhookService(repository=mock_repo)

        payout = {
            "id": "payout_test_123",
            "amount": 9500,  # Direct integer
            "currency": "usd",
            "completed_at": 1704067200,  # Unix timestamp
            "metadata": {"voya_booking_reference": "VOYA-TEST-001"},
        }

        # Act
        await service.process_payout_completed(payout)

        # Assert
        assert mock_repo.update_transaction_status.called

    @pytest.mark.asyncio
    async def test_process_payout_completed_missing_metadata(self):
        """Should log warning and return early if voya_booking_reference missing."""
        # Arrange
        mock_repo = AsyncMock()
        service = RevolutWebhookService(repository=mock_repo)

        payout = {
            "id": "payout_test_123",
            "amount": 9500,
            "metadata": {},  # Missing voya_booking_reference
        }

        # Act
        await service.process_payout_completed(payout)

        # Assert - No repository calls
        mock_repo.get_transaction_by_voya_reference.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_payout_completed_transaction_not_found(self):
        """Should log warning and return early if transaction not found."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_transaction_by_voya_reference = AsyncMock(return_value=None)
        service = RevolutWebhookService(repository=mock_repo)

        payout = {
            "id": "payout_test_123",
            "amount": 9500,
            "metadata": {"voya_booking_reference": "VOYA-UNKNOWN"},
        }

        # Act
        await service.process_payout_completed(payout)

        # Assert - Update not called
        mock_repo.update_transaction_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_payout_completed_with_temporary_mapping(self):
        """Should handle transaction with temporary stripe_payment_intent_id mapping."""
        # Arrange
        mock_repo = AsyncMock()
        mock_transaction = MagicMock()
        # Transaction with temporary mapping format
        mock_transaction.revolut_order_id = None
        mock_transaction.stripe_payment_intent_id = "revolut_ord_test_123"
        mock_transaction.status = PaymentStatus.SUCCEEDED
        mock_repo.get_transaction_by_voya_reference = AsyncMock(
            return_value=mock_transaction
        )
        service = RevolutWebhookService(repository=mock_repo)

        payout = {
            "id": "payout_test_123",
            "amount": 9500,
            "metadata": {"voya_booking_reference": "VOYA-TEST-001"},
        }

        # Act
        await service.process_payout_completed(payout)

        # Assert - Should extract order_id from temporary mapping
        assert mock_repo.update_transaction_status.called
        call_kwargs = mock_repo.update_transaction_status.call_args[1]
        assert call_kwargs["order_id"] == "ord_test_123"
