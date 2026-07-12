"""Payment repository for MongoDB transaction operations."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.database.dependencies import get_database
from app.domains.payment.constants import TRANSACTION_COLLECTION
from app.domains.payment.enums import PaymentStatus

if TYPE_CHECKING:
    from app.database.models.transaction import TransactionModel

logger = logging.getLogger(__name__)


class PaymentRepository:
    """Repository for payment transaction persistence."""

    async def create_transaction(
        self, transaction_data: dict[str, Any]
    ) -> "TransactionModel":
        """Create a new transaction record in MongoDB.

        Args:
            transaction_data: Transaction data dictionary

        Returns:
            Created transaction model

        Raises:
            Exception: If database operation fails
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()

            # Set defaults
            now = datetime.now(UTC)
            defaults = {
                "created_at": now,
                "updated_at": now,
                "payment_provider": "stripe",  # Mark as Stripe transaction
            }

            final_data = {**defaults, **transaction_data}
            result = await db[TRANSACTION_COLLECTION].insert_one(final_data)
            final_data["_id"] = result.inserted_id

            logger.info(
                f"Created transaction {result.inserted_id} "
                f"for payment {final_data.get('stripe_payment_intent_id')}"
            )

            return TransactionModel(**final_data)
        except Exception as e:
            logger.error(
                f"Error creating transaction for payment {transaction_data.get('stripe_payment_intent_id')}: {e}"
            )
            raise

    async def update_transaction_status(
        self, payment_intent_id: str, status: PaymentStatus, **updates: Any
    ) -> "TransactionModel | None":
        """Update transaction status and additional fields.

        Args:
            payment_intent_id: Stripe payment intent ID
            status: New payment status
            **updates: Additional fields to update

        Returns:
            Updated transaction model or None if not found
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()

            update_data = {
                "status": status.value,
                "updated_at": datetime.now(UTC),
                **updates,
            }

            # Use find_one_and_update to return updated document
            # Filter by payment_provider to ensure we only update Stripe transactions
            result = await db[TRANSACTION_COLLECTION].find_one_and_update(
                {
                    "stripe_payment_intent_id": payment_intent_id,
                    "payment_provider": "stripe",
                },
                {"$set": update_data},
                return_document=True,
            )

            if result:
                logger.info(
                    f"Updated transaction for payment {payment_intent_id} to status: {status.value}"
                )
                return TransactionModel(**result)
            logger.warning(
                f"No transaction found for payment intent {payment_intent_id}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error updating transaction status for payment {payment_intent_id}: {e}"
            )
            return None

    async def get_transaction_by_payment_intent(
        self, payment_intent_id: str
    ) -> "TransactionModel | None":
        """Get transaction by Stripe payment intent ID.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Transaction model or None if not found
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()
            # Filter by payment_provider to ensure we only get Stripe transactions
            result = await db[TRANSACTION_COLLECTION].find_one(
                {
                    "stripe_payment_intent_id": payment_intent_id,
                    "payment_provider": "stripe",
                }
            )
            return TransactionModel(**result) if result else None
        except Exception as e:
            logger.error(
                f"Error getting transaction by payment intent {payment_intent_id}: {e}"
            )
            return None

    async def get_transaction_by_voya_reference(
        self, voya_booking_reference: str
    ) -> "TransactionModel | None":
        """Get transaction by VOYA booking reference.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX reference

        Returns:
            Transaction model or None if not found
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()
            # Filter by payment_provider to ensure we only get Stripe transactions
            result = await db[TRANSACTION_COLLECTION].find_one(
                {
                    "voya_booking_reference": voya_booking_reference,
                    "payment_provider": "stripe",
                },
                sort=[("created_at", -1)],  # Get most recent transaction
            )
            return TransactionModel(**result) if result else None
        except Exception as e:
            logger.error(
                f"Error getting transaction by voya reference {voya_booking_reference}: {e}"
            )
            return None

    async def get_all_transactions_by_voya_reference(
        self, voya_booking_reference: str
    ) -> list["TransactionModel"]:
        """Get all transactions for a VOYA booking reference.

        Used to check for duplicate payments and prevent multiple charges.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX reference

        Returns:
            List of transaction models (may be empty)
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()
            # Filter by payment_provider to ensure we only get Stripe transactions
            cursor = (
                db[TRANSACTION_COLLECTION]
                .find(
                    {
                        "voya_booking_reference": voya_booking_reference,
                        "payment_provider": "stripe",
                    }
                )
                .sort("created_at", -1)
            )
            results = await cursor.to_list(
                length=100
            )  # Max 100 transactions per booking
            return [TransactionModel(**result) for result in results]
        except Exception as e:
            logger.error(
                f"Error getting transactions by voya reference {voya_booking_reference}: {e}"
            )
            return []
