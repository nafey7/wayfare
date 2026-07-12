"""Booking event persistence (MongoDB)."""

from typing import Any

from pymongo.results import UpdateResult

from app.database.dependencies import get_database
from app.domains.bookings.constants import BOOKING_EVENT_COLLECTION, TEMP_EXTERNAL_REF


class BookingRepository:
    """Repository for booking event documents."""

    async def update_gds_pending_booking_to_booked(
        self,
        voya_booking_reference: str,
        set_fields: dict[str, Any],
        unset_fields: dict[str, str] | None = None,
    ) -> UpdateResult:
        """Apply ``$set`` (and optional ``$unset``) to the GDS PENDING row (TEMP-REF).

        The service layer builds ``set_fields`` (external ref, PNR, dates, etc.). The filter
        is fixed here: PENDING + TEMP-REF + GDS so LCC TEMP-REF rows and completed bookings
        are not matched.
        """
        db = await get_database()
        update_doc: dict[str, Any] = {"$set": set_fields}
        if unset_fields:
            update_doc["$unset"] = unset_fields
        return await db[BOOKING_EVENT_COLLECTION].update_one(
            {
                "voya_booking_reference": voya_booking_reference,
                "external_booking_reference": TEMP_EXTERNAL_REF,
                "action": "PENDING",
                "carrier_type": "GDS",
            },
            update_doc,
        )
