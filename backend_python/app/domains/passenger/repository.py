"""Passenger repository - CRUD with encryption at repository layer."""

import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database.constants import PASSENGERS_COLLECTION
from app.database.dependencies import get_database
from app.domains.passenger.categories import derive_hotel_title, derive_type_hotel
from app.domains.passenger.encryption import (
    decrypt_document,
    encrypt_document,
    encrypt_field,
)
from app.domains.passenger.schemas import (
    ENCRYPTED_FIELDS,
    PassengerCreate,
    PassengerMasked,
    PassengerResponse,
    PassengerUpdate,
    mask_date,
    mask_sensitive,
)

logger = logging.getLogger(__name__)


def _get_hotel_title(doc: dict[str, Any]) -> str:
    """Get hotel_title from doc or derive from title + date_of_birth (backward compat)."""
    if doc.get("hotel_title"):
        return doc["hotel_title"]
    return derive_hotel_title(doc.get("title", ""), doc.get("date_of_birth"))


def _get_type_hotel(doc: dict[str, Any]) -> str:
    """Get type_hotel from doc or derive from date_of_birth (backward compat)."""
    if doc.get("type_hotel"):
        return doc["type_hotel"]
    return derive_type_hotel(doc.get("date_of_birth"))


def _field_value(doc: dict[str, Any], decrypted: dict[str, Any], field: str) -> Any:
    """Get field value: use decrypted for ENCRYPTED_FIELDS, else doc (future-proof)."""
    return decrypted.get(field) if field in ENCRYPTED_FIELDS else doc.get(field)


def _doc_to_masked(doc: dict[str, Any], decrypted: dict[str, Any]) -> PassengerMasked:
    """Convert DB document to masked response. Uses decrypted values for masking."""
    return PassengerMasked(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        is_primary=bool(doc.get("is_primary", False)),
        title=doc["title"],
        hotel_title=_get_hotel_title(doc),
        type_hotel=_get_type_hotel(doc),
        first_name=doc["first_name"],
        last_name=doc["last_name"],
        date_of_birth=doc["date_of_birth"],
        nationality=doc["nationality"],
        email=_field_value(doc, decrypted, "email"),
        phone=_field_value(doc, decrypted, "phone"),
        passport_number=mask_sensitive(_field_value(doc, decrypted, "passport_number")),
        passport_expiry=mask_date(_field_value(doc, decrypted, "passport_expiry")),
        passport_country=_field_value(doc, decrypted, "passport_country"),
        frequent_flyer_number=mask_sensitive(
            _field_value(doc, decrypted, "frequent_flyer_number")
        ),
        type=doc.get("type"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _doc_to_response(
    doc: dict[str, Any], decrypted: dict[str, Any]
) -> PassengerResponse:
    """Convert DB document to full response (with decrypted sensitive fields)."""
    return PassengerResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        is_primary=bool(doc.get("is_primary", False)),
        title=doc["title"],
        hotel_title=_get_hotel_title(doc),
        type_hotel=_get_type_hotel(doc),
        first_name=doc["first_name"],
        last_name=doc["last_name"],
        date_of_birth=doc["date_of_birth"],
        nationality=doc["nationality"],
        email=_field_value(doc, decrypted, "email"),
        phone=_field_value(doc, decrypted, "phone"),
        passport_number=_field_value(doc, decrypted, "passport_number"),
        passport_expiry=_field_value(doc, decrypted, "passport_expiry"),
        passport_country=_field_value(doc, decrypted, "passport_country"),
        frequent_flyer_number=_field_value(doc, decrypted, "frequent_flyer_number"),
        type=doc.get("type"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _build_doc(user_id: str, data: PassengerCreate) -> dict[str, Any]:
    """Build MongoDB document from create data."""
    raw = data.model_dump(exclude_none=True)

    now = datetime.now(UTC)
    title = raw.get("title", "")
    date_of_birth = raw.get("date_of_birth")
    is_primary = raw.get("is_primary", False)

    doc: dict[str, Any] = {
        "user_id": ObjectId(user_id),
        "is_primary": is_primary,
        "title": title,
        "hotel_title": derive_hotel_title(title, date_of_birth),
        "type_hotel": derive_type_hotel(date_of_birth),
        "first_name": raw.get("first_name", ""),
        "last_name": raw.get("last_name", ""),
        "date_of_birth": raw.get("date_of_birth", ""),
        "nationality": raw.get("nationality", ""),
        "email": raw.get("email"),
        "phone": raw.get("phone"),
        "passport_number": raw.get("passport_number"),
        "passport_expiry": raw.get("passport_expiry"),
        "passport_country": raw.get("passport_country"),
        "frequent_flyer_number": raw.get("frequent_flyer_number"),
        "type": raw.get("type"),
        "created_at": now,
        "updated_at": now,
    }
    return doc


async def create_passenger(user_id: str, data: PassengerCreate) -> PassengerMasked:
    """Create a new passenger for the user. Encrypts sensitive fields before insert."""
    db = await get_database()
    coll = db[PASSENGERS_COLLECTION]

    doc = _build_doc(user_id, data)
    if doc.get("is_primary"):
        await coll.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"is_primary": False, "updated_at": datetime.now(UTC)}},
        )
    doc = encrypt_document(doc)

    result = await coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["user_id"] = str(user_id)
    decrypted = decrypt_document(dict(doc))
    return _doc_to_masked(doc, decrypted)


async def get_passengers_for_user(user_id: str) -> list[PassengerMasked]:
    """Get all passengers for a user. Primary first, then by created_at. Returns masked."""
    db = await get_database()
    coll = db[PASSENGERS_COLLECTION]

    cursor = coll.find({"user_id": ObjectId(user_id)}).sort(
        [("is_primary", -1), ("created_at", 1)]
    )
    docs = await cursor.to_list(length=100)

    result = []
    for d in docs:
        doc = dict(d)
        decrypted = decrypt_document(doc)
        result.append(_doc_to_masked(doc, decrypted))
    return result


async def get_passenger_by_id(
    passenger_id: str,
    user_id: str,
    *,
    include_sensitive: bool = False,
) -> PassengerMasked | PassengerResponse | None:
    """Get a passenger by ID. Must belong to user. Optionally return full (decrypted) data."""
    db = await get_database()
    coll = db[PASSENGERS_COLLECTION]

    try:
        oid = ObjectId(passenger_id)
    except Exception:
        return None

    raw = await coll.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if not raw:
        return None

    doc = dict(raw)
    doc["user_id"] = str(user_id)
    doc["id"] = str(doc["_id"])

    decrypted = decrypt_document(doc)
    if include_sensitive:
        return _doc_to_response(doc, decrypted)
    return _doc_to_masked(doc, decrypted)


async def update_passenger(
    passenger_id: str,
    user_id: str,
    data: PassengerUpdate,
) -> PassengerMasked | None:
    """Update a passenger. Encrypts sensitive fields. Returns None if not found."""
    db = await get_database()
    coll = db[PASSENGERS_COLLECTION]

    try:
        oid = ObjectId(passenger_id)
    except Exception:
        return None

    update_payload = data.model_dump(exclude_unset=True)
    if not update_payload:
        raw = await coll.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if raw:
            doc = dict(raw)
            doc["user_id"] = str(user_id)
            doc["id"] = str(doc["_id"])
            decrypted = decrypt_document(doc)
            return _doc_to_masked(doc, decrypted)
        return None

    # Fetch existing doc for hotel_title derivation (merge title + date_of_birth)
    raw_existing = await coll.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    merged_title = raw_existing.get("title", "") if raw_existing else ""
    merged_dob = raw_existing.get("date_of_birth") if raw_existing else None
    if "title" in update_payload and update_payload["title"] is not None:
        merged_title = update_payload["title"]
    if (
        "date_of_birth" in update_payload
        and update_payload["date_of_birth"] is not None
    ):
        merged_dob = update_payload["date_of_birth"]

    now = datetime.now(UTC)
    set_data: dict[str, Any] = {
        "updated_at": now,
        "hotel_title": derive_hotel_title(merged_title, merged_dob),
        "type_hotel": derive_type_hotel(merged_dob),
    }
    unset_data: dict[str, Any] = {}

    if update_payload.get("is_primary") is True:
        await coll.update_many(
            {"user_id": ObjectId(user_id), "_id": {"$ne": oid}},
            {"$set": {"is_primary": False, "updated_at": now}},
        )

    # Support explicit null clears via $unset and encrypt sensitive $set values.
    for field, value in update_payload.items():
        if value is None:
            unset_data[field] = ""
            continue
        if field in ENCRYPTED_FIELDS and isinstance(value, str) and value:
            set_data[field] = encrypt_field(value)
            continue
        set_data[field] = value

    update_doc: dict[str, Any] = {"$set": set_data}
    if unset_data:
        update_doc["$unset"] = unset_data

    raw_result = await coll.find_one_and_update(
        {"_id": oid, "user_id": ObjectId(user_id)},
        update_doc,
        return_document=True,
    )
    if not raw_result:
        return None

    result = dict(raw_result)
    result["user_id"] = str(user_id)
    result["id"] = str(result["_id"])
    decrypted = decrypt_document(result)
    return _doc_to_masked(result, decrypted)


async def delete_passenger(passenger_id: str, user_id: str) -> bool:
    """Delete a passenger. Physically removes the document (GDPR right to deletion)."""
    db = await get_database()
    coll = db[PASSENGERS_COLLECTION]

    try:
        oid = ObjectId(passenger_id)
    except Exception:
        return False

    result = await coll.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
    return result.deleted_count > 0
