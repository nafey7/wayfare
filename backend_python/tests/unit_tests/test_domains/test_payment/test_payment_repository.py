"""Unit tests for PaymentRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.database.models.transaction import TransactionModel
from app.domains.payment import PaymentRepository, PaymentStatus, PayoutStatus

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
    return collection


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for creating records."""
    return {
        "stripe_payment_intent_id": "pi_test_123456789",
        "voya_booking_reference": "VOYA-TEST123",
        "user_id": ObjectId(),  # Use actual ObjectId
        "amount": 10000,
        "platform_fee": 500,
        "supplier_amount": 9500,
        "status": PaymentStatus.PENDING,  # Use enum directly
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest.fixture
def sample_transaction_doc():
    """Sample transaction document from MongoDB."""
    now = datetime.now(UTC)
    return {
        "_id": ObjectId(),
        "stripe_payment_intent_id": "pi_test_123456789",
        "stripe_charge_id": "ch_test_123",
        "stripe_transfer_id": None,
        "refund_id": None,
        "voya_booking_reference": "VOYA-TEST123",
        "user_id": ObjectId(),
        "amount": 10000,
        "currency": "usd",
        "platform_fee": 500,
        "supplier_amount": 9500,
        "destination_account_id": "acct_test",
        "status": PaymentStatus.SUCCEEDED,  # Use enum directly
        "payout_status": None,
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
    """Test PaymentRepository.create_transaction()."""

    @patch("app.domains.payment.repository.get_database")
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
        repo = PaymentRepository()
        result = await repo.create_transaction(sample_transaction_data)

        # Verify insert was called once (data includes defaults)
        mock_collection.insert_one.assert_called_once()
        # Verify result is TransactionModel with correct attributes
        assert isinstance(result, TransactionModel)
        assert result.stripe_payment_intent_id == "pi_test_123456789"
        assert result.voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.payment.repository.get_database")
    async def test_create_transaction_database_error(
        self, mock_get_db, mock_collection, sample_transaction_data
    ):
        """Test transaction creation when database fails."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.side_effect = Exception("Database error")

        repo = PaymentRepository()

        with pytest.raises(Exception) as exc_info:
            await repo.create_transaction(sample_transaction_data)

        assert "Database error" in str(exc_info.value)


# ==============================================================================
# UPDATE TRANSACTION STATUS TESTS
# ==============================================================================


class TestUpdateTransactionStatus:
    """Test PaymentRepository.update_transaction_status()."""

    @patch("app.domains.payment.repository.get_database")
    async def test_update_transaction_status_success(
        self, mock_get_db, mock_collection
    ):
        """Test successful transaction status update."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "stripe_payment_intent_id": "pi_test_123456789",
            "stripe_charge_id": "ch_test_123",
            "stripe_transfer_id": None,
            "refund_id": None,
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "acct_test",
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": None,
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

        repo = PaymentRepository()
        result = await repo.update_transaction_status(
            payment_intent_id="pi_test_123456789",
            status=PaymentStatus.SUCCEEDED,
            stripe_charge_id="ch_test_123",
            paid_at=now,
        )

        # Verify find_one_and_update was called
        mock_collection.find_one_and_update.assert_called_once()
        call_args = mock_collection.find_one_and_update.call_args

        # Check filter
        filter_arg = call_args[0][0]
        assert filter_arg["stripe_payment_intent_id"] == "pi_test_123456789"

        # Check update data
        update_arg = call_args[0][1]["$set"]
        assert update_arg["status"] == PaymentStatus.SUCCEEDED.value
        assert update_arg["stripe_charge_id"] == "ch_test_123"
        assert "paid_at" in update_arg
        assert "updated_at" in update_arg

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.stripe_payment_intent_id == "pi_test_123456789"

    @patch("app.domains.payment.repository.get_database")
    async def test_update_transaction_status_with_payout(
        self, mock_get_db, mock_collection
    ):
        """Test transaction update with payout information."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "stripe_payment_intent_id": "pi_test_123456789",
            "stripe_charge_id": None,
            "stripe_transfer_id": "tr_test_123",
            "refund_id": None,
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "acct_test",
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": PayoutStatus.IN_TRANSIT,
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

        repo = PaymentRepository()
        result = await repo.update_transaction_status(
            payment_intent_id="pi_test_123456789",
            status=PaymentStatus.SUCCEEDED,
            stripe_transfer_id="tr_test_123",
            payout_status=PayoutStatus.IN_TRANSIT.value,
        )

        call_args = mock_collection.find_one_and_update.call_args
        update_arg = call_args[0][1]["$set"]
        assert update_arg["stripe_transfer_id"] == "tr_test_123"
        assert update_arg["payout_status"] == PayoutStatus.IN_TRANSIT.value

        # Verify result
        assert isinstance(result, TransactionModel)
        assert result.stripe_transfer_id == "tr_test_123"

    @patch("app.domains.payment.repository.get_database")
    async def test_update_transaction_status_minimal(
        self, mock_get_db, mock_collection
    ):
        """Test transaction update with minimal data (only status)."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "stripe_payment_intent_id": "pi_test_123456789",
            "stripe_charge_id": None,
            "stripe_transfer_id": None,
            "refund_id": None,
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "acct_test",
            "status": PaymentStatus.FAILED,
            "payout_status": None,
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

        repo = PaymentRepository()
        result = await repo.update_transaction_status(
            payment_intent_id="pi_test_123456789",
            status=PaymentStatus.FAILED,
        )

        call_args = mock_collection.find_one_and_update.call_args
        update_arg = call_args[0][1]["$set"]
        assert update_arg["status"] == PaymentStatus.FAILED.value
        assert "updated_at" in update_arg
        # Should not have optional fields
        assert "stripe_charge_id" not in update_arg
        assert "stripe_transfer_id" not in update_arg

        # Verify result
        assert isinstance(result, TransactionModel)
        assert result.status == PaymentStatus.FAILED


# ==============================================================================
# GET TRANSACTION TESTS
# ==============================================================================


class TestGetTransactionByPaymentIntent:
    """Test PaymentRepository.get_transaction_by_payment_intent()."""

    @patch("app.domains.payment.repository.get_database")
    async def test_get_transaction_success(
        self, mock_get_db, mock_collection, sample_transaction_doc
    ):
        """Test successful transaction retrieval."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = sample_transaction_doc

        repo = PaymentRepository()
        result = await repo.get_transaction_by_payment_intent("pi_test_123456789")

        # Verify query
        mock_collection.find_one.assert_called_once_with(
            {
                "stripe_payment_intent_id": "pi_test_123456789",
                "payment_provider": "stripe",
            }
        )

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.stripe_payment_intent_id == "pi_test_123456789"
        assert result.voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.payment.repository.get_database")
    async def test_get_transaction_not_found(self, mock_get_db, mock_collection):
        """Test transaction retrieval when not found."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        repo = PaymentRepository()
        result = await repo.get_transaction_by_payment_intent("pi_nonexistent")

        # Repository returns None when not found (doesn't raise)
        assert result is None


class TestGetTransactionByVoyaReference:
    """Test PaymentRepository.get_transaction_by_voya_reference()."""

    @patch("app.domains.payment.repository.get_database")
    async def test_get_transaction_by_voya_reference_success(
        self, mock_get_db, mock_collection, sample_transaction_doc
    ):
        """Test successful transaction retrieval by Voya reference."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = sample_transaction_doc

        repo = PaymentRepository()
        result = await repo.get_transaction_by_voya_reference("VOYA-TEST123")

        # Verify query (includes sort to get most recent transaction)
        mock_collection.find_one.assert_called_once_with(
            {"voya_booking_reference": "VOYA-TEST123", "payment_provider": "stripe"},
            sort=[("created_at", -1)],
        )

        # Verify result is TransactionModel
        assert isinstance(result, TransactionModel)
        assert result.voya_booking_reference == "VOYA-TEST123"

    @patch("app.domains.payment.repository.get_database")
    async def test_get_transaction_by_voya_reference_not_found(
        self, mock_get_db, mock_collection
    ):
        """Test transaction retrieval by Voya reference when not found."""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        repo = PaymentRepository()
        result = await repo.get_transaction_by_voya_reference("VOYA-NONEXISTENT")

        # Repository returns None when not found (doesn't raise)
        assert result is None


# ==============================================================================
# EDGE CASES
# ==============================================================================


class TestPaymentRepositoryEdgeCases:
    """Test edge cases and error handling."""

    @patch("app.domains.payment.repository.get_database")
    async def test_update_with_empty_kwargs(self, mock_get_db, mock_collection):
        """Test update with no optional parameters still sets updated_at."""
        now = datetime.now(UTC)
        updated_doc = {
            "_id": ObjectId(),
            "stripe_payment_intent_id": "pi_test_123456789",
            "stripe_charge_id": None,
            "stripe_transfer_id": None,
            "refund_id": None,
            "voya_booking_reference": "VOYA-TEST123",
            "user_id": None,
            "amount": 10000,
            "currency": "usd",
            "platform_fee": 500,
            "supplier_amount": 9500,
            "destination_account_id": "acct_test",
            "status": PaymentStatus.PROCESSING,
            "payout_status": None,
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

        repo = PaymentRepository()
        result = await repo.update_transaction_status(
            payment_intent_id="pi_test_123456789",
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

    @patch("app.domains.payment.repository.get_database")
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
            "stripe_payment_intent_id": "pi_full_123",
            "stripe_charge_id": "ch_full_123",
            "stripe_transfer_id": "tr_full_123",
            "voya_booking_reference": "VOYA-FULL123",
            "user_id": user_id,
            "amount": 50000,
            "currency": "usd",
            "platform_fee": 2500,
            "supplier_amount": 47500,
            "status": PaymentStatus.SUCCEEDED,
            "payout_status": PayoutStatus.PAID.value,
        }

        repo = PaymentRepository()
        result = await repo.create_transaction(full_data)

        mock_collection.insert_one.assert_called_once()
        # Verify result is TransactionModel with correct attributes
        assert isinstance(result, TransactionModel)
        assert result.stripe_payment_intent_id == "pi_full_123"
        assert result.user_id == user_id
        assert result.amount == 50000
