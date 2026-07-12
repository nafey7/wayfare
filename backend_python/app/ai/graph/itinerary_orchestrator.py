"""Orchestrator: fire flight + hotel searches alongside ``generate_itinerary``.

Implements step (2) of the personalized-itinerary flow described in
``docs/PERSONALIZED_ITINERARY_PLAN.md``: while the LLM-driven itinerary agent
runs (~40-50s), this module fires ``_do_flight_search`` and
``_do_hotel_search`` as concurrent tasks so their ~3-6s latency is hidden
inside the LLM budget.

The LLM running ``generate_itinerary`` never sees these payloads — flights
and hotels arrive on the response **side-channel** (top-level ``flights`` /
``hotels`` arrays on the chat response) and as stitched ``kind`` entries on
``itineraryItems``. The artifact contract from #1034 (LLM-blind heavy
payloads) is preserved.

When ``shared_context.trip`` doesn't yet have the fields needed to fire a
search (cold first turn, user typed something ambiguous), the corresponding
side-search is skipped silently and the itinerary still ships.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from app.ai.graph.itinerary_stitcher import stitch_itinerary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Multi-hub result merging (#1152)
# ---------------------------------------------------------------------------


def _build_multistay_chain_result(
    results: list[dict[str, Any] | None],
    hub_list: list[dict[str, str]],
    trip_ctx: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a ``multistay_hotel_search_results`` chain-result payload.

    Produces the ``{ type, data }`` shape consumed by
    ``hydrateMultistayHotelSearchResultsFromPayload`` on the frontend.
    Each hub becomes one leg with its own session_id so the booking flow
    can route to the correct FlightLogic hotel session.
    """
    legs: list[dict[str, Any]] = []
    for idx, (hub, result) in enumerate(zip(hub_list, results, strict=False)):
        if not result or result.get("status") != "success":
            continue
        hotels = result.get("hotels") or []
        prices = []
        for h in hotels:
            p = h.get("per_night_price") or h.get("total_price") or h.get("price") or 0
            with contextlib.suppress(TypeError, ValueError):
                prices.append(float(p))
        currency = next(
            (
                h.get("currency")
                for h in hotels
                if isinstance(h.get("currency"), str) and h["currency"]
            ),
            "USD",
        )
        legs.append(
            {
                "leg_index": idx,
                "destination": hub["city"],
                "destination_iata": hub["iata"],
                "check_in_date": trip_ctx.get("departure_date") or "",
                "check_out_date": trip_ctx.get("return_date") or "",
                "session_id": result.get("session_id") or "",
                "summary": {
                    "total_found": len(hotels),
                    "price_range": {
                        "min": round(min(prices), 2) if prices else 0,
                        "max": round(max(prices), 2) if prices else 0,
                        "currency": currency,
                    },
                },
                "hotels": hotels,
            }
        )
    if not legs:
        return None

    search_params = {
        "check_in_date": trip_ctx.get("departure_date") or "",
        "check_out_date": trip_ctx.get("return_date") or "",
        "adults": trip_ctx.get("adults") or 1,
        "children": trip_ctx.get("children") or 0,
        "rooms": trip_ctx.get("rooms") or 1,
    }
    return {
        "type": "multistay_hotel_search_results",
        "data": {
            "search_params": search_params,
            "multistay_legs": legs,
        },
    }


def _merge_hotel_results(
    results: list[dict[str, Any] | None],
    hub_list: list[dict[str, str]],
    trip_ctx: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Merge hotel results from multiple hub searches into one response.

    Tags each hotel with ``search_city`` / ``hub_iata``. Deduplicates by
    ``hotel_id`` (keeps first occurrence — primary hub takes precedence).
    All hub sessions exposed under ``hub_sessions``.
    """
    all_hotels: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    hub_sessions: dict[str, str] = {}
    primary_result: dict[str, Any] | None = None

    for hub, result in zip(hub_list, results, strict=False):
        if not result or result.get("status") != "success":
            continue
        if primary_result is None:
            primary_result = result
        session = result.get("session_id")
        if session:
            hub_sessions[hub["iata"]] = session
        for hotel in result.get("hotels") or []:
            hotel_id = hotel.get("hotel_id") or hotel.get("id") or hotel.get("name", "")
            if hotel_id and hotel_id in seen_ids:
                continue
            if hotel_id:
                seen_ids.add(hotel_id)
            tagged = dict(hotel)
            tagged.setdefault("search_city", hub["city"])
            tagged.setdefault("hub_iata", hub["iata"])
            all_hotels.append(tagged)

    if not all_hotels:
        return None

    merged = dict(primary_result or {})
    merged["hotels"] = all_hotels
    merged["hub_sessions"] = hub_sessions
    merged["hub_count"] = len(hub_list)
    if trip_ctx is not None:
        merged["multistay_chain_result"] = _build_multistay_chain_result(
            results, hub_list, trip_ctx
        )
    return merged


# Fields we need from shared_context.trip to fire each side-search.
_FLIGHT_REQUIRED = ("origin_iata", "destination_iata", "departure_date")
# Hotel search requires an explicit check-out, so one-way trips (no
# ``return_date`` in trip_ctx) skip the hotel side-search silently. The
# stitcher's "outbound + check-in only" criterion for one-way itineraries
# therefore won't render an inline check-in card today. Follow-up: derive
# ``return_date`` from the itinerary day count when the user gives one-way
# intent + a duration ("5 days in Paris") so the check-in still surfaces.
_HOTEL_REQUIRED = ("destination", "departure_date", "return_date")


def _has_required(trip_ctx: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(trip_ctx.get(k) for k in keys)


async def _safe_flight_search(
    trip_ctx: dict[str, Any], user_id: str
) -> dict[str, Any] | None:
    """Call ``_do_flight_search`` with the trip_ctx fields, return result or None.

    Wraps the helper so a failure on one side doesn't cancel the other
    (doc: "Graceful degradation — FlightLogic outage on one side doesn't
    block the other; itinerary still ships with whatever succeeded").
    """
    try:
        from app.ai.graph.tools.flights import _do_flight_search

        return await _do_flight_search(
            origin=trip_ctx["origin_iata"],
            destination=trip_ctx["destination_iata"],
            departure_date=trip_ctx["departure_date"],
            return_date=trip_ctx.get("return_date"),
            trip_type="round-trip" if trip_ctx.get("return_date") else "one-way",
            adults=trip_ctx.get("adults") or 1,
            children=trip_ctx.get("children") or 0,
            infants=trip_ctx.get("infants") or 0,
            # Trip context already gave us a specific IATA — search that airport
            # (not the whole city), so results match what the day plan implies.
            origin_is_city=False,
            destination_is_city=False,
            cabin_class=trip_ctx.get("cabin_class"),
            config={"configurable": {"user_id": user_id}},
        )
    except Exception:
        logger.exception("itinerary side-search: flight search failed")
        return None


async def _safe_multicity_flight_search(
    hub_list: list[dict[str, str]],
    trip_ctx: dict[str, Any],
    user_id: str,  # noqa: ARG001 — reserved for future per-user config
) -> dict[str, Any] | None:
    """Fire a single multi-city search covering all hubs as legs.

    Calls ``_search_multicity`` with one leg per hub (same origin, different
    destinations, same departure date). The result is the native
    ``multicity_results`` payload the frontend already knows how to render
    as pre-populated legs in the multi-city route modal.
    """
    try:
        from app.ai.graph.tools.flights import _search_multicity

        origin_iata = trip_ctx.get("origin_iata", "")
        departure_date = trip_ctx.get("departure_date", "")
        adults = trip_ctx.get("adults") or 1
        children = trip_ctx.get("children") or 0
        infants = trip_ctx.get("infants") or 0
        cabin_class = trip_ctx.get("cabin_class")

        segments = [
            {
                "origin": origin_iata,
                "destination": hub["iata"],
                "departure_date": departure_date,
            }
            for hub in hub_list
        ]

        result = await _search_multicity(
            segments_input=segments,
            adults=adults,
            children=children,
            infants=infants,
            cabin_class=cabin_class,
        )

        if result.get("status") != "multicity_results":
            logger.warning(
                "itinerary side-search: multicity flight search returned status=%s",
                result.get("status"),
            )
            return None

        legs = result.get("multicity_legs") or []
        logger.info(
            "itinerary side-search: multicity flight search complete — %d legs, "
            "%d total flights",
            len(legs),
            sum(len(leg.get("flights") or []) for leg in legs),
        )

        # Build the chain_result payload in the exact format the frontend
        # expects for multicity_flight_search_results.
        passengers = {
            "adults": adults,
            "children": children,
            "infants": infants,
        }
        chain_result = {
            "type": "multicity_flight_search_results",
            "data": {
                "search_params": {
                    "origin": trip_ctx.get("origin_iata") or "",
                    "departure_date": departure_date,
                    "return_date": trip_ctx.get("return_date"),
                    "journey_type": "Circle",
                    "passengers": passengers,
                    "cabin_class": cabin_class or "Economy",
                },
                "multicity_parallel": True,
                "multicity_legs": legs,
            },
        }

        # Also expose a flat flights list for the Flights tab cache so the
        # user can browse all options while viewing the multi-city modal.
        all_flights: list[dict[str, Any]] = []
        for leg in legs:
            for flight in leg.get("flights") or []:
                tagged = dict(flight)
                tagged.setdefault(
                    "hub_city", leg.get("destination_city") or leg.get("destination")
                )
                tagged.setdefault("hub_iata", leg.get("destination"))
                all_flights.append(tagged)

        primary_session = legs[0].get("session_id") if legs else None
        return {
            "status": "success",
            "flights": all_flights,
            "session_id": primary_session,
            "search_params": result.get("search_params"),
            "multicity_chain_result": chain_result,
            "hub_count": len(hub_list),
        }

    except Exception:
        logger.exception("itinerary side-search: multicity flight search failed")
        return None


async def _safe_hotel_search_multi_hub(
    hub_list: list[dict[str, str]],
    trip_ctx: dict[str, Any],
    user_id: str,
) -> dict[str, Any] | None:
    """Fire one hotel search per hub in parallel, merge results."""
    tasks = [
        _safe_hotel_search(
            {**trip_ctx, "destination_search_city": hub["city"]}, user_id
        )
        for hub in hub_list
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(
        "itinerary side-search: multi-hub hotel search complete — %d/%d hubs returned results",
        sum(1 for r in results if r and r.get("status") == "success"),
        len(hub_list),
    )
    return _merge_hotel_results(list(results), hub_list, trip_ctx)


async def _resolve_destination_for_hotel(
    destination: str,
) -> tuple[str | None, str | None, float | None, float | None]:
    """Geocode ``destination`` once for hotel search.

    Returns ``(city, country_full_name, lat, lng)``. Any value can be
    ``None`` on geocoding failure — caller is expected to fall back.

    Why no country parameter (issue #1076)
    --------------------------------------
    PR #1071 previously passed an ISO-2 country code from the MWGG airport
    resolver into the query (e.g. ``"Barcelona, ES"``) on the theory that
    appending the country would disambiguate the city. Google Geocoding
    interprets the second component positionally as *subdivision or
    country, whichever ranks higher* — and ``ES`` collides with the
    Brazilian state Espírito Santo, so the API returned a Barcelona
    village near Serra, Brazil instead of Barcelona, Spain. FlightLogic
    was then asked for ``Barcelona, Brazil`` hotels and threw
    ``HotelSearchError``.

    Frontend autocomplete and the hotel agent's ``resolve_city`` tool
    both geocode the bare destination without any country hint and rely
    on Google's relevance ranking to pick the right one — which it does
    correctly for major cities. This helper now does the same so all
    three hotel-resolution paths agree.
    """
    if not destination:
        return None, None, None, None
    try:
        from app.shared.geocoding import GeocodingService

        results = await GeocodingService().geocode_city(destination)
        if not results:
            return None, None, None, None
        r = results[0]
        return r.city, r.country, r.lat, r.lng
    except Exception:
        # Don't let geocoding failure block the hotel search — caller's
        # trip_ctx fallback preserves a best-effort attempt.
        logger.warning(
            "Hotel destination geocoding failed for '%s'",
            destination,
            exc_info=True,
        )
        return None, None, None, None


async def _enrich_hotel_images(
    result: dict[str, Any],
    city_name: str,
) -> dict[str, Any]:
    """Resolve Google Places images for hotels missing thumbnail_url in parallel."""
    try:
        from integrations.googleplaces.client import GooglePlacesClient

        hotels: list[dict[str, Any]] = list(result.get("hotels") or [])
        missing = [h for h in hotels if not h.get("thumbnail_url")]
        if not missing:
            return result

        places = GooglePlacesClient()

        async def _resolve(hotel: dict[str, Any]) -> None:
            name = hotel.get("hotel_name") or hotel.get("name") or ""
            if not name:
                return
            try:
                url = await places.resolve_place_image_url(f"{name} {city_name}")
                if url:
                    hotel["thumbnail_url"] = url
            except Exception:
                pass

        await asyncio.gather(*(_resolve(h) for h in missing), return_exceptions=True)
        logger.info(
            "itinerary side-search: enriched %d/%d hotel images for %s",
            sum(1 for h in missing if h.get("thumbnail_url")),
            len(missing),
            city_name,
        )
    except Exception:
        logger.warning(
            "itinerary side-search: hotel image enrichment failed", exc_info=True
        )
    return result


async def _safe_hotel_search(
    trip_ctx: dict[str, Any], user_id: str
) -> dict[str, Any] | None:
    """Call ``_do_hotel_search`` with trip_ctx fields, return result or None.

    Hotel resolution uses geocoding only — see
    :func:`_resolve_destination_for_hotel` for why we don't reuse the
    MWGG-derived ISO-2 country from ``trip_ctx``.
    """
    try:
        from app.ai.graph.tools.hotels import _do_hotel_search

        # When the destination is a country but has no hub mapping, we have
        # no valid city to search — skip gracefully rather than passing the
        # raw country name to FlightLogic (which would return an error).
        if trip_ctx.get("destination_is_country") and not trip_ctx.get(
            "destination_search_city"
        ):
            logger.info(
                "itinerary side-search: skipping hotel search — '%s' is an "
                "unmapped country (add it to country_to_city.py to enable)",
                trip_ctx.get("destination"),
            )
            return None

        # #1127: when the user named a country ("Montenegro") instead of a
        # city, the trip extractor records the country label on
        # ``destination`` (so the itinerary LLM still produces a multi-city
        # country-wide plan) AND populates ``destination_search_city`` with
        # a curated tourist hub (Kotor, in this example). The hotel search
        # requires a real city, so prefer the hub when present.
        destination = trip_ctx.get("destination_search_city") or trip_ctx.get(
            "destination", ""
        )

        # Geocode the destination once → city + full country name + coords.
        # If geocoding fails, fall back to whatever trip_ctx had (which may
        # be an ISO-2 code from MWGG — better than nothing, and the local
        # FlightLogic mock still tolerates it for dev).
        geo_city, geo_country, geo_lat, geo_lng = await _resolve_destination_for_hotel(
            destination
        )

        # Prefer geocoded values; fall back to landmark-resolver coords or
        # the MWGG-derived country only if geocoding came up empty.
        # Strings use ``or`` (empty/None both fall through). Coords use
        # ``is not None`` because 0.0 is a meaningful latitude/longitude
        # (equator / prime meridian) that ``or`` would wrongly override.
        city_name = geo_city or destination
        country_name = geo_country or (trip_ctx.get("destination_country") or "")
        nearby_lat = geo_lat if geo_lat is not None else trip_ctx.get("nearby_lat")
        nearby_lng = geo_lng if geo_lng is not None else trip_ctx.get("nearby_lng")

        result = await _do_hotel_search(
            city_name=city_name,
            country_name=country_name,
            checkin=trip_ctx["departure_date"],
            checkout=trip_ctx["return_date"],
            adults=trip_ctx.get("adults") or 2,
            rooms=trip_ctx.get("rooms") or 1,
            children=trip_ctx.get("children") or 0,
            nearby_lat=nearby_lat,
            nearby_lng=nearby_lng,
            config={"configurable": {"user_id": user_id}},
        )
        if result and result.get("status") == "success":
            result = await _enrich_hotel_images(result, city_name)
        return result
    except Exception:
        logger.exception("itinerary side-search: hotel search failed")
        return None


# ---------------------------------------------------------------------------
# Phase 3 O5 — pre-started side-searches stash
# ---------------------------------------------------------------------------
# When ``pre_resolve_trip`` resolves IATA + dates, it kicks off the side-
# searches immediately (instead of waiting for ``dispatch_itinerary``).  The
# tasks need to survive the graph transition between nodes, so we stash them
# in a module-level dict keyed by ``chat_id``. ``dispatch_itinerary`` then
# pops and awaits them as if it had fired them itself.
#
# Tasks left behind by stale flows (e.g. user pivoted to a different agent
# mid-turn) get cancelled by ``clear_pending_side_searches`` so we don't
# leak file descriptors or burn FlightLogic quota.
_PENDING_SIDE_SEARCHES: dict[
    str,
    tuple[
        asyncio.Task[dict[str, Any] | None] | None,
        asyncio.Task[dict[str, Any] | None] | None,
    ],
] = {}


def stash_pending_side_searches(
    chat_id: str,
    flight_task: asyncio.Task[dict[str, Any] | None] | None,
    hotel_task: asyncio.Task[dict[str, Any] | None] | None,
) -> None:
    """Record pre-started side-search tasks for later pickup.

    Called by ``pre_resolve_trip`` after IATA + dates resolve. If a previous
    pair is still pending for the same chat_id (rare: re-routing during a
    single turn), cancel it first to avoid leaking tasks.
    """
    if chat_id in _PENDING_SIDE_SEARCHES:
        old_flight, old_hotel = _PENDING_SIDE_SEARCHES[chat_id]
        for t in (old_flight, old_hotel):
            if t is not None and not t.done():
                t.cancel()
    _PENDING_SIDE_SEARCHES[chat_id] = (flight_task, hotel_task)


def pop_pending_side_searches(
    chat_id: str,
) -> tuple[
    asyncio.Task[dict[str, Any] | None] | None,
    asyncio.Task[dict[str, Any] | None] | None,
]:
    """Pop pre-started side-search tasks for ``chat_id``.

    Returns ``(None, None)`` when nothing was pre-started (cold path —
    caller is expected to kick off side-searches itself).
    """
    return _PENDING_SIDE_SEARCHES.pop(chat_id, (None, None))


def clear_pending_side_searches(chat_id: str) -> None:
    """Cancel + discard any side-searches stashed for ``chat_id``.

    Called by non-itinerary dispatchers so stale tasks (e.g. pre_resolve fired
    them but the user pivoted to general/flight/hotel) don't leak.
    """
    flight_task, hotel_task = _PENDING_SIDE_SEARCHES.pop(chat_id, (None, None))
    for t in (flight_task, hotel_task):
        if t is not None and not t.done():
            t.cancel()


def compute_hotel_search_key(trip_ctx: dict[str, Any]) -> str:
    """Stable dedup key for the hotel side-search inputs.

    #1127 made follow-up turns (the user replying with origin after the
    ``block_missing_origin`` gate fires) re-enter ``pre_resolve_trip``. The
    hotel-required fields (destination, dates, party) are typically
    UNCHANGED between the cold turn and the follow-up — only ``origin``
    arrives — so without a dedup the hotel FlightLogic call repeats every
    turn until origin lands. This key hashes the inputs ``_safe_hotel_search``
    actually consumes; ``kick_off_side_searches`` skips the fire when the
    trip context's previously-stored ``last_hotel_search_key`` matches the
    current one.

    Format choice: pipe-joined string rather than a real hash — easier to
    eyeball in logs ("kotor|2026-07-20|2026-08-02|2|2|1") and small enough
    to keep on the persisted trip context. Includes ``destination_search_city``
    in addition to ``destination`` so hub-resolved trips (Montenegro → Kotor)
    don't accidentally hit the same key as a regular city destination.
    """
    hub_list: list[dict[str, str]] = trip_ctx.get("destination_hub_list") or []
    hubs_key = "+".join(sorted(h.get("iata", "") for h in hub_list)) if hub_list else ""
    return "|".join(
        [
            str(trip_ctx.get("destination_search_city") or "").lower(),
            str(trip_ctx.get("destination") or "").lower(),
            hubs_key,
            str(trip_ctx.get("departure_date") or ""),
            str(trip_ctx.get("return_date") or ""),
            str(trip_ctx.get("adults") or ""),
            str(trip_ctx.get("children") or ""),
            str(trip_ctx.get("rooms") or 1),
        ]
    )


def kick_off_side_searches(
    trip_ctx: dict[str, Any] | None,
    user_id: str,
) -> tuple[
    asyncio.Task[dict[str, Any] | None] | None,
    asyncio.Task[dict[str, Any] | None] | None,
    str | None,
]:
    """Spawn flight + hotel search tasks if the inputs are present.

    Each side is gated independently — if origin is missing we still fire
    hotel, and vice versa. Returns ``(flight_task, hotel_task, new_hotel_key)``:

    - ``flight_task`` / ``hotel_task`` — asyncio tasks (or None when skipped)
      so the caller can await them concurrently with the LLM agent.
    - ``new_hotel_key`` — the dedup key for the hotel side-search that was
      just fired, or ``None`` when we either skipped firing or the previous
      key already matched. Callers MUST persist this onto
      ``shared_context.trip.last_hotel_search_key`` so the next turn skips a
      duplicate FlightLogic hotel call.

    Doc reference: "Always on. Every authenticated itinerary auto-runs
    flight + hotel searches. If origin is missing, flight search is
    skipped silently."
    """
    if not trip_ctx:
        return None, None, None

    flight_task: asyncio.Task[dict[str, Any] | None] | None = None
    hotel_task: asyncio.Task[dict[str, Any] | None] | None = None
    new_hotel_key: str | None = None

    hub_list: list[dict[str, str]] = trip_ctx.get("destination_hub_list") or []

    if _has_required(trip_ctx, _FLIGHT_REQUIRED):
        if len(hub_list) > 1:
            logger.info(
                "itinerary side-search: kicking off multicity flight search "
                "%s→[%s] on %s (%d hubs) via _search_multicity",
                trip_ctx.get("origin_iata"),
                ", ".join(h["iata"] for h in hub_list),
                trip_ctx.get("departure_date"),
                len(hub_list),
            )
            flight_task = asyncio.create_task(
                _safe_multicity_flight_search(hub_list, trip_ctx, user_id)
            )
        else:
            logger.info(
                "itinerary side-search: kicking off flight search %s→%s on %s",
                trip_ctx.get("origin_iata"),
                trip_ctx.get("destination_iata"),
                trip_ctx.get("departure_date"),
            )
            flight_task = asyncio.create_task(_safe_flight_search(trip_ctx, user_id))
    else:
        logger.debug(
            "itinerary side-search: skipping flight search (missing required fields)"
        )

    # Region-destination guard mirrors ``block_region_destination`` in the
    # generate_itinerary tool: when the user names a continent / region
    # ("Europe", "the Caribbean") the itinerary tool refuses generation and
    # asks for a specific city, so a hotel side-search against the region
    # string is wasted FlightLogic capacity. Flight is naturally gated by
    # missing IATA in this case; hotel only requires ``destination`` + dates
    # so we add the explicit check here.
    from app.ai.graph.tools.itinerary import _destination_is_region

    destination_is_region = _destination_is_region(trip_ctx.get("destination"))

    if _has_required(trip_ctx, _HOTEL_REQUIRED) and not destination_is_region:
        # #1127: hotel dedup. Previous turn's key (if any) lives on
        # ``trip_ctx.last_hotel_search_key``; if the inputs haven't changed
        # we already have hotel results for this exact query and another
        # FlightLogic call would just waste quota. The flight side-search
        # has no equivalent gate today — it's keyed on origin_iata which
        # only lands on follow-up turns, so the cold-skip already prevents
        # the duplicate-fire pattern there.
        current_hotel_key = compute_hotel_search_key(trip_ctx)
        last_hotel_key = trip_ctx.get("last_hotel_search_key")
        if current_hotel_key == last_hotel_key:
            logger.info(
                "itinerary side-search: skipping hotel search — params unchanged "
                "from previous turn (key=%s)",
                current_hotel_key,
            )
        else:
            logger.info(
                "itinerary side-search: kicking off hotel search %s on %s→%s",
                trip_ctx.get("destination"),
                trip_ctx.get("departure_date"),
                trip_ctx.get("return_date"),
            )
            if len(hub_list) > 1:
                logger.info(
                    "itinerary side-search: kicking off multi-hub hotel search "
                    "[%s] (%d hubs)",
                    ", ".join(h["city"] for h in hub_list),
                    len(hub_list),
                )
                hotel_task = asyncio.create_task(
                    _safe_hotel_search_multi_hub(hub_list, trip_ctx, user_id)
                )
            else:
                hotel_task = asyncio.create_task(_safe_hotel_search(trip_ctx, user_id))
            new_hotel_key = current_hotel_key
    elif destination_is_region:
        logger.debug(
            "itinerary side-search: skipping hotel search (destination '%s' is a region)",
            trip_ctx.get("destination"),
        )
    else:
        logger.debug(
            "itinerary side-search: skipping hotel search (missing required fields)"
        )

    return flight_task, hotel_task, new_hotel_key


async def await_side_searches(
    flight_task: asyncio.Task[dict[str, Any] | None] | None,
    hotel_task: asyncio.Task[dict[str, Any] | None] | None,
) -> dict[str, Any]:
    """Await the side-search tasks (if any) and return aggregated results.

    Returns a dict with:
    - ``flights`` (list): best-value-sorted flight list (empty on no-results / error / skipped)
    - ``hotels`` (list): best-value-sorted hotel list (empty on no-results / error / skipped)
    - ``flight_session_id`` (str | None): FlightLogic session for revalidation, when available
    - ``hotel_session_id`` (str | None): FlightLogic session for revalidation, when available
    - ``flight_search_params`` (dict | None): the search params the orchestrator
      used — needed so the FE can hydrate its recommendations slice without
      re-fetching (#1038 follow-up: avoid duplicate FlightLogic calls when the
      user clicks the Flights tab from the itinerary).
    - ``hotel_search_params`` (dict | None): same idea for hotels.
    """
    flights: list[dict[str, Any]] = []
    hotels: list[dict[str, Any]] = []
    flight_session_id: str | None = None
    hotel_session_id: str | None = None
    flight_search_params: dict[str, Any] | None = None
    hotel_search_params: dict[str, Any] | None = None
    flight_result: dict[str, Any] | None = None
    hotel_result: dict[str, Any] | None = None

    if flight_task is not None:
        flight_result = await flight_task
        if flight_result and flight_result.get("status") == "success":
            flights = list(flight_result.get("flights") or [])
            flight_session_id = flight_result.get("session_id") or None
            sp = flight_result.get("search_params")
            if isinstance(sp, dict):
                flight_search_params = sp
            logger.info(
                "itinerary side-search: flight search returned %d flights (session=%s)",
                len(flights),
                flight_session_id or "—",
            )
        elif flight_result:
            logger.info(
                "itinerary side-search: flight status=%s — no flights surfaced",
                flight_result.get("status"),
            )

    if hotel_task is not None:
        hotel_result = await hotel_task
        if hotel_result and hotel_result.get("status") == "success":
            hotels = list(hotel_result.get("hotels") or [])
            hotel_session_id = hotel_result.get("session_id") or None
            sp = hotel_result.get("search_params")
            if isinstance(sp, dict):
                hotel_search_params = sp
            logger.info(
                "itinerary side-search: hotel search returned %d hotels (session=%s)",
                len(hotels),
                hotel_session_id or "—",
            )
        elif hotel_result:
            logger.info(
                "itinerary side-search: hotel status=%s — no hotels surfaced",
                hotel_result.get("status"),
            )

    # Multi-hub chain results (#1152) — present when > 1 hub was searched.
    flight_multicity_chain: dict[str, Any] | None = None
    if flight_task and flight_result:
        flight_multicity_chain = flight_result.get("multicity_chain_result")

    hotel_multistay_chain: dict[str, Any] | None = None
    if hotel_task and hotel_result:
        hotel_multistay_chain = hotel_result.get("multistay_chain_result")

    return {
        "flights": flights,
        "hotels": hotels,
        "flight_session_id": flight_session_id,
        "hotel_session_id": hotel_session_id,
        "flight_search_params": flight_search_params,
        "hotel_search_params": hotel_search_params,
        # Multi-hub session maps — only set when > 1 hub was searched (#1152).
        "flight_hub_sessions": (
            flight_result.get("hub_sessions") if flight_task and flight_result else None
        ),
        "hotel_hub_sessions": (
            hotel_result.get("hub_sessions") if hotel_task and hotel_result else None
        ),
        # Ready-to-embed chain_results for multi-city/stay frontend views (#1152).
        "flight_multicity_chain_result": flight_multicity_chain,
        "hotel_multistay_chain_result": hotel_multistay_chain,
    }


def attach_search_results_to_response(
    response: dict[str, Any],
    side_results: dict[str, Any],
    *,
    is_round_trip: bool,
) -> dict[str, Any]:
    """Mutate the itinerary response with stitched cards + top-level lists.

    Operates on the ``itinerary_results`` response shape produced by
    ``process_itinerary_messages``:
    - ``response["metadata"]["structured_itinerary"]`` — the LLM day plan;
      the stitcher inserts Day 1 / Day N entries.
    - Top-level ``response["flights"]`` / ``["hotels"]`` — the full lists for
      the FE's "Recommended" rails AND for pre-hydrating the recommendations
      slice so the Flights/Stays tabs from the itinerary skip the duplicate
      FlightLogic call.
    - Top-level ``response["flight_session_id"]`` / ``["hotel_session_id"]``
      and ``flight_search_params`` / ``hotel_search_params`` — needed for the
      booking flow and for the FE to recognise the cached results match the
      current trip context.

    Returns the mutated response for caller convenience.
    """
    flights = side_results.get("flights") or []
    hotels = side_results.get("hotels") or []

    metadata = response.get("metadata") or {}
    structured = metadata.get("structured_itinerary")
    if isinstance(structured, dict):
        stitch_itinerary(structured, flights, hotels, is_round_trip=is_round_trip)
    else:
        logger.debug(
            "attach_search_results_to_response: no structured_itinerary in response — "
            "stitcher skipped, top-level flights/hotels still attached"
        )

    # Full lists + session + params ride on the response — LLM never sees them.
    response["flights"] = flights
    response["hotels"] = hotels
    response["flight_session_id"] = side_results.get("flight_session_id")
    response["hotel_session_id"] = side_results.get("hotel_session_id")
    response["flight_search_params"] = side_results.get("flight_search_params")
    response["hotel_search_params"] = side_results.get("hotel_search_params")
    # Multi-hub session maps — only set when > 1 hub was searched (#1152).
    if side_results.get("flight_hub_sessions"):
        response["flight_hub_sessions"] = side_results["flight_hub_sessions"]
    if side_results.get("hotel_hub_sessions"):
        response["hotel_hub_sessions"] = side_results["hotel_hub_sessions"]

    # Multi-hub side-searches: embed as chain_results so the frontend shows
    # multicity flights / multistay hotels alongside the itinerary (#1152).
    chain_results: list[dict[str, Any]] = list(response.get("chain_results") or [])
    multicity_chain = side_results.get("flight_multicity_chain_result")
    if multicity_chain:
        chain_results.append(multicity_chain)
    multistay_chain = side_results.get("hotel_multistay_chain_result")
    if multistay_chain:
        chain_results.append(multistay_chain)
    if chain_results:
        response["chain_results"] = chain_results

    return response


__all__ = [
    "attach_search_results_to_response",
    "await_side_searches",
    "clear_pending_side_searches",
    "kick_off_side_searches",
    "pop_pending_side_searches",
    "stash_pending_side_searches",
]
