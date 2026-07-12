"""Revolut payment repository for MongoDB transaction operations.

Uses the same transaction collection as Stripe but with Revolut-specific fields.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.database.dependencies import get_database
from app.domains.revolut_payment.constants import TRANSACTION_COLLECTION
from app.domains.revolut_payment.enums import PaymentStatus

if TYPE_CHECKING:
    from app.database.models.transaction import TransactionModel

logger = logging.getLogger(__name__)


class RevolutPaymentRepository:
    """Repository for Revolut payment transaction persistence."""

    async def create_transaction(
        self, transaction_data: dict[str, Any]
    ) -> "TransactionModel":
        """Create a new Revolut transaction record in MongoDB.

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
                "payment_provider": "revolut",  # Mark as Revolut transaction
            }

            final_data = {**defaults, **transaction_data}
            result = await db[TRANSACTION_COLLECTION].insert_one(final_data)
            final_data["_id"] = result.inserted_id

            logger.info(
                f"Created Revolut transaction {result.inserted_id} "
                f"for order {final_data.get('revolut_order_id')}"
            )

            return TransactionModel(**final_data)
        except Exception as e:
            logger.error(
                f"Error creating Revolut transaction for order {transaction_data.get('revolut_order_id')}: {e}"
            )
            raise

    async def update_transaction_status(
        self, order_id: str, status: PaymentStatus, **updates: Any
    ) -> "TransactionModel | None":
        """Update Revolut transaction status and additional fields.

        Args:
            order_id: Revolut order ID
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
            result = await db[TRANSACTION_COLLECTION].find_one_and_update(
                {"revolut_order_id": order_id, "payment_provider": "revolut"},
                {"$set": update_data},
                return_document=True,
            )

            if result:
                logger.info(
                    f"Updated Revolut transaction for order {order_id} to status: {status.value}"
                )
                return TransactionModel(**result)
            logger.warning(f"No Revolut transaction found for order {order_id}")
            return None
        except Exception as e:
            logger.error(
                f"Error updating Revolut transaction status for order {order_id}: {e}"
            )
            return None

    async def get_transaction_by_order_id(
        self, order_id: str
    ) -> "TransactionModel | None":
        """Get transaction by Revolut order ID.

        Args:
            order_id: Revolut order ID

        Returns:
            Transaction model or None if not found
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()
            result = await db[TRANSACTION_COLLECTION].find_one(
                {"revolut_order_id": order_id, "payment_provider": "revolut"}
            )
            return TransactionModel(**result) if result else None
        except Exception as e:
            logger.error(f"Error getting Revolut transaction by order {order_id}: {e}")
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
            result = await db[TRANSACTION_COLLECTION].find_one(
                {
                    "voya_booking_reference": voya_booking_reference,
                    "payment_provider": "revolut",
                },
                sort=[("created_at", -1)],  # Get most recent transaction
            )
            return TransactionModel(**result) if result else None
        except Exception as e:
            logger.error(
                f"Error getting Revolut transaction by voya reference {voya_booking_reference}: {e}"
            )
            return None

    async def get_all_transactions_by_voya_reference(
        self, voya_booking_reference: str
    ) -> list["TransactionModel"]:
        """Get all Revolut transactions for a VOYA booking reference.

        Used to check for duplicate payments and prevent multiple charges.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX reference

        Returns:
            List of transaction models (may be empty)
        """
        from app.database.models.transaction import TransactionModel

        try:
            db = await get_database()
            cursor = (
                db[TRANSACTION_COLLECTION]
                .find(
                    {
                        "voya_booking_reference": voya_booking_reference,
                        "payment_provider": "revolut",
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
                f"Error getting Revolut transactions by voya reference {voya_booking_reference}: {e}"
            )
            return []
