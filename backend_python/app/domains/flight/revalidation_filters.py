"""Revalidation filters for flight search results.

Provides reusable helpers to identify and remove flights that fail fare revalidation
after search. Used by both the search endpoint and chat recommendation flows.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from app.domains.flight.schemas import (
    FareItinerary,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
)

logger = logging.getLogger(__name__)

# Per-call timeout for each FlightLogic revalidate (parallel gather; avoids blocking search).
REVALIDATE_CALL_TIMEOUT_SECONDS = 5.0

# Type for revalidate execution (e.g. FlightService.revalidate_fare)
RevalidateFn = Callable[[FlightRevalidateRequest], Awaitable[FlightRevalidateResponse]]


def get_fare_source_code(fare_itinerary: FareItinerary) -> str | None:
    """Extract fare_source_code from a FareItinerary."""
    if not fare_itinerary.pricing:
        return None
    return getattr(fare_itinerary.pricing, "fare_source_code", None)


async def get_flight_ids_to_remove_after_revalidation(
    session_id: str,
    flights: list[FareItinerary],
    adults: int,
    children: int,
    infants: int,
    revalidate_flights_count: int,
    revalidate_fn: RevalidateFn,
) -> set[str]:
    """Identify fare_source_codes of flights to remove after revalidation.

    Revalidates up to revalidate_flights_count flights in parallel via asyncio.gather.
    Returns fare_source_codes for flights that:
    - Have is_fare_available == False
    - Raised an exception during revalidation
    - Have malformed response or missing required data

    Selection strategy (V1): First N flights in response order (stable, deterministic).

    Args:
        session_id: FlightLogic session ID from search response
        flights: List of FareItinerary from filtered search results
        adults: Adult passenger count
        children: Child passenger count
        infants: Infant passenger count
        revalidate_flights_count: Max number of flights to revalidate (0 = none)
        revalidate_fn: Async callable that executes revalidate (e.g. FlightService.revalidate_fare)

    Returns:
        Set of fare_source_code strings to remove from results
    """
    if revalidate_flights_count <= 0 or not flights:
        return set()

    # Take first N candidates in response order
    candidates = flights[:revalidate_flights_count]
    ids_to_remove: set[str] = set()

    async def _revalidate_one(fare_itinerary: FareItinerary) -> str | None:
        """Revalidate single flight; return fare_source_code if invalid, else None."""
        fare_source_code = get_fare_source_code(fare_itinerary)
        if not fare_source_code:
            logger.warning(
                "Revalidation skip: FareItinerary missing fare_source_code",
                extra={
                    "session_id": session_id[:12] + "..."
                    if len(session_id) > 12
                    else session_id
                },
            )
            return None  # Cannot identify flight to remove

        try:
            req = FlightRevalidateRequest(
                session_id=session_id,
                fare_source_code=fare_source_code,
                return_fare_source_code=None,
                adults=adults,
                children=children,
                infants=infants,
            )
            resp = await asyncio.wait_for(
                revalidate_fn(req),
                timeout=REVALIDATE_CALL_TIMEOUT_SECONDS,
            )
            if not getattr(resp, "is_fare_available", False):
                return fare_source_code
            return None
        except TimeoutError:
            logger.warning(
                "Revalidation timed out for fare %s...",
                fare_source_code[:20] if fare_source_code else "?",
                extra={
                    "fare_source_code_prefix": fare_source_code[:12],
                    "timeout_seconds": REVALIDATE_CALL_TIMEOUT_SECONDS,
                },
            )
            return fare_source_code
        except Exception as e:
            logger.warning(
                "Revalidation failed for fare %s...: %s",
                fare_source_code[:20] if fare_source_code else "?",
                e,
                extra={
                    "fare_source_code_prefix": fare_source_code[:12],
                    "error": str(e),
                },
            )
            return fare_source_code

    tasks = [_revalidate_one(fi) for fi in candidates]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            logger.warning(
                "Unexpected revalidation task failure",
                exc_info=r,
                extra={"candidate_index": i},
            )
            code = get_fare_source_code(candidates[i])
            if code:
                ids_to_remove.add(code)
        elif r is not None:
            ids_to_remove.add(r)

    return ids_to_remove


# Per-category revalidation defaults (V1)
CANDIDATES_PER_CATEGORY = 8
REVALIDATE_PER_CATEGORY = 4
MAX_PER_CATEGORY = 3


async def filter_category_flights_after_revalidation(
    session_id: str,
    categories: dict[str, dict],
    adults: int,
    children: int,
    infants: int,
    revalidate_fn: RevalidateFn,
    get_fare_source_code: Callable[[object], str | None],
    *,
    candidates_per_category: int = CANDIDATES_PER_CATEGORY,
    revalidate_per_category: int = REVALIDATE_PER_CATEGORY,
    max_per_category: int = MAX_PER_CATEGORY,
) -> dict[str, dict]:
    """Filter category flights by revalidating top candidates per category.

    For each category: select top 8, revalidate top 4, filter invalid, take top 3.
    Overlapping flights across categories are revalidated once.

    Args:
        session_id: FlightLogic session ID from search response
        categories: Dict with 'cheapest', 'fastest', 'best_value' keys; each value
            must have 'flights' key (list of flight items)
        adults: Adult passenger count
        children: Child passenger count
        infants: Infant passenger count
        revalidate_fn: Async callable that executes revalidate
        get_fare_source_code: Callable to extract fare_source_code from a flight item
        candidates_per_category: Flights selected per category before revalidation (default 8)
        revalidate_per_category: How many of those to revalidate (default 4)
        max_per_category: Flights sent per category after filtering (default 3)

    Returns:
        Same categories dict with invalid flights removed and truncated to max_per_category
    """
    start = time.perf_counter()
    category_names = ("cheapest", "fastest", "best_value")

    # For each category: take first N candidates, collect top revalidate_per_category codes
    # Dedupe across categories
    codes_to_revalidate: set[str] = set()
    category_flights: dict[str, list] = {}

    for name in category_names:
        cat = categories.get(name)
        if not cat or "flights" not in cat:
            category_flights[name] = []
            continue

        flights = cat["flights"]
        # Take first candidates_per_category
        candidates = flights[:candidates_per_category]
        category_flights[name] = candidates

        # From those, take top revalidate_per_category for revalidation
        for item in candidates[:revalidate_per_category]:
            code = get_fare_source_code(item)
            if code:
                codes_to_revalidate.add(code)

    if not codes_to_revalidate:
        for name in category_names:
            cat = categories.get(name)
            if cat and "flights" in cat:
                cat["flights"] = cat["flights"][:max_per_category]
        return categories

    # Revalidate unique set in parallel
    ids_to_remove = await _revalidate_fare_source_codes(
        session_id=session_id,
        fare_source_codes=list(codes_to_revalidate),
        adults=adults,
        children=children,
        infants=infants,
        revalidate_fn=revalidate_fn,
    )

    # Filter each category: remove invalid, truncate to max_per_category
    for name in category_names:
        cat = categories.get(name)
        if not cat or "flights" not in cat:
            continue

        candidates = category_flights.get(name, [])
        before_count = len(candidates)
        filtered = [
            item
            for item in candidates
            if get_fare_source_code(item) not in ids_to_remove
        ]
        cat["flights"] = filtered[:max_per_category]
        removed_count = before_count - len(filtered)
        logger.info(
            "Category revalidation",
            extra={
                "category": name,
                "candidates_count": before_count,
                "removed_count": removed_count,
                "final_count": len(cat["flights"]),
            },
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Category revalidation complete",
        extra={
            "duration_ms": round(duration_ms, 1),
            "ids_removed_total": len(ids_to_remove),
        },
    )
    return categories


async def filter_flights_after_revalidation(
    session_id: str,
    flights: list[dict],
    adults: int,
    children: int,
    infants: int,
    revalidate_fn: RevalidateFn,
    get_fare_source_code: Callable[[object], str | None],
    *,
    revalidate_top_n: int = REVALIDATE_PER_CATEGORY,
) -> list[dict]:
    """Filter a flat (best-value-sorted) flight list by revalidating the top N.

    Replaces the category-aware ``filter_category_flights_after_revalidation``
    for the post-#1034 flat-results pipeline. Revalidates only the top N flights
    (the ones most likely to be displayed prominently) — invalid ones are
    removed. The remaining tail passes through unmodified; booking-time
    revalidation will catch any of those that turn out to be invalid.

    Args:
        session_id: FlightLogic session ID from search response.
        flights: Best-value-sorted list of flight items (dicts).
        adults: Adult passenger count.
        children: Child passenger count.
        infants: Infant passenger count.
        revalidate_fn: Async callable that executes revalidate.
        get_fare_source_code: Callable extracting fare_source_code from a flight.
        revalidate_top_n: How many top flights to revalidate (default 4).

    Returns:
        The flight list with revalidation failures removed. All other flights
        pass through; the list is NOT truncated.
    """
    if not flights:
        return flights

    start = time.perf_counter()

    codes_to_revalidate: set[str] = set()
    for item in flights[:revalidate_top_n]:
        code = get_fare_source_code(item)
        if code:
            codes_to_revalidate.add(code)

    if not codes_to_revalidate:
        return flights

    ids_to_remove = await _revalidate_fare_source_codes(
        session_id=session_id,
        fare_source_codes=list(codes_to_revalidate),
        adults=adults,
        children=children,
        infants=infants,
        revalidate_fn=revalidate_fn,
    )

    before = len(flights)
    filtered = [f for f in flights if get_fare_source_code(f) not in ids_to_remove]
    removed = before - len(filtered)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Flat revalidation complete",
        extra={
            "candidates_revalidated": len(codes_to_revalidate),
            "removed_count": removed,
            "final_count": len(filtered),
            "duration_ms": round(duration_ms, 1),
        },
    )
    return filtered


async def _revalidate_fare_source_codes(
    session_id: str,
    fare_source_codes: list[str],
    adults: int,
    children: int,
    infants: int,
    revalidate_fn: RevalidateFn,
) -> set[str]:
    """Revalidate a list of fare_source_codes in parallel; return invalid codes."""
    if not fare_source_codes:
        return set()

    ids_to_remove: set[str] = set()

    async def _revalidate_one(code: str) -> str | None:
        try:
            req = FlightRevalidateRequest(
                session_id=session_id,
                fare_source_code=code,
                return_fare_source_code=None,
                adults=adults,
                children=children,
                infants=infants,
            )
            resp = await asyncio.wait_for(
                revalidate_fn(req),
                timeout=REVALIDATE_CALL_TIMEOUT_SECONDS,
            )
            if not getattr(resp, "is_fare_available", False):
                return code
            return None
        except TimeoutError:
            logger.warning(
                "Revalidation timed out for fare %s...",
                code[:20] if code else "?",
                extra={
                    "fare_source_code_prefix": (code or "")[:12],
                    "timeout_seconds": REVALIDATE_CALL_TIMEOUT_SECONDS,
                },
            )
            return code
        except Exception as e:
            logger.warning(
                "Revalidation failed for fare %s...: %s",
                code[:20] if code else "?",
                e,
                extra={"fare_source_code_prefix": (code or "")[:12], "error": str(e)},
            )
            return code

    tasks = [_revalidate_one(c) for c in fare_source_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            logger.warning(
                "Unexpected revalidation task failure",
                exc_info=r,
                extra={"fare_index": i},
            )
            c = fare_source_codes[i]
            if c:
                ids_to_remove.add(c)
        elif r is not None:
            ids_to_remove.add(r)
    return ids_to_remove
