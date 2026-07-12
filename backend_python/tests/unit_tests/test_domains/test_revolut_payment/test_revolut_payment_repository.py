"""Unit tests for RevolutPaymentRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.database.models.transaction import TransactionModel
from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.domains.revolut_payment.repository import RevolutPaymentRepository

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_collection():
    """Mock MongoDB collection."""
    collection = Mock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find_one_and_update = AsyncMock()
    collection.find = Mock()
    return collection


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for creating records."""
    return {
        "revolut_order_id": "ord_test_123456789",
        "voya_booking_reference": "VOYA-TEST123",
        "user_id": ObjectId(),
        "amount": 10000,
        "currency": "usd",
        "platform_fee": 500,
        "supplier_amount": 9500,
        "status": PaymentStatus.PENDING,
        "payment_provider": "revolut",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest.fixture
def sample_transaction_doc():
    """Sample transaction document from MongoDB."""
    now = datetime.now(UTC)
    return {
        "_id": ObjectId(),
        "revolut_order_id": "ord_test_123456789",
        "stripe_payment_intent_id": None,
        "stripe_charge_id": None,
        "stripe_transfer_id": None,
        "refund_id": None,
        "voya_booking_reference": "VOYA-TEST123",
        "user_id": ObjectId(),
        "amount": 10000,
        "currency": "usd",
        "platform_fee": 500,
        "supplier_amount": 9500,
        "destination_account_id": "merchant_test",
        "status": PaymentStatus.SUCCEEDED,
        "payout_status": None,
        "payment_provider": "revolut",
        "booking_created": False,
        "created_at": now,
        "updated_at": now,
        "paid_at": now,
        "refunded_at": None,
        "payout_released_at": None,
        "payout_released_by": None,
        "payout_notes": None,
    }


# ==============================================================================
# CREATE TRANSACTION TESTS
# ==============================================================================


class TestCreateTransaction:
    """Test RevolutPaymentRepository.create_transaction()."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_create_transaction_success(
        self, mock_get_db, mock_collection, sample_transaction_data
    ):
        """Test successful transaction creation."""
        # Setup mocks - database needs to support subscript access
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())

        # Create repository and call method
        repo = RevolutPaymentRepository()
        result = await repo.create_transaction(sample_transaction_data)

        # Verify insert was called once
        mock_collection.insert_one.assert_called_once()
        # Verify result is TransactionModel with correct attributes
        assert isinstance(result, TransactionModel)
        assert result.revolut_order_id == "ord_test_123456789"
        assert result.voya_booking_reference == "VOYA-TEST123"
        assert result.payment_provider == "revolut"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_create_transaction_database_error(
        self, mock_get_db, mock_collection, sample_transaction_data
    ):
        """Test transaction creation when database fails."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.side_effect = Exception("Database error")

        repo = RevolutPaymentRepository()

        with pytest.raises(Exception) as exc_info:
            await repo.create_transaction(sample_transaction_data)

        assert "Database error" in str(exc_info.value)

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_create_transaction_sets_defaults(self, mock_get_db, mock_collection):
        """Test that create_transaction sets payment_provider and timestamps."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())

        repo = RevolutPaymentRepository()
        transaction_data = {
            "revolut_order_id": "ord_test_123",
            "voya_booking_reference": "VOYA-TEST",
            "amount": 10000,
            "platform_fee": 500,
            "supplier_amount": 9500,
            "status": PaymentStatus.PENDING,
        }

        result = await repo.create_transaction(transaction_data)

        # Verify defaults were set
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["payment_provider"] == "revolut"
        assert "created_at" in call_args
        assert "updated_at" in call_args
        assert isinstance(result, TransactionModel)


# ==============================================================================
# UPDATE TRANSACTION STATUS TESTS
# ==============================================================================


class TestUpdateTransactionStatus:
    """Test RevolutPaymentRepository.update_transaction_status()."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_update_transaction_status_success(
        self, mock_get_db, mock_collection
    ):
        """Test successful transaction status update."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "revolut_order_id": "ord_test_123456789",
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "merchant_test",
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": None,
            "payment_provider": "revolut",
            "booking_created": False,
            "created_at": now,
            "updated_at": now,
            "paid_at": now,
            "refunded_at": None,
            "payout_released_at": None,
            "payout_released_by": None,
            "payout_notes": None,
        }

        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one_and_update.return_value = updated_doc

        repo = RevolutPaymentRepository()
        result = await repo.update_transaction_status(
            order_id="ord_test_123456789",
            status=PaymentStatus.SUCCEEDED,
            paid_at=now,
        )

        # Verify find_one_and_update was called
        mock_collection.find_one_and_update.assert_called_once()
        call_args = mock_collection.find_one_and_update.call_args

        # Check filter - should include revolut_order_id and payment_provider
        filter_arg = call_args[0][0]
        assert filter_arg["revolut_order_id"] == "ord_test_123456789"
        assert filter_arg["payment_provider"] == "revolut"

        # Check update data
        update_arg = call_args[0][1]["$set"]
        assert update_arg["status"] == PaymentStatus.SUCCEEDED.value
        assert "paid_at" in update_arg
        assert "updated_at" in update_arg

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.revolut_order_id == "ord_test_123456789"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_update_transaction_status_with_payout(
        self, mock_get_db, mock_collection
    ):
        """Test transaction update with payout information."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "revolut_order_id": "ord_test_123456789",
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "merchant_test",
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": PayoutStatus.PAID.value,
            "payment_provider": "revolut",
            "revolut_payout_id": "payout_test_123",
            "booking_created": False,
            "created_at": now,
            "updated_at": now,
            "paid_at": None,
            "refunded_at": None,
            "payout_released_at": now,
            "payout_released_by": "admin_123",
            "payout_notes": "Test payout",
        }

        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one_and_update.return_value = updated_doc

        repo = RevolutPaymentRepository()
        result = await repo.update_transaction_status(
            order_id="ord_test_123456789",
            status=PaymentStatus.SUCCEEDED,
            revolut_payout_id="payout_test_123",
            payout_status=PayoutStatus.PAID.value,
        )

        call_args = mock_collection.find_one_and_update.call_args
        update_arg = call_args[0][1]["$set"]
        assert update_arg["revolut_payout_id"] == "payout_test_123"
        assert update_arg["payout_status"] == PayoutStatus.PAID.value

        # Verify result
        assert isinstance(result, TransactionModel)
        assert result.revolut_payout_id == "payout_test_123"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_update_transaction_status_minimal(
        self, mock_get_db, mock_collection
    ):
        """Test transaction update with minimal data (only status)."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "revolut_order_id": "ord_test_123456789",
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "merchant_test",
            "status": PaymentStatus.FAILED,
            "payout_status": None,
            "payment_provider": "revolut",
            "booking_created": False,
            "created_at": now,
            "updated_at": now,
            "paid_at": None,
            "refunded_at": None,
            "payout_released_at": None,
            "payout_released_by": None,
            "payout_notes": None,
        }

        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one_and_update.return_value = updated_doc

        repo = RevolutPaymentRepository()
        result = await repo.update_transaction_status(
            order_id="ord_test_123456789",
            status=PaymentStatus.FAILED,
        )

        call_args = mock_collection.find_one_and_update.call_args
        update_arg = call_args[0][1]["$set"]
        assert update_arg["status"] == PaymentStatus.FAILED.value
        assert "updated_at" in update_arg
        # Should not have optional fields
        assert "revolut_payout_id" not in update_arg

        # Verify result
        assert isinstance(result, TransactionModel)
        assert result.status == PaymentStatus.FAILED

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_update_transaction_status_not_found(
        self, mock_get_db, mock_collection
    ):
        """Test update when transaction not found."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one_and_update.return_value = None

        repo = RevolutPaymentRepository()
        result = await repo.update_transaction_status(
            order_id="ord_nonexistent",
            status=PaymentStatus.SUCCEEDED,
        )

        # Should return None when not found
        assert result is None


# ==============================================================================
# GET TRANSACTION TESTS
# ==============================================================================


class TestGetTransactionByOrderId:
    """Test RevolutPaymentRepository.get_transaction_by_order_id()."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_transaction_success(
        self, mock_get_db, mock_collection, sample_transaction_doc
    ):
        """Test successful transaction retrieval."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = sample_transaction_doc

        repo = RevolutPaymentRepository()
        result = await repo.get_transaction_by_order_id("ord_test_123456789")

        # Verify query - should include payment_provider filter
        mock_collection.find_one.assert_called_once_with(
            {"revolut_order_id": "ord_test_123456789", "payment_provider": "revolut"}
        )

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.revolut_order_id == "ord_test_123456789"
        assert result.voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_transaction_not_found(self, mock_get_db, mock_collection):
        """Test transaction retrieval when not found."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        repo = RevolutPaymentRepository()
        result = await repo.get_transaction_by_order_id("ord_nonexistent")

        # Repository returns None when not found (doesn't raise)
        assert result is None


class TestGetTransactionByVoyaReference:
    """Test RevolutPaymentRepository.get_transaction_by_voya_reference()."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_transaction_by_voya_reference_success(
        self, mock_get_db, mock_collection, sample_transaction_doc
    ):
        """Test successful transaction retrieval by Voya reference."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = sample_transaction_doc

        repo = RevolutPaymentRepository()
        result = await repo.get_transaction_by_voya_reference("VOYA-TEST123")

        # Verify query (includes sort to get most recent transaction and payment_provider filter)
        mock_collection.find_one.assert_called_once_with(
            {
                "voya_booking_reference": "VOYA-TEST123",
                "payment_provider": "revolut",
            },
            sort=[("created_at", -1)],
        )

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_transaction_by_voya_reference_not_found(
        self, mock_get_db, mock_collection
    ):
        """Test transaction retrieval by Voya reference when not found."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        repo = RevolutPaymentRepository()
        result = await repo.get_transaction_by_voya_reference("VOYA-NONEXISTENT")

        # Repository returns None when not found (doesn't raise)
        assert result is None


class TestGetAllTransactionsByVoyaReference:
    """Test RevolutPaymentRepository.get_all_transactions_by_voya_reference()."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_all_transactions_success(
        self, mock_get_db, mock_collection, sample_transaction_doc
    ):
        """Test successful retrieval of all transactions for a booking."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        # Mock cursor for find() operation
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[sample_transaction_doc])
        mock_collection.find.return_value = mock_cursor

        repo = RevolutPaymentRepository()
        results = await repo.get_all_transactions_by_voya_reference("VOYA-TEST123")

        # Verify find was called with correct filter
        mock_collection.find.assert_called_once_with(
            {
                "voya_booking_reference": "VOYA-TEST123",
                "payment_provider": "revolut",
            }
        )
        mock_cursor.sort.assert_called_once_with("created_at", -1)
        mock_cursor.to_list.assert_called_once_with(length=100)

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], TransactionModel)
        assert results[0].voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_all_transactions_empty(self, mock_get_db, mock_collection):
        """Test retrieval when no transactions exist."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        repo = RevolutPaymentRepository()
        results = await repo.get_all_transactions_by_voya_reference("VOYA-NONEXISTENT")

        # Should return empty list
        assert results == []

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_get_all_transactions_error_handling(
        self, mock_get_db, mock_collection
    ):
        """Test error handling when database query fails."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
        mock_collection.find.return_value = mock_cursor

        repo = RevolutPaymentRepository()
        results = await repo.get_all_transactions_by_voya_reference("VOYA-TEST123")

        # Should return empty list on error
        assert results == []


# ==============================================================================
# EDGE CASES
# ==============================================================================


class TestRevolutPaymentRepositoryEdgeCases:
    """Test edge cases and error handling."""

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_update_with_empty_kwargs(self, mock_get_db, mock_collection):
        """Test update with no optional parameters still sets updated_at."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "revolut_order_id": "ord_test_123456789",
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "merchant_test",
            "status": PaymentStatus.PROCESSING,
            "payout_status": None,
            "payment_provider": "revolut",
            "booking_created": False,
            "created_at": now,
            "updated_at": now,
            "paid_at": None,
            "refunded_at": None,
            "payout_released_at": None,
            "payout_released_by": None,
            "payout_notes": None,
        }

        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one_and_update.return_value = updated_doc

        repo = RevolutPaymentRepository()
        result = await repo.update_transaction_status(
            order_id="ord_test_123456789",
            status=PaymentStatus.PROCESSING,
        )

        call_args = mock_collection.find_one_and_update.call_args
        update_arg = call_args[0][1]["$set"]

        # Should always have status and updated_at
        assert update_arg["status"] == PaymentStatus.PROCESSING.value
        assert "updated_at" in update_arg
        assert len(update_arg) == 2  # Only status and updated_at

        # Verify result
        assert isinstance(result, TransactionModel)

    @patch("app.domains.revolut_payment.repository.get_database")
    async def test_create_transaction_with_all_fields(
        self, mock_get_db, mock_collection
    ):
        """Test creating transaction with all possible fields."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        transaction_id = ObjectId()
        mock_collection.insert_one.return_value = Mock(inserted_id=transaction_id)

        now = datetime.now(UTC)
        user_id = ObjectId()
        full_data = {
            "revolut_order_id": "ord_full_123",
            "voya_booking_reference": "VOYA-FULL123",
            "user_id": user_id,
            "amount": 50000,
            "currency": "usd",
            "platform_fee": 2500,
            "supplier_amount": 47500,
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": PayoutStatus.PAID.value,
            "payment_provider": "revolut",
        }

        repo = RevolutPaymentRepository()
        result = await repo.create_transaction(full_data)

        mock_collection.insert_one.assert_called_once()
        # Verify result is TransactionModel with correct attributes
        assert isinstance(result, TransactionModel)
        assert result.revolut_order_id == "ord_full_123"
        assert result.user_id == user_id
        assert result.amount == 50000
