"""Saved itinerary repository - CRUD operations."""

import logging
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.constants import (
    BOOKING_EVENT_COLLECTION,
    SAVED_ITINERARIES_COLLECTION,
)
from app.database.dependencies import get_database
from app.database.flight_route import (
    departure_iata_from_route_legs_raw,
    parse_route_legs_from_document,
)

from .schemas import (
    LinkedBookingEventSummary,
    LinkedBookings,
    SavedItineraryCreate,
    SavedItineraryResponse,
)

logger = logging.getLogger(__name__)

# Max documents returned by GET /itineraries (newest first). Documented on the route.
SAVED_ITINERARIES_LIST_LIMIT = 100

# Cap linked refs per type per itinerary (newest first; see fetch_linked_bookings_for_itinerary_ids).
_MAX_LINKS_PER_TYPE = 5
# Max booking_events documents read per query; UI shows at most _MAX_LINKS_PER_TYPE per type.
_LINKED_BOOKING_QUERY_DOCS_LIMIT = 500

# Index names — single source for migration ``004_saved_itineraries_indexes`` and startup.
SAVED_ITINERARIES_INDEX_USER_CREATED = "idx_saved_itineraries_user_created"
SAVED_ITINERARIES_INDEX_USER_CHAT_UNIQUE = "uniq_saved_itineraries_user_chat"


async def ensure_saved_itinerary_indexes(
    db: AsyncIOMotorDatabase | None = None,
) -> None:
    """Ensure indexes on ``saved_itineraries`` (idempotent).

    Used by migration 004 and optionally at app startup so dev DBs that skip
    migrations still get list and chat-scoped uniqueness indexes.
    """
    resolved = db if db is not None else await get_database()
    coll = resolved[SAVED_ITINERARIES_COLLECTION]
    await coll.create_index(
        [("user_id", 1), ("created_at", -1)],
        name=SAVED_ITINERARIES_INDEX_USER_CREATED,
    )
    await coll.create_index(
        [("user_id", 1), ("chat_id", 1)],
        name=SAVED_ITINERARIES_INDEX_USER_CHAT_UNIQUE,
        unique=True,
        partialFilterExpression={"chat_id": {"$type": "string"}},
    )


def _user_id_match_clause(user_id: str) -> dict[str, Any]:
    """Match booking_events where user_id is ObjectId or string (legacy / export variance)."""
    uid = str(user_id).strip()
    try:
        oid = ObjectId(uid)
    except InvalidId:
        return {"user_id": uid}
    return {"$or": [{"user_id": oid}, {"user_id": uid}]}


def _saved_itinerary_id_in_clause(oids: list[ObjectId]) -> dict[str, Any]:
    """Match saved_itinerary_id stored as ObjectId or string."""
    values: list[Any] = []
    for o in oids:
        values.append(o)
        values.append(str(o))
    return {"saved_itinerary_id": {"$in": values}}


def _normalize_saved_itinerary_key(sid_raw: Any) -> str | None:
    """Canonical key for grouping into flight_by_sid / hotel_by_sid (matches valid_ids)."""
    if sid_raw is None:
        return None
    if isinstance(sid_raw, ObjectId):
        return str(sid_raw)
    s = str(sid_raw).strip()
    try:
        return str(ObjectId(s))
    except InvalidId:
        return s


def _booking_doc_to_summary(doc: Mapping[str, Any]) -> LinkedBookingEventSummary | None:
    """Build API row from a booking_events document; None if reference missing."""
    ref = doc.get("voya_booking_reference")
    if not ref or not str(ref).strip():
        return None
    et_raw = doc.get("event_type") or "FLIGHT"
    event_type: Literal["FLIGHT", "HOTEL"] = "HOTEL" if et_raw == "HOTEL" else "FLIGHT"
    ts = doc.get("timestamp")
    if not isinstance(ts, datetime):
        ts = datetime.now(UTC)
    db = doc.get("date_booked")
    date_booked = db if isinstance(db, datetime) else None
    raw_ft = doc.get("flight_trip_type")
    flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = (
        raw_ft if raw_ft in ("one_way", "round_trip", "multi_city") else None
    )
    route_legs = parse_route_legs_from_document(
        doc.get("route_legs"),
        booking_id=str(doc.get("_id")) if doc.get("_id") is not None else None,
    )
    dep = departure_iata_from_route_legs_raw(doc.get("route_legs"))
    if dep is None:
        draw = doc.get("departure_airport_iata")
        if isinstance(draw, str) and len(draw.strip()) == 3:
            dep = draw.strip().upper()
    return LinkedBookingEventSummary(
        voya_booking_reference=str(ref).strip(),
        event_type=event_type,
        timestamp=ts,
        amount=float(doc["amount"])
        if isinstance(doc.get("amount"), (int, float))
        else None,
        ticket_status=doc.get("ticket_status")
        if isinstance(doc.get("ticket_status"), str)
        else None,
        airline_pnr_code=doc.get("airline_pnr_code")
        if isinstance(doc.get("airline_pnr_code"), str)
        else None,
        airline_pnr_airline_name=doc.get("airline_pnr_airline_name")
        if isinstance(doc.get("airline_pnr_airline_name"), str)
        else None,
        primary_marketing_airline_name=doc.get("primary_marketing_airline_name")
        if isinstance(doc.get("primary_marketing_airline_name"), str)
        else None,
        flight_trip_type=flight_trip_type,
        route_legs=route_legs,
        departure_airport_iata=dep,
        hotel_reference_number=doc.get("hotel_reference_number")
        if isinstance(doc.get("hotel_reference_number"), str)
        else None,
        date_booked=date_booked,
    )


def _doc_to_response(doc: dict[str, Any]) -> SavedItineraryResponse:
    """Convert DB document to response schema."""
    created_at = doc["created_at"]
    updated_raw = doc.get("updated_at")
    updated_at = updated_raw if isinstance(updated_raw, datetime) else created_at
    return SavedItineraryResponse(
        id=str(doc["_id"]),
        structured_itinerary=doc["structured_itinerary"],
        trip_meta=doc.get("trip_meta"),
        created_at=created_at,
        updated_at=updated_at,
    )


async def fetch_linked_bookings_for_itinerary_ids(
    user_id: str, itinerary_ids: list[str]
) -> dict[str, LinkedBookings]:
    """Load VOYA booking refs from booking_events grouped by saved itinerary.

    Returns one entry per valid itinerary id string; empty lists when no bookings.

    Uses the most recent booking events per user/itinerary match, capped at
    ``_LINKED_BOOKING_QUERY_DOCS_LIMIT`` documents total (sorted by timestamp
    descending). Each itinerary still surfaces at most ``_MAX_LINKS_PER_TYPE``
    flight and hotel refs in the API response.
    """
    if not itinerary_ids:
        return {}

    valid_ids: list[str] = []
    oids: list[ObjectId] = []
    for sid in itinerary_ids:
        try:
            oids.append(ObjectId(str(sid).strip()))
            valid_ids.append(str(sid).strip())
        except InvalidId:
            continue

    if not oids:
        return {}

    db = await get_database()
    coll = db[BOOKING_EVENT_COLLECTION]

    cursor = coll.find(
        {
            "$and": [
                _user_id_match_clause(user_id),
                _saved_itinerary_id_in_clause(oids),
                {"action": "BOOKED"},
                {"voya_booking_reference": {"$exists": True, "$nin": [None, ""]}},
            ]
        }
    ).sort("timestamp", -1)
    docs = await cursor.to_list(length=_LINKED_BOOKING_QUERY_DOCS_LIMIT)

    flight_by_sid: dict[str, list[str]] = defaultdict(list)
    hotel_by_sid: dict[str, list[str]] = defaultdict(list)
    flight_events_by_sid: dict[str, list[LinkedBookingEventSummary]] = defaultdict(list)
    hotel_events_by_sid: dict[str, list[LinkedBookingEventSummary]] = defaultdict(list)

    for doc in docs:
        sid_raw = doc.get("saved_itinerary_id")
        sid_str = _normalize_saved_itinerary_key(sid_raw)
        if not sid_str:
            continue
        ref = doc.get("voya_booking_reference")
        if not ref:
            continue
        et = doc.get("event_type") or "FLIGHT"
        summary = _booking_doc_to_summary(doc)
        if et == "HOTEL":
            bucket = hotel_by_sid[sid_str]
            if len(bucket) < _MAX_LINKS_PER_TYPE and ref not in bucket:
                bucket.append(ref)
                if summary is not None:
                    hotel_events_by_sid[sid_str].append(summary)
        else:
            bucket = flight_by_sid[sid_str]
            if len(bucket) < _MAX_LINKS_PER_TYPE and ref not in bucket:
                bucket.append(ref)
                if summary is not None:
                    flight_events_by_sid[sid_str].append(summary)

    result: dict[str, LinkedBookings] = {}
    for sid in valid_ids:
        result[sid] = LinkedBookings(
            flight_voya_references=list(flight_by_sid.get(sid, [])),
            hotel_voya_references=list(hotel_by_sid.get(sid, [])),
            flight_events=list(flight_events_by_sid.get(sid, [])),
            hotel_events=list(hotel_events_by_sid.get(sid, [])),
        )
    return result


async def relink_saved_itineraries_to_user(chat_id: str, user_id: str) -> int:
    """Defensive: attach ``user_id`` to ``saved_itineraries`` docs matching
    ``chat_id`` that have no owner yet (post guest-chat claim).

    Returns the count of documents updated.
    """
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]
    result = await coll.update_many(
        {"chat_id": str(chat_id).strip(), "user_id": {"$exists": False}},
        {
            "$set": {
                "user_id": ObjectId(user_id),
                "updated_at": datetime.now(UTC),
            }
        },
    )
    return int(result.modified_count)


async def create_saved_itinerary(
    user_id: str, data: SavedItineraryCreate
) -> SavedItineraryResponse:
    """Create a new saved itinerary for the user."""
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]

    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "user_id": ObjectId(user_id),
        "structured_itinerary": data.structured_itinerary,
        "trip_meta": data.trip_meta,
        "created_at": now,
        "updated_at": now,
    }

    result = await coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_response(doc)


async def upsert_saved_itinerary_for_chat(
    user_id: str,
    chat_id: str,
    data: SavedItineraryCreate,
) -> SavedItineraryResponse:
    """Create or replace the saved itinerary for this chat (one row per chat thread).

    Regenerating an itinerary in the same chat updates the same document so
    ``saved_itinerary_id`` stays stable and the list does not accumulate duplicates.
    """
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]

    now = datetime.now(UTC)
    uid = ObjectId(user_id)
    cid = str(chat_id).strip()
    set_doc = {
        "user_id": uid,
        "chat_id": cid,
        "structured_itinerary": data.structured_itinerary,
        "trip_meta": data.trip_meta,
        "updated_at": now,
    }
    update_doc = {
        "$set": set_doc,
        "$setOnInsert": {"created_at": now},
    }
    try:
        updated = await coll.find_one_and_update(
            {"user_id": uid, "chat_id": cid},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        updated = await coll.find_one_and_update(
            {"user_id": uid, "chat_id": cid},
            update_doc,
            upsert=False,
            return_document=ReturnDocument.AFTER,
        )
    if updated is None:
        raise RuntimeError("upsert_saved_itinerary_for_chat returned no document")
    return _doc_to_response(dict(updated))


async def get_saved_itineraries_for_user(
    user_id: str,
) -> list[SavedItineraryResponse]:
    """Get saved itineraries for a user, newest first (see ``SAVED_ITINERARIES_LIST_LIMIT``)."""
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]

    cursor = coll.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
    docs = await cursor.to_list(length=SAVED_ITINERARIES_LIST_LIMIT)

    responses = [_doc_to_response(dict(d)) for d in docs]
    ids = [r.id for r in responses]
    linked_map = await fetch_linked_bookings_for_itinerary_ids(user_id, ids)
    return [
        r.model_copy(update={"linked_bookings": linked_map.get(r.id, LinkedBookings())})
        for r in responses
    ]


async def get_saved_itinerary_by_id(
    itinerary_id: str, user_id: str
) -> SavedItineraryResponse | None:
    """Get a saved itinerary by ID. Must belong to user."""
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]

    try:
        oid = ObjectId(itinerary_id)
    except InvalidId:
        return None

    raw = await coll.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if not raw:
        return None

    base = _doc_to_response(dict(raw))
    linked_map = await fetch_linked_bookings_for_itinerary_ids(user_id, [itinerary_id])
    return base.model_copy(
        update={"linked_bookings": linked_map.get(itinerary_id, LinkedBookings())}
    )


async def delete_saved_itinerary(itinerary_id: str, user_id: str) -> bool:
    """Delete a saved itinerary. Physically removes the document."""
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]

    try:
        oid = ObjectId(itinerary_id)
    except InvalidId:
        return False

    result = await coll.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
    return result.deleted_count > 0


async def ensure_saved_itinerary_owned_by_user(
    user_id: str, itinerary_id: str | None
) -> ObjectId | None:
    """Return ObjectId if itinerary exists and belongs to user; else None.

    Invalid ObjectId format or missing document yields None (no exception).
    """
    if not itinerary_id or not str(itinerary_id).strip():
        return None
    try:
        oid = ObjectId(str(itinerary_id).strip())
    except InvalidId:
        logger.warning("Invalid saved_itinerary_id format: %s", itinerary_id)
        return None
    db = await get_database()
    coll = db[SAVED_ITINERARIES_COLLECTION]
    doc = await coll.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if not doc:
        logger.warning(
            "saved_itinerary_id not found or not owned by user (id=%s)", itinerary_id
        )
        return None
    return oid
