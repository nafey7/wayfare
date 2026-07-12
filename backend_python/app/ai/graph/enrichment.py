"""Post-generation enrichment for structured itineraries.

Shared by both V1 (planning_agent) and V2 (generate_itinerary tool).
Populates imageUrl fields via Google Places API and travelBars via
Google Routes API.  All operations are fire-and-forget — failures are
silently ignored so itinerary generation never breaks.
"""

from __future__ import annotations

import asyncio
import logging
import math
import unicodedata
from typing import TYPE_CHECKING, Any

from app.ai.graph.tools.itinerary import TravelBar

if TYPE_CHECKING:
    from app.ai.graph.tools.itinerary import ExpandedContent, StructuredItineraryResult
    from integrations.googlemaps.client import DriveSummary

logger = logging.getLogger(__name__)


def _strip_leading_emoji(text: str) -> str:
    """Strip leading emoji (Unicode Symbol_Other) from text, preserving accented chars."""
    text = text.lstrip()
    while text and unicodedata.category(text[0]).startswith("So"):
        text = text[1:].lstrip()
    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enrich_itinerary(
    result: StructuredItineraryResult,
    destination: str,
) -> StructuredItineraryResult:
    """Populate images and travel bars for a structured itinerary.

    Runs both enrichment steps in parallel so neither starves the other
    under the caller's timeout budget.
    Never raises — enrichment failure must not break itinerary delivery.

    Args:
        result: Structured itinerary with empty imageUrl / travelBars
        destination: Trip destination for search query context

    Returns:
        Same result with enriched fields where possible
    """
    outcomes = await asyncio.gather(
        populate_itinerary_images(result, destination),
        populate_travel_bars(result, destination),
        return_exceptions=True,
    )
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            logger.warning(
                "enrich_itinerary sub-task failed — partial enrichment returned",
                exc_info=outcome,
            )
    return result


# ---------------------------------------------------------------------------
# Google Places — image population
# ---------------------------------------------------------------------------


async def populate_itinerary_images(
    result: StructuredItineraryResult,
    destination: str,
) -> StructuredItineraryResult:
    """Populate imageUrl fields using Google Places API.

    Runs all image searches in parallel.  Failures are silently ignored
    (imageUrl stays empty "").  Never raises — image failure must not
    break itinerary generation.

    Args:
        result: Structured itinerary with empty imageUrl fields
        destination: Trip destination for search query context

    Returns:
        Same result with imageUrl fields populated where possible
    """
    from integrations.googleplaces.client import GooglePlacesClient

    try:
        client = GooglePlacesClient()
        if not client.api_key:
            logger.warning("Google API key not configured — skipping image population")
            return result
    except Exception as e:
        logger.warning(f"Failed to initialize Places client: {e}")
        return result

    # Limit concurrent API calls to avoid rate-limiting
    sem = asyncio.Semaphore(10)

    # Cache destination fallback by width to avoid repeated API calls
    _destination_cache: dict[int, str] = {}

    async def _resolve_destination(max_width: int) -> str:
        """Resolve destination image URL with caching."""
        if max_width in _destination_cache:
            return _destination_cache[max_width]
        try:
            url = await client.resolve_place_image_url(destination, max_width)
            _destination_cache[max_width] = url or ""
        except Exception:
            _destination_cache[max_width] = ""
        return _destination_cache[max_width]

    async def _resolve(query: str, max_width: int = 400) -> str:
        """Resolve a place query to proxy image URL, or '' on failure."""
        async with sem:
            try:
                url = await client.resolve_place_image_url(query, max_width)
                if url:
                    return url
                # Fallback: use cached destination image
                return await _resolve_destination(max_width)
            except Exception:
                return ""

    # Build all image fetch tasks.
    # Local experiences are queued FIRST so they land in the initial semaphore
    # batch and complete before the enrichment timeout cuts the remaining work.
    tasks: list[asyncio.Task[str]] = []
    task_targets: list[tuple[Any, str]] = []  # (object, field_name)

    # Local experience images (400px) — high-priority, queued first
    for exp in result.local_experiences:
        query = f"{exp.title} {destination}"
        tasks.append(asyncio.ensure_future(_resolve(query, 400)))
        task_targets.append((exp, "image_url"))

    for day in result.itinerary_items:
        # Day card image (400px)
        query = f"{day.title} {destination}"
        tasks.append(asyncio.ensure_future(_resolve(query, 400)))
        task_targets.append((day, "image_url"))

        # Expanded main image (800px) — same query, larger
        tasks.append(asyncio.ensure_future(_resolve(query, 800)))
        task_targets.append((day.expanded_content, "main_image_url"))

        # Activity images (200px)
        for activity in day.expanded_content.activities:
            desc = _strip_leading_emoji(activity.description)
            activity_query = f"{desc[:60]} {destination}"
            tasks.append(asyncio.ensure_future(_resolve(activity_query, 200)))
            task_targets.append((activity, "image_url"))

    if not tasks:
        return result

    # Run all in parallel
    logger.info(f"Fetching {len(tasks)} place images for itinerary...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Apply results
    populated = 0
    for i, img_result in enumerate(results):
        if isinstance(img_result, str) and img_result:
            obj, field = task_targets[i]
            setattr(obj, field, img_result)
            populated += 1

    logger.info(f"Populated {populated}/{len(tasks)} itinerary images")
    return result


# ---------------------------------------------------------------------------
# Google Routes — travel bars
# ---------------------------------------------------------------------------


async def populate_travel_bars(
    result: StructuredItineraryResult, destination: str
) -> StructuredItineraryResult:
    """Populate travelBars between consecutive activities using Google Routes API.

    For each pair of consecutive activities in a day, fetches a DRIVE route
    and estimates walk time from distance.  Populates travelBars with car/walk
    options and a polyline for the map.

    Args:
        result: Structured itinerary with empty travelBars
        destination: Trip destination for address context

    Returns:
        Same result with travelBars populated where possible
    """
    from integrations.googlemaps.client import GoogleMapsRoutesClient

    try:
        client = GoogleMapsRoutesClient()
        if not client.api_key:
            logger.warning("Google API key not configured — skipping travelBars")
            return result
    except Exception as e:
        logger.warning(f"Failed to initialize Maps client: {e}")
        return result

    # Limit concurrent API calls to avoid rate-limiting
    sem = asyncio.Semaphore(10)

    async def _resolve_drive(origin_place: str, dest_place: str) -> DriveSummary | None:
        async with sem:
            try:
                return await client.resolve_drive_summary(origin_place, dest_place)
            except Exception:
                logger.debug(
                    "Drive route lookup failed: %s → %s", origin_place, dest_place
                )
                return None

    def _build_place_query(activity: Any) -> str:
        """Build a geocodable place query from an activity's location field.

        Uses the `location` field (e.g. "Cancún International Airport") which
        is a specific venue/place name — NOT the `description` field which is
        a full sentence that Google Routes cannot geocode accurately.
        """
        loc = getattr(activity, "location", "") or ""
        if not loc:
            # Fallback to description if location is empty
            loc = _strip_leading_emoji(getattr(activity, "description", "") or "")[
                :60
            ].rstrip(".")
        return f"{loc}, {destination}"

    # Build tasks: one per consecutive activity pair per day
    tasks: list[asyncio.Task[DriveSummary | None]] = []
    task_targets: list[
        tuple[ExpandedContent, int]
    ] = []  # (expanded_content, pair_index)

    for day in result.itinerary_items:
        activities = day.expanded_content.activities
        num_pairs = len(activities) - 1
        if num_pairs > 0:
            # Pre-allocate travel_bars with None so indices stay aligned
            day.expanded_content.travel_bars = [None] * num_pairs  # type: ignore[list-item]
        for i in range(num_pairs):
            origin_place = _build_place_query(activities[i])
            dest_place = _build_place_query(activities[i + 1])
            tasks.append(
                asyncio.ensure_future(_resolve_drive(origin_place, dest_place))
            )
            task_targets.append((day.expanded_content, i))

    if not tasks:
        return result

    logger.info(f"Fetching {len(tasks)} drive routes for travelBars...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    populated = 0
    for i, route_result in enumerate(results):
        expanded_content, pair_idx = task_targets[i]
        if isinstance(route_result, dict) and route_result.get("duration_text"):
            options = [
                {"icon": "car", "label": route_result["duration_text"]},
            ]

            # Estimate walk time from distance (~5 km/h = ~83 m/min)
            dist_m = route_result.get("distance_meters")
            if dist_m and isinstance(dist_m, (int, float)) and dist_m > 0:
                walk_minutes = math.ceil(dist_m / 83)
                if walk_minutes < 60:
                    walk_label = f"{walk_minutes} min"
                else:
                    hours = walk_minutes // 60
                    mins = walk_minutes % 60
                    walk_label = f"{hours}hr {mins} min" if mins else f"{hours}hr"
                options.append({"icon": "walk", "label": walk_label})

            expanded_content.travel_bars[pair_idx] = TravelBar.model_validate(
                {
                    "options": options,
                    "polyline": route_result.get("polyline") or "",
                    "originLatLng": route_result.get("origin_lat_lng"),
                    "destinationLatLng": route_result.get("destination_lat_lng"),
                }
            )
            populated += 1

    # Remove None placeholders for failed lookups
    for day in result.itinerary_items:
        day.expanded_content.travel_bars = [
            tb for tb in day.expanded_content.travel_bars if tb is not None
        ]

    logger.info(f"Populated {populated}/{len(tasks)} travelBars")
    return result
