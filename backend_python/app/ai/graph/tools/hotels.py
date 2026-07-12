"""Hotel search tool for LangGraph hotel agent.

This tool wraps the FlightLogic Hotel API to search for available hotels.
"""

import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from app.ai.hotel_scoring import sort_hotels_by_best_value
from app.ai.utils.error_message_generator import (
    detect_error_type,
    generate_error_message,
)
from app.domains.hotel.pricing import (
    HOTELS_DISCOUNT_PERCENTAGE,
    apply_platform_fee,
)
from app.domains.user_preferences import get_preferences
from app.shared.geo import haversine_km
from app.shared.geocoding import GeocodingService

logger = logging.getLogger(__name__)

# Per issue #1034: send the full best-value-sorted hotel list to the frontend.
# Frontend handles its own paging/filtering UI. No truncation at the tool layer.

MILES_TO_KM = 1.60934

# Default radius (km) for proximity fallback when locality name doesn't match
PROXIMITY_FALLBACK_RADIUS_KM = 3.0


async def _proximity_filter(
    hotels: list[dict[str, Any]],
    locality: str,
    city_name: str,
    radius_km: float = PROXIMITY_FALLBACK_RADIUS_KM,
) -> list[dict[str, Any]]:
    """Geocode a locality/landmark and return hotels within *radius_km*.

    Falls back gracefully: returns an empty list if geocoding fails or
    no hotels have coordinates.
    """
    try:
        geo = GeocodingService()
        results = await geo.geocode_city(f"{locality}, {city_name}")
        if not results:
            return []

        target_lat, target_lng = results[0].lat, results[0].lng
        nearby: list[dict[str, Any]] = []
        for h in hotels:
            h_lat = h.get("latitude")
            h_lng = h.get("longitude")
            if h_lat is None or h_lng is None:
                continue
            try:
                dist = haversine_km(target_lat, target_lng, float(h_lat), float(h_lng))
            except (TypeError, ValueError):
                continue
            if dist <= radius_km:
                nearby.append(h)
        return nearby
    except Exception:
        logger.warning(
            "Proximity fallback failed for '%s, %s'", locality, city_name, exc_info=True
        )
        return []


class HotelSearchInput(BaseModel):
    """Input schema for hotel search."""

    city_name: str = Field(description="City name (e.g., 'Paris')")
    country_name: str = Field(description="Country name (e.g., 'France')")
    checkin: str = Field(description="Check-in date in YYYY-MM-DD format")
    checkout: str = Field(description="Check-out date in YYYY-MM-DD format")
    rooms: int = Field(default=1, ge=1, le=5, description="Number of rooms (1-5)")
    adults: int = Field(
        ge=1,
        le=9,
        description="Number of adults per room (REQUIRED — must be explicitly stated by user, never assume 1)",
    )
    children: int = Field(default=0, ge=0, description="Number of children per room")
    # --- Post-filters (applied after API results, not supported at API level) ---
    price_min: float | None = Field(
        default=None,
        gt=0,  # gt=0: price must be positive if provided (0 is meaningless)
        description="Minimum hotel price per night. E.g. 'hotels over £50/night' → price_min=50.",
    )
    price_max: float | None = Field(
        default=None,
        gt=0,  # gt=0: price must be positive if provided (0 is meaningless)
        description="Maximum hotel price per night. E.g. 'hotels under £150' → price_max=150.",
    )
    min_rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Minimum star rating (1-5). E.g. '5-star hotels' → min_rating=5, '4+ star' → min_rating=4.",
    )
    property_types: list[str] | None = Field(
        default=None,
        description=(
            "Property type(s) to include. E.g. 'hotels only' → ['Hotel'], 'resorts' → ['Resort']. "
            "Common values: Hotel, Resort, Apartment, Hostel, Guesthouse."
        ),
    )
    refundable_only: bool | None = Field(
        default=None,
        description="If True, only show refundable hotels. E.g. 'refundable hotels only' → refundable_only=True.",
    )
    required_facilities: list[str] | None = Field(
        default=None,
        description=(
            "Facilities the hotel must have (ALL required). "
            "E.g. 'hotels with pool and gym' → ['pool', 'gym']. "
            "Uses case-insensitive substring matching against facility names."
        ),
    )
    max_distance_km: float | None = Field(
        default=None,
        gt=0,  # gt=0: distance must be positive if provided (0 is meaningless)
        description="Maximum distance from city centre in km. E.g. 'within 2km of centre' → max_distance_km=2.0.",
    )
    locality: str | None = Field(
        default=None,
        description=(
            "Neighbourhood or district to filter by. "
            "E.g. 'hotels in Montmartre' → locality='Montmartre', 'Waikiki area' → locality='Waikiki'. "
            "Use ONLY for neighbourhood/district names. Do NOT use for famous landmarks or attractions "
            "(Times Square, Eiffel Tower, Colosseum, etc.) — use nearby_lat/nearby_lng for those instead."
        ),
    )
    nearby_lat: float | None = Field(
        default=None,
        description=(
            "Latitude of a specific destination for proximity sorting. "
            "Use the lat returned by resolve_city when the user asked for a specific "
            "place/landmark/attraction rather than a plain city. "
            "E.g. user says 'Walt Disney World' → resolve_city returns city='Bay Lake' "
            "and lat/lng of Disney World → pass lat here so results are sorted nearest to it."
        ),
    )
    nearby_lng: float | None = Field(
        default=None,
        description=(
            "Longitude of the specific destination (always pair with nearby_lat)."
        ),
    )


# --- Output validation ---
REQUIRED_HOTEL_FIELDS = ("hotel_name", "total_price", "hotel_rating", "address")


def _validate_hotel_results(
    hotels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and filter hotel results for data integrity.

    Removes hotels with:
    - Price <= 0
    - Missing required fields (hotel_name, total_price, hotel_rating, address)
    """
    valid: list[dict[str, Any]] = []

    for hotel in hotels:
        # Check required fields
        if any(hotel.get(f) is None for f in REQUIRED_HOTEL_FIELDS):
            logger.warning(
                f"Hotel {hotel.get('hotel_name', '?')} missing required fields, skipping"
            )
            continue

        # Validate price > 0
        price = hotel.get("total_price", 0)
        try:
            if float(price) <= 0:
                logger.warning(
                    f"Hotel {hotel.get('hotel_name', '?')} has invalid price {price}, skipping"
                )
                continue
        except (TypeError, ValueError):
            logger.warning(
                f"Hotel {hotel.get('hotel_name', '?')} has non-numeric price {price}, skipping"
            )
            continue

        valid.append(hotel)

    if len(valid) < len(hotels):
        logger.info(
            f"Hotel validation: {len(hotels)} → {len(valid)} "
            f"({len(hotels) - len(valid)} filtered out)"
        )

    return valid


def _build_hotel_response(
    hotels: list[dict[str, Any]],
    session_id: str,
    checkin_date: date,
    checkout_date: date,
    *,
    search_params: dict[str, Any] | None = None,
    user_preferences: Any = None,
    travel_style: Any = None,
) -> dict[str, Any]:
    """Build the full unsplit hotel-search success response.

    Returns a single dict carrying ``status / session_id / summary / hotels /
    search_params / instruction``. The public ``search_hotels`` ``@tool`` wraps
    this via ``_split_hotel_search_result`` into a ``(content, artifact)`` tuple
    so the LLM only sees ``status + summary + instruction`` and the heavy
    ``hotels`` list rides on the artifact (#1034). Direct callers (itinerary
    orchestrator, n8n capabilities API) call this helper through
    ``_do_hotel_search`` to get the full dict back without losing the heavy
    payload.

    ``search_params`` (#1038) is echoed on the response so the FE can hydrate
    its hotel-search-form chips without reconstructing them — mirrors the
    flights side.
    """
    sorted_hotels = sort_hotels_by_best_value(hotels, user_preferences, travel_style)

    prices = [float(h.get("total_price", 0) or 0) for h in hotels]
    nights = (checkout_date - checkin_date).days
    summary = {
        "total_found": len(sorted_hotels),
        "nights": nights,
        "price_range": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "currency": hotels[0].get("currency", "GBP") if hotels else "GBP",
        },
    }

    # Echo the city + any applied filter criteria in the LLM-facing
    # instruction so the response includes them. Without this hint the
    # agent often produces a generic "Found N hotels" reply that's
    # ambiguous to the user and brittle to test against (#1105 follow-up).
    sp = search_params or {}
    city_for_echo = sp.get("destination_city") or ""
    filter_hints: list[str] = []
    if sp.get("min_rating"):
        filter_hints.append(f"{sp['min_rating']}-star")
    if sp.get("refundable_only"):
        filter_hints.append("refundable")
    if sp.get("property_types"):
        filter_hints.append(", ".join(sp["property_types"]))
    if sp.get("price_max"):
        filter_hints.append(f"under {sp['price_max']}")
    if sp.get("locality"):
        filter_hints.append(f"in {sp['locality']}")
    filter_phrase = f" matching {', '.join(filter_hints)}" if filter_hints else ""
    city_phrase = f" in {city_for_echo}" if city_for_echo else ""

    return {
        "status": "success",
        "session_id": session_id,
        "summary": summary,
        "search_params": sp,
        "hotels": sorted_hotels,
        "instruction": (
            f"Tell the user we found {len(sorted_hotels)} hotels"
            f"{city_phrase}{filter_phrase}. "
            f"They're displayed above the chat. Booking is initiated by clicking "
            f"the Book button on a card. Do NOT list hotels in the chat reply. "
            f"Include the city name{' and filter criteria' if filter_hints else ''} "
            f"in your reply text so the user can see what was searched."
        ),
    }


def _split_hotel_search_result(
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Split a hotel-search result dict into a (content, artifact) tuple.

    Mirrors ``flights._split_search_result``. Error and no-results responses
    pass through with ``artifact=None`` (nothing heavy to hide). For
    ``status == "success"`` the ``hotels`` array, ``session_id`` and full
    ``summary`` move to the artifact, while ``content`` keeps a slim
    ``status + summary + instruction`` for the LLM.
    """
    if result.get("status") != "success":
        return result, None

    summary = result.get("summary")
    artifact = {
        "session_id": result.get("session_id"),
        "summary": summary,
        "search_params": result.get("search_params") or {},
        "hotels": result.get("hotels", []),
    }
    content = {
        "status": "success",
        "summary": summary,
        "instruction": result.get("instruction"),
    }
    return content, artifact


async def _do_hotel_search(
    city_name: str,
    country_name: str,
    checkin: str,
    checkout: str,
    adults: int,
    rooms: int = 1,
    children: int = 0,
    # Post-filters (applied after API results, not supported at API level)
    price_min: float | None = None,
    price_max: float | None = None,
    min_rating: int | None = None,
    property_types: list[str] | None = None,
    refundable_only: bool | None = None,
    required_facilities: list[str] | None = None,
    max_distance_km: float | None = None,
    locality: str | None = None,
    nearby_lat: float | None = None,
    nearby_lng: float | None = None,
    # Injected by LangGraph — not provided by the LLM
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Internal hotel-search implementation returning a full dict.

    The public ``search_hotels`` ``@tool`` wraps this and splits the dict into a
    ``(content, artifact)`` tuple so the LLM never sees the heavy hotel list
    (#1034). Direct internal callers — itinerary orchestrator side-search,
    n8n capabilities API — call this helper directly to get the full dict
    back.
    """
    from datetime import datetime

    from app.domains.common import utc_date
    from app.domains.hotel.constants import DEFAULT_CURRENCY
    from app.domains.hotel.schemas import (
        HotelSearchRequest,
        NearbyLocation,
        OccupancyRoom,
    )

    # Validate dates
    try:
        checkin_date = datetime.strptime(checkin, "%Y-%m-%d").date()
        checkout_date = datetime.strptime(checkout, "%Y-%m-%d").date()
    except ValueError:
        return {
            "status": "error",
            "error": f"Invalid date format. Use YYYY-MM-DD. Got checkin={checkin}, checkout={checkout}",
            "instruction": "Ask the user to provide dates in YYYY-MM-DD format.",
        }

    if checkout_date <= checkin_date:
        return {
            "status": "error",
            "error": "Check-out date must be after check-in date.",
            "instruction": "Ask the user to correct the check-out date so it's after check-in.",
        }

    # Validate dates are not in the past
    today = utc_date()
    if checkin_date < today:
        return {
            "status": "error",
            "error": f"Check-in date {checkin} is in the past. Today is {today.isoformat()}. "
            f"Use the parse_dates tool to get correct dates, or ask the user to clarify.",
            "instruction": "Ask the user for a future check-in date.",
        }
    if checkout_date < today:
        return {
            "status": "error",
            "error": f"Check-out date {checkout} is in the past. Today is {today.isoformat()}.",
            "instruction": "Ask the user for a future check-out date.",
        }

    # Fetch user preferences for preference-aware best_value scoring
    user_preferences = None
    travel_style_prefs = None
    user_id = (config or {}).get("configurable", {}).get("user_id") if config else None
    if user_id:
        try:
            prefs_response = await get_preferences(user_id)
            user_preferences = prefs_response.hotels
            travel_style_prefs = prefs_response.travel_style
        except Exception as pref_err:
            logger.warning("Could not fetch user preferences for scoring: %s", pref_err)

    # Build occupancy for each room
    occupancy = [
        OccupancyRoom(
            room_no=i + 1,
            adult=adults,
            child=children,
            child_age=[8] * children if children > 0 else [],
        )
        for i in range(rooms)
    ]

    # Build nearby_location for proximity sorting when coordinates provided
    nearby_location = None
    if nearby_lat is not None and nearby_lng is not None:
        nearby_location = NearbyLocation(lat=nearby_lat, lng=nearby_lng)

    # Build search request (explicit optional fields for pydantic-mypy init_typed)
    request = HotelSearchRequest(
        user_id=None,
        user_password=None,
        access=None,
        ip_address=None,
        city_name=city_name,
        country_name=country_name,
        latitude=None,
        longitude=None,
        hotel_codes=None,
        radius=None,
        checkin=checkin,
        checkout=checkout,
        occupancy=occupancy,
        requiredCurrency=DEFAULT_CURRENCY,
        resultsPerPage=None,
        requiredLanguage=None,
        nationality=None,
        nearby_location=nearby_location,
    )

    try:
        from integrations.flightlogic.client import FlightLogicClient

        client = FlightLogicClient()
        response = await client.search_hotels(request)

        # Note: HotelSearchResponse doesn't have an errors field like FlightSearchResponse
        # Errors are raised as exceptions (HotelSearchError) instead
        # So we don't need to check response.errors here

        # Extract hotel options (no cap; use all results from API)
        hotels = []
        for hotel in response.itineraries:
            hotel_info = _extract_hotel_info(hotel)
            if hotel_info:
                hotels.append(hotel_info)

        # Validate hotel results for data integrity
        hotels = _validate_hotel_results(hotels)

        if not hotels:
            return {
                "status": "no_results",
                "message": f"No hotels found in {city_name}, {country_name} for {checkin} to {checkout}.",
                "suggestion": "Try different dates or a nearby city.",
                "instruction": "Inform the user no hotels were found and suggest alternatives.",
            }

        # Apply post-filters (price, rating, property type, fare type, facilities, distance, locality)
        unfiltered_hotels = hotels
        hotels = _apply_hotel_post_filters(
            hotels,
            price_min=price_min,
            price_max=price_max,
            min_rating=min_rating,
            property_types=property_types,
            refundable_only=refundable_only,
            required_facilities=required_facilities,
            max_distance_km=max_distance_km,
            locality=locality,
        )

        if not hotels and locality:
            # Locality name didn't match — try geocode proximity fallback.
            # Re-apply all filters EXCEPT locality so we have a candidate set.
            hotels_without_locality = _apply_hotel_post_filters(
                unfiltered_hotels,
                price_min=price_min,
                price_max=price_max,
                min_rating=min_rating,
                property_types=property_types,
                refundable_only=refundable_only,
                required_facilities=required_facilities,
                max_distance_km=max_distance_km,
                locality=None,
            )
            if hotels_without_locality:
                nearby = await _proximity_filter(
                    hotels_without_locality,
                    locality,
                    city_name,
                )
                if nearby:
                    logger.info(
                        "Locality '%s' matched %d hotels via proximity fallback",
                        locality,
                        len(nearby),
                    )
                    hotels = nearby

        if not hotels:
            # Build suggestions for ALL active filters so combined-filter
            # requests get comprehensive feedback (not just the first match).
            suggestion_parts: list[str] = []

            if required_facilities:
                # Count how many hotels offer each facility
                facility_counts: dict[str, int] = {}
                for h in unfiltered_hotels:
                    for f in h.get("facilities") or []:
                        facility_counts[f] = facility_counts.get(f, 0) + 1
                if facility_counts:
                    # Show top 10 most common facilities (most useful to the user)
                    top_facilities = sorted(
                        facility_counts.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    facilities_list = ", ".join(f for f, _ in top_facilities)
                    suggestion_parts.append(
                        f"No hotels offer {', '.join(required_facilities)} in this area. "
                        f"Most common facilities across hotels: {facilities_list}."
                    )

            if property_types:
                available_types: set[str] = {
                    str(h["property_type"])
                    for h in unfiltered_hotels
                    if h.get("property_type")
                }
                if available_types:
                    types_list = ", ".join(sorted(available_types))
                    suggestion_parts.append(
                        f"No {', '.join(property_types)} found in this area. "
                        f"Available property types: {types_list}."
                    )

            if price_min is not None or price_max is not None:
                prices = [
                    float(h["per_night_price"])
                    for h in unfiltered_hotels
                    if h.get("per_night_price") is not None
                ]
                if prices:
                    lo, hi = min(prices), max(prices)
                    currency = next(
                        (
                            h.get("currency", "GBP")
                            for h in unfiltered_hotels
                            if h.get("currency")
                        ),
                        "GBP",
                    )
                    suggestion_parts.append(
                        f"Hotels in this area range from {lo:.0f} to {hi:.0f} {currency} per night."
                    )

            if min_rating is not None:
                ratings = sorted(
                    {
                        int(h["hotel_rating"])
                        for h in unfiltered_hotels
                        if h.get("hotel_rating")
                    },
                    reverse=True,
                )
                if ratings:
                    ratings_str = ", ".join(f"{r}★" for r in ratings)
                    suggestion_parts.append(
                        f"Available star ratings in this area: {ratings_str}."
                    )

            if max_distance_km is not None:

                def _dist_km(h: dict[str, Any]) -> float | None:
                    val = h.get("distance_value")
                    if val is None:
                        return None
                    unit = (h.get("distance_unit") or "km").lower()
                    return float(val) * MILES_TO_KM if "mile" in unit else float(val)

                distances = [
                    d for d in (_dist_km(h) for h in unfiltered_hotels) if d is not None
                ]
                if distances:
                    nearest = min(distances)
                    suggestion_parts.append(
                        f"No hotels within {max_distance_km:.0f}km of the centre. "
                        f"The nearest hotel is {nearest:.1f}km away."
                    )

            if locality:
                available_localities: set[str] = {
                    str(h["locality"]) for h in unfiltered_hotels if h.get("locality")
                }
                if available_localities:
                    # Show at most 5 neighbourhoods to avoid a raw text dump
                    top_localities = sorted(available_localities)[:5]
                    localities_str = ", ".join(top_localities)
                    more = (
                        f" (and {len(available_localities) - 5} more)"
                        if len(available_localities) > 5
                        else ""
                    )
                    suggestion_parts.append(
                        f"No hotels found in that area. "
                        f"Try one of these neighbourhoods: {localities_str}{more}."
                    )
                else:
                    suggestion_parts.append(
                        "No hotels found in that area. "
                        "Try searching without a neighbourhood filter."
                    )

            suggestion = (
                " ".join(suggestion_parts)
                if suggestion_parts
                else "Try relaxing your filters (e.g. higher price limit, lower star rating)."
            )
            suggestion += " Would you like to adjust your filters?"

            return {
                "status": "no_results",
                "message": f"No hotels found matching your filters in {city_name}, {country_name}.",
                "suggestion": suggestion,
                "instruction": "Inform the user that hotels exist but none match their filters, and suggest adjustments.",
            }

        # #1038: echo the search params the user/orchestrator gave us so the
        # FE recommendations slice can hydrate its header chips (destination,
        # dates, room/passenger count) without reconstructing them.
        echoed_search_params = {
            "destination_city": city_name,
            "country": country_name,
            "check_in_date": checkin,
            "check_out_date": checkout,
            "rooms": rooms,
            "adults": adults,
            "children": children,
        }
        return _build_hotel_response(
            hotels,
            response.session_id,
            checkin_date,
            checkout_date,
            search_params=echoed_search_params,
            user_preferences=user_preferences,
            travel_style=travel_style_prefs,
        )

    except Exception as e:
        error_type, error_message, error_code, status_code = detect_error_type(e)

        # Timezone resilience: if the API rejects a same-day checkin as "in the past",
        # it's likely because the destination timezone is ahead of UTC.
        # Auto-retry once with dates bumped forward by 1 day.
        _past_date_keywords = ("earlier than today", "in the past", "past date")
        is_past_date_error = any(
            kw in error_message.lower() for kw in _past_date_keywords
        )

        if is_past_date_error and checkin_date == today:
            new_checkin = checkin_date + timedelta(days=1)
            new_checkout = checkout_date + timedelta(days=1)
            logger.warning(
                f"Same-day checkin {checkin} rejected by API (likely destination timezone ahead of UTC). "
                f"Retrying with checkin={new_checkin.isoformat()}, checkout={new_checkout.isoformat()}"
            )
            try:
                retry_request = HotelSearchRequest(
                    user_id=None,
                    user_password=None,
                    access=None,
                    ip_address=None,
                    city_name=city_name,
                    country_name=country_name,
                    latitude=None,
                    longitude=None,
                    hotel_codes=None,
                    radius=None,
                    checkin=new_checkin.isoformat(),
                    checkout=new_checkout.isoformat(),
                    occupancy=occupancy,
                    requiredCurrency=DEFAULT_CURRENCY,
                    resultsPerPage=None,
                    requiredLanguage=None,
                    nationality=None,
                    nearby_location=nearby_location,
                )
                retry_response = await client.search_hotels(retry_request)

                hotels = []
                for hotel in retry_response.itineraries:
                    hotel_info = _extract_hotel_info(hotel)
                    if hotel_info:
                        hotels.append(hotel_info)
                hotels = _validate_hotel_results(hotels)

                if not hotels:
                    return {
                        "status": "no_results",
                        "message": f"No hotels found in {city_name}, {country_name} for {new_checkin.isoformat()} to {new_checkout.isoformat()}.",
                        "suggestion": "Try different dates or a nearby city.",
                        "instruction": "Inform the user no hotels were found and suggest alternatives.",
                    }

                # Apply same post-filters as original request
                hotels = _apply_hotel_post_filters(
                    hotels,
                    price_min=price_min,
                    price_max=price_max,
                    min_rating=min_rating,
                    property_types=property_types,
                    refundable_only=refundable_only,
                    required_facilities=required_facilities,
                    max_distance_km=max_distance_km,
                    locality=locality,
                )

                if not hotels:
                    return {
                        "status": "no_results",
                        "message": f"No hotels found matching your filters in {city_name}, {country_name}.",
                        "suggestion": "Try relaxing your filters.",
                        "instruction": "Inform the user that hotels exist but none match their filters.",
                    }

                # #1038: echo the BUMPED dates so the FE sees what was
                # actually searched (not the original same-day request).
                retry_search_params = {
                    "destination_city": city_name,
                    "country": country_name,
                    "check_in_date": new_checkin.isoformat(),
                    "check_out_date": new_checkout.isoformat(),
                    "rooms": rooms,
                    "adults": adults,
                    "children": children,
                }
                return _build_hotel_response(
                    hotels,
                    retry_response.session_id,
                    new_checkin,
                    new_checkout,
                    search_params=retry_search_params,
                    user_preferences=user_preferences,
                    travel_style=travel_style_prefs,
                )
            except Exception as retry_error:
                logger.warning(f"Same-day retry also failed: {retry_error}")
                # Fall through to normal error handling below

        logger.exception(f"search_hotels error: {e}")

        # AI-CHAT-010: classify once and reuse for both the fallback user
        # message and the error_class field downstream consumers read.
        from app.ai.errors import classify_exception

        classified = classify_exception(e)

        # Generate empathetic error message using LLM; fall back to the
        # classifier's user message if the LLM call itself fails.
        try:
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
                error_code=error_code,
                status_code=status_code,
                additional_context={
                    "city_name": city_name,
                    "country_name": country_name,
                    "checkin": checkin,
                    "checkout": checkout,
                },
            )
        except Exception as llm_error:
            logger.warning(
                f"Failed to generate LLM error message, using fallback: {llm_error}"
            )
            user_friendly_message = classified.user_message

        return {
            "status": "error",
            "error": error_message,  # Technical error for logging
            "error_type": error_type,
            "error_class": classified.cls.value,
            "message": user_friendly_message,  # LLM-generated user-friendly message
            "instruction": "Inform the user about the error and suggest next steps.",
        }


def _extract_hotel_info(hotel: Any) -> dict[str, Any] | None:
    """Extract hotel information from a HotelSearchResult.

    Args:
        hotel: HotelSearchResult domain model

    Returns:
        Dict with hotel details for frontend, or None if extraction fails
    """
    try:
        # Original price from API (before platform fee)
        original_total = (
            float(hotel.total) if isinstance(hotel.total, Decimal) else hotel.total
        )
        nights = hotel.get_nights() or 1
        # Apply platform fee to get total price (what customer pays), matching flight-booker/chat behavior
        price_with_fee = float(apply_platform_fee(original_total))
        per_night_with_fee = (
            round(price_with_fee / nights, 2) if nights > 0 else price_with_fee
        )

        return {
            # Identification (needed for room rates API)
            "hotel_id": hotel.hotel_id,
            "token_id": hotel.token_id,
            "product_id": hotel.product_id,
            # Display info
            "hotel_name": hotel.hotel_name,
            "city": hotel.city or "",
            "country": hotel.country,
            "address": hotel.address or "",
            "locality": hotel.locality,
            # Rating
            "hotel_rating": hotel.hotel_rating,
            "trip_advisor_rating": hotel.trip_advisor_rating,
            "trip_advisor_reviews": hotel.trip_advisor_review,
            # Pricing (with platform fee for display, same as flights in chat)
            "total_price": round(price_with_fee, 2),
            "per_night_price": per_night_with_fee,
            "currency": hotel.currency,
            "fare_type": hotel.fare_type,
            "nights": nights,
            # Price breakdown (for modal display, like flights)
            "original_total_fare": round(original_total, 2),
            "platform_fee_percentage": float(HOTELS_DISCOUNT_PERCENTAGE),
            # Amenities
            "facilities": hotel.facilities[:10] if hotel.facilities else [],
            "property_type": hotel.property_type,
            # Image
            "thumbnail_url": hotel.thumbnail_url,
            # Location (decimal strings from API; used by /hotels/recommendations map markers)
            "latitude": hotel.latitude,
            "longitude": hotel.longitude,
            "distance_value": hotel.distance_value,
            "distance_unit": hotel.distance_unit,
            # Nearby destination proximity (set when nearby_location was provided)
            "nearby_distance_km": hotel.nearby_distance_km,
        }

    except Exception:
        return None


def _apply_hotel_post_filters(
    hotels: list[dict[str, Any]],
    price_min: float | None = None,
    price_max: float | None = None,
    min_rating: int | None = None,
    property_types: list[str] | None = None,
    refundable_only: bool | None = None,
    required_facilities: list[str] | None = None,
    max_distance_km: float | None = None,
    locality: str | None = None,
) -> list[dict[str, Any]]:
    """Apply post-API filters to hotel results.

    All hotel filters are post-filters — FlightLogic Hotel API does not support
    filter params. Applied once after the API returns; no double API call.

    Hotels with None/missing values for a filtered field are EXCLUDED
    (a hotel without a price shouldn't match "under £150").
    """
    filtered = hotels

    # W5: Swap if caller accidentally reversed min/max
    if price_min is not None and price_max is not None and price_min > price_max:
        price_min, price_max = price_max, price_min

    if price_min is not None:
        filtered = [
            h
            for h in filtered
            if h.get("per_night_price") is not None
            and float(h["per_night_price"]) >= price_min
        ]

    if price_max is not None:
        filtered = [
            h
            for h in filtered
            if h.get("per_night_price") is not None
            and float(h["per_night_price"]) <= price_max
        ]

    if min_rating is not None:
        filtered = [
            h
            for h in filtered
            if h.get("hotel_rating") is not None
            and int(h["hotel_rating"]) >= min_rating
        ]

    if property_types is not None:
        normalised_types = [pt.lower() for pt in property_types]
        filtered = [
            h
            for h in filtered
            if h.get("property_type") and h["property_type"].lower() in normalised_types
        ]

    if refundable_only:
        filtered = [
            h
            for h in filtered
            if h.get("fare_type") and "non-refundable" not in h["fare_type"].lower()
        ]

    if required_facilities:

        def _norm(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower())

        def has_all_facilities(hotel: dict[str, Any]) -> bool:
            hotel_facilities = [_norm(f) for f in (hotel.get("facilities") or [])]
            return all(
                any(_norm(req) in fac for fac in hotel_facilities)
                for req in required_facilities
            )

        filtered = [h for h in filtered if has_all_facilities(h)]

    if max_distance_km is not None:

        def distance_in_km(hotel: dict[str, Any]) -> float | None:
            val = hotel.get("distance_value")
            if val is None:
                return None
            unit = (hotel.get("distance_unit") or "km").lower()
            return float(val) * MILES_TO_KM if "mile" in unit else float(val)

        filtered = [
            h
            for h in filtered
            if (d := distance_in_km(h)) is not None and d <= max_distance_km
        ]

    if locality is not None and locality.strip():
        locality_lower = locality.strip().lower()
        filtered = [
            h
            for h in filtered
            if h.get("locality") is not None and locality_lower in h["locality"].lower()
        ]

    return filtered


# ---------------------------------------------------------------------------
# Public @tool wrapper — splits the helper's full dict into (content, artifact)
# so the LLM never sees the heavy ``hotels`` list (#1034).
# ---------------------------------------------------------------------------


@tool(
    "search_hotels",
    args_schema=HotelSearchInput,
    response_format="content_and_artifact",
)
async def search_hotels(
    city_name: str,
    country_name: str,
    checkin: str,
    checkout: str,
    adults: int,
    rooms: int = 1,
    children: int = 0,
    price_min: float | None = None,
    price_max: float | None = None,
    min_rating: int | None = None,
    property_types: list[str] | None = None,
    refundable_only: bool | None = None,
    required_facilities: list[str] | None = None,
    max_distance_km: float | None = None,
    locality: str | None = None,
    nearby_lat: float | None = None,
    nearby_lng: float | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # type: ignore[assignment]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Search for available hotels.

    Use this tool after you have resolved the city to a city/country pair
    and parsed the check-in/check-out dates.

    Per issue #1034: returns a ``(content, artifact)`` tuple. The LLM only sees
    the content (summary + instruction). The full best-value-sorted hotel
    list lives on ``ToolMessage.artifact`` and is consumed by the graph
    extractor for the frontend payload — it is NEVER sent to the LLM.
    """
    result = await _do_hotel_search(
        city_name=city_name,
        country_name=country_name,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        rooms=rooms,
        children=children,
        price_min=price_min,
        price_max=price_max,
        min_rating=min_rating,
        property_types=property_types,
        refundable_only=refundable_only,
        required_facilities=required_facilities,
        max_distance_km=max_distance_km,
        locality=locality,
        nearby_lat=nearby_lat,
        nearby_lng=nearby_lng,
        config=config,
    )
    return _split_hotel_search_result(result)


__all__ = ["HotelSearchInput", "_do_hotel_search", "search_hotels"]
