"""User preferences repository."""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database.constants import USER_PREFERENCES_COLLECTION
from app.database.dependencies import get_database

from .schemas import (
    FlightsPreferences,
    HotelsPreferences,
    TravelStylePreferences,
    UserPreferencesResponse,
)


def _default_preferences_doc() -> dict[str, Any]:
    """Return empty preferences document structure."""
    return {
        "preference_chips": [],
        "travel_style": {
            "travel_pace": None,
            "budget_mindset": None,
            "accommodation": None,
            "activity_density": None,
            "primary_goals": [],
            "getting_around": [],
        },
        "flights": {
            "seat_preference": None,
            "max_stops": None,
            "preferred_airlines": [],
            "departure_window": ["00:00", "23:59"],
        },
        "hotels": {
            "bed_type": None,
            "room_type": None,
            "amenities": [],
            "hotel_style": [],
            "location_preference": [],
            "cancellation": [],
        },
    }


def _normalize_preferred_airlines(raw: list[Any] | None) -> list[str]:
    """Flatten nested lists and extract strings. Handles legacy [['British Airways']]."""
    if not raw:
        return []
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, str) and sub:
                    result.append(sub)
    return result


def _doc_to_response(
    doc: dict[str, Any], *, document_exists: bool = True
) -> UserPreferencesResponse:
    """Convert DB document to UserPreferencesResponse."""
    ts = doc.get("travel_style") or {}
    fl = doc.get("flights") or {}
    ho = doc.get("hotels") or {}

    return UserPreferencesResponse(
        document_exists=document_exists,
        preference_chips=doc.get("preference_chips") or [],
        travel_style=TravelStylePreferences(
            travel_pace=ts.get("travel_pace"),
            budget_mindset=ts.get("budget_mindset"),
            accommodation=ts.get("accommodation"),
            activity_density=ts.get("activity_density"),
            primary_goals=ts.get("primary_goals") or [],
            getting_around=ts.get("getting_around") or [],
        ),
        flights=FlightsPreferences(
            seat_preference=fl.get("seat_preference"),
            max_stops=fl.get("max_stops"),
            preferred_airlines=_normalize_preferred_airlines(
                fl.get("preferred_airlines")
            ),
            departure_window=fl.get("departure_window") or ["00:00", "23:59"],
        ),
        hotels=HotelsPreferences(
            bed_type=ho.get("bed_type"),
            room_type=ho.get("room_type"),
            amenities=ho.get("amenities") or [],
            hotel_style=ho.get("hotel_style") or [],
            location_preference=ho.get("location_preference") or [],
            cancellation=ho.get("cancellation") or [],
        ),
    )


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Merge update into base. Update values override; lists are replaced.
    None values are applied to allow clients to explicitly clear fields."""
    result = dict(base)
    for key, value in update.items():
        if (
            isinstance(value, dict)
            and isinstance(result.get(key), dict)
            and value is not None
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


async def get_preferences(user_id: str) -> UserPreferencesResponse:
    """Get preferences for user. Returns defaults if none exist."""
    db = await get_database()
    coll = db[USER_PREFERENCES_COLLECTION]

    doc = await coll.find_one({"user_id": ObjectId(user_id)})
    if not doc:
        return _doc_to_response(_default_preferences_doc(), document_exists=False)

    d: dict[str, Any] = dict(doc)
    d["travel_style"] = dict(doc.get("travel_style") or {})
    d["flights"] = dict(doc.get("flights") or {})
    d["hotels"] = dict(doc.get("hotels") or {})
    return _doc_to_response(d, document_exists=True)


async def upsert_preferences(
    user_id: str, update_data: dict[str, Any]
) -> UserPreferencesResponse:
    """Upsert preferences (partial update). Creates document if missing."""
    db = await get_database()
    coll = db[USER_PREFERENCES_COLLECTION]

    now = datetime.now(UTC)
    oid = ObjectId(user_id)

    existing = await coll.find_one({"user_id": oid})
    base: dict[str, Any] = dict(_default_preferences_doc())
    if existing:
        base["preference_chips"] = list(existing.get("preference_chips") or [])
        base["travel_style"] = dict(existing.get("travel_style") or {})
        base["flights"] = dict(existing.get("flights") or {})
        base["hotels"] = dict(existing.get("hotels") or {})

    merged = _deep_merge(base, update_data)

    doc: dict[str, Any] = {
        "user_id": oid,
        "preference_chips": merged["preference_chips"],
        "travel_style": merged["travel_style"],
        "flights": merged["flights"],
        "hotels": merged["hotels"],
        "updated_at": now,
    }
    if not existing:
        doc["created_at"] = now

    await coll.update_one(
        {"user_id": oid},
        {"$set": doc},
        upsert=True,
    )

    return _doc_to_response(doc, document_exists=True)
