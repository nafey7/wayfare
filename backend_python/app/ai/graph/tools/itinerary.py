"""Itinerary generation, budget estimation, and persistence tools for Planning Agent.

Smart tools that use internal LLM calls with structured output for consistent,
validated results. Follows V2 principle: "Tools handle complexity, agents handle
conversation."

Shared Pydantic models (StructuredItineraryResult and nested types) live here and
are imported by planning_agent.py so both V1 and V2 produce identical JSON output.
"""

import asyncio
import contextlib
import json
import logging
import os
import random
import re
import threading
from collections.abc import Callable
from datetime import date, timedelta
from typing import Annotated, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from app.ai.prompt_management import (
    get_itinerary_chunk_fill_prompt,
    get_itinerary_generation_prompt,
    get_itinerary_skeleton_prompt,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_get_stream_writer() -> Callable[[Any], None] | None:
    """Return LangGraph's per-step custom stream writer, or ``None`` when unavailable.

    Piece 3 of #1117 — itinerary tools emit incremental "skeleton →
    activities" snapshots through this writer so the SSE chat endpoint
    can surface day cards to the user within a few seconds of the request
    instead of after the full ~30 s LLM call.

    ``langgraph.config.get_stream_writer()`` only works when called from
    within a node executing under ``graph.astream(...)``. Outside that
    context — the non-streaming ``invoke_supervisor_v2`` path, V1
    ``planning_agent.py`` callers, unit tests — it raises ``RuntimeError``.
    We swallow that (and any ImportError on older langgraph builds) so
    the caller can branch on streaming-vs-not via the ``None`` return.
    """
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        # RuntimeError when outside a graph node; ImportError on older
        # langgraph; anything else is also "no streaming available".
        # Log at DEBUG so local dev can spot a misconfigured langgraph
        # setup (the line stays silent in prod where every non-streaming
        # invoke path expects this to fail).
        logger.debug(
            "_safe_get_stream_writer: no writer available, partials disabled",
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Region-destination gate (#1053 Phase 2 follow-up — R5/R6 fix)
# ---------------------------------------------------------------------------
# The Phase 2 O11 prompt rule asks the LLM to suggest specific cities when the
# user names a vague region (e.g. "Europe city break", "somewhere in Asia").
# In practice the LLM is non-deterministic — about 1 run in 3 it treats
# "Europe" as a literal destination city and generates a "4-day Europe
# itinerary".  This set + helper power a deterministic tool-level refusal,
# mirroring the existing ``block_country_only_origin`` pattern (#1105).
KNOWN_REGIONS: frozenset[str] = frozenset(
    {
        # Continents / hemispheres
        "europe",
        "asia",
        "africa",
        "north america",
        "central america",
        "south america",
        "latin america",
        "the americas",
        "americas",
        "oceania",
        "antarctica",
        # Sub-regions / common vague phrasings
        "caribbean",
        "mediterranean",
        "scandinavia",
        "balkans",
        "middle east",
        "southeast asia",
        "south asia",
        "east asia",
        "central asia",
        "western europe",
        "eastern europe",
        "northern europe",
        "southern europe",
        "sub-saharan africa",
        "north africa",
        "polynesia",
        "micronesia",
        "melanesia",
    }
)

_REGION_ARTICLE_PATTERN = re.compile(r"^(the\s+)", re.IGNORECASE)


def _destination_is_region(destination: str | None) -> bool:
    """True when ``destination`` names a continent / region, not a city.

    Strips a leading article ("the Caribbean" → "caribbean") and trailing
    punctuation before checking against ``KNOWN_REGIONS``.  Conservative:
    anything not in the set passes through (countries, islands, ambiguous
    short names are intentionally NOT blocked here — that's handled by the
    airport / city resolver and the country-only-origin gate).
    """
    if not destination:
        return False
    s = destination.strip().lower()
    s = _REGION_ARTICLE_PATTERN.sub("", s)
    s = s.rstrip(".,!?;:")
    return s in KNOWN_REGIONS


# ---------------------------------------------------------------------------
# LLM singletons — avoid re-instantiating SDK clients on every tool call
# ---------------------------------------------------------------------------
_itinerary_llm: Any = None
_itinerary_lock = threading.Lock()


def _get_itinerary_llm() -> Any:
    global _itinerary_llm
    if _itinerary_llm is None:
        with _itinerary_lock:
            if _itinerary_llm is None:
                from app.ai.graph.llm_factory import create_llm

                _itinerary_llm = create_llm("tool_itinerary", temperature=0.7)
    return _itinerary_llm


# ---------------------------------------------------------------------------
# Shared Pydantic models — used by both V1 (planning_agent.py) and V2 tools
# ---------------------------------------------------------------------------


class ItineraryActivity(BaseModel):
    """A single activity within a day."""

    location: str = Field(
        ...,
        description="Specific place or venue name, e.g. 'Louvre Museum', 'Eiffel Tower', 'Charles de Gaulle Airport'",
    )
    description: str = Field(
        ...,
        description="Activity description with emoji prefix, e.g. '✈️ Arrive at LAX and transfer to your hotel.'",
    )
    image_url: str = Field(
        default="",
        alias="imageUrl",
        description="Image URL (leave empty)",
    )
    duration: str = Field(
        ..., description="Human-readable duration like '2h', '1hr 30m', '3h'"
    )
    rating: float | None = Field(
        default=None,
        description="Optional activity rating (1.0-5.0). Only include for highly-rated attractions.",
    )

    model_config = {"populate_by_name": True}


class LatLng(BaseModel):
    """Latitude/longitude coordinate pair."""

    lat: float
    lng: float


class TravelBarOption(BaseModel):
    """A transport option within a travel bar."""

    icon: str = Field(..., description="Transport icon, e.g. 'car', 'walk'")
    label: str = Field(..., description="Duration label, e.g. '15 min', '1hr 30 min'")


class TravelBar(BaseModel):
    """Travel bar between consecutive activities (populated by enrichment)."""

    model_config = {"populate_by_name": True}

    options: list[TravelBarOption] = Field(
        default_factory=list, description="Transport options"
    )
    polyline: str = Field(default="", description="Encoded polyline for map")
    origin_lat_lng: LatLng | None = Field(
        default=None, alias="originLatLng", description="Route start coordinates"
    )
    destination_lat_lng: LatLng | None = Field(
        default=None, alias="destinationLatLng", description="Route end coordinates"
    )


class DayTip(BaseModel):
    """Insider tip for a day."""

    text: str = Field(..., description="Insider tip text for this day")


class ExpandedContent(BaseModel):
    """Expanded content for a day, shown when the day card is opened."""

    main_image_url: str = Field(
        default="",
        alias="mainImageUrl",
        description="Main image URL for expanded view (leave empty)",
    )
    activities: list[ItineraryActivity] = Field(
        ..., description="Activities for this day (2-4 items)"
    )
    travel_bars: list[TravelBar] = Field(
        default_factory=list,
        alias="travelBars",
        description="Travel bars between activities (leave as empty array)",
    )
    tip: DayTip = Field(..., description="Insider tip for this day")

    model_config = {"populate_by_name": True}


class ItineraryDay(BaseModel):
    """A single day in the itinerary."""

    day: int = Field(..., description="Day number (1-indexed)")
    title: str = Field(..., description="Day title like 'Arrival & First Impressions'")
    description: str = Field(..., description="Brief 1-2 sentence summary of the day")
    image_url: str = Field(
        default="",
        alias="imageUrl",
        description="Image URL for day card (leave empty)",
    )
    expanded_content: ExpandedContent = Field(
        ...,
        alias="expandedContent",
        description="Expanded content with activities, travel bars, and tip",
    )

    model_config = {"populate_by_name": True}


class LocalExperience(BaseModel):
    """A must-try local experience."""

    id: str = Field(..., description="Sequential string ID like '1', '2', '3'")
    image_url: str = Field(
        default="",
        alias="imageUrl",
        description="Image URL (leave empty)",
    )
    image_alt: str = Field(
        default="",
        alias="imageAlt",
        description="Descriptive alt text for image",
    )
    title: str = Field(..., description="Experience title")
    description: str = Field(..., description="1-2 sentence description")

    model_config = {"populate_by_name": True}


class BudgetSnapshot(BaseModel):
    """Brief budget overview."""

    title: str = Field(default="Budget Snapshot", description="Section title")
    description: str = Field(
        ...,
        description="One-liner with per-person USD range, e.g. 'Expect around $1,500-2,000 USD per person'",
    )


class StructuredItineraryResult(BaseModel):
    """Complete structured itinerary matching frontend JSON shape.

    Top-level keys: itineraryItems, footerSectionTitle, budgetSnapshot, localExperiences.
    Used by both V1 (planning_agent.py) and V2 (generate_itinerary tool).
    """

    itinerary_items: list[ItineraryDay] = Field(
        ..., alias="itineraryItems", description="Day-by-day itinerary"
    )
    footer_section_title: str = Field(
        default="Must-Try Local Experiences",
        alias="footerSectionTitle",
        description="Title for local experiences section",
    )
    budget_snapshot: BudgetSnapshot = Field(
        ...,
        alias="budgetSnapshot",
        description="Brief budget overview",
    )
    local_experiences: list[LocalExperience] = Field(
        ...,
        alias="localExperiences",
        description="3 must-try local experiences",
    )

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Two-stage generation schemas (#1053 Phase 4 O1)
# ---------------------------------------------------------------------------
# Skeleton-of-Thought split: stage 1 emits the day-level metadata + global
# fields (budget, experiences) WITHOUT activities; stage 2 fans out parallel
# per-day calls that each fill ``ExpandedContent`` for one day. Final
# composition merges stage-1 + stage-2 outputs back into the existing
# ``StructuredItineraryResult`` so the rest of the pipeline (validation,
# enrichment, side-search stitching, FE rendering) is unchanged.


class ItineraryDaySkeleton(BaseModel):
    """Day metadata WITHOUT ``expandedContent`` — stage-1 output.

    Same field set as ``ItineraryDay`` minus the activity payload. Lets
    the fast stage-1 model emit titles + descriptions for all N days in
    one call (~5 s), so the FE can render skeleton day cards while
    stage-2 fills activities in parallel.

    ``extra='forbid'`` is required for OpenAI's strict structured-output
    mode — the API rejects schemas that don't declare
    ``additionalProperties: false`` at every object level. The legacy
    ``StructuredItineraryResult`` path doesn't trip this because it
    happens to satisfy strict validation via aliases; new schemas must
    opt in explicitly.
    """

    day: int = Field(..., description="Day number (1-indexed)")
    title: str = Field(..., description="Day title like 'Arrival & First Impressions'")
    description: str = Field(..., description="Brief 1-2 sentence summary of the day")
    image_url: str = Field(
        default="",
        alias="imageUrl",
        description="Image URL for day card (leave empty)",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class StructuredItinerarySkeleton(BaseModel):
    """Stage-1 output: day skeletons + global trip fields, no activities.

    Stage 2 then fans out one parallel LLM call per ``itinerary_items``
    entry to fill its ``ExpandedContent``. The merged result conforms to
    :class:`StructuredItineraryResult`.
    """

    itinerary_items: list[ItineraryDaySkeleton] = Field(
        ...,
        alias="itineraryItems",
        description="Day-by-day skeleton (titles + descriptions, no activities)",
    )
    footer_section_title: str = Field(
        default="Must-Try Local Experiences",
        alias="footerSectionTitle",
        description="Title for local experiences section",
    )
    budget_snapshot: BudgetSnapshot = Field(
        ...,
        alias="budgetSnapshot",
        description="Brief budget overview",
    )
    local_experiences: list[LocalExperience] = Field(
        ...,
        alias="localExperiences",
        description="3 must-try local experiences",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class DayActivitiesFill(BaseModel):
    """Stage-2 output: ``ExpandedContent`` for ONE day of the itinerary.

    Kept for backward-compatibility with existing tests. Production
    stage-2 now uses :class:`DayChunkFill` (multi-day per call).
    """

    expanded_content: ExpandedContent = Field(
        ...,
        alias="expandedContent",
        description="Activities + travel bars + tip for this day",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class DayChunkFillItem(BaseModel):
    """Activities for ONE day within a stage-2 chunk call (#1140).

    Part of :class:`DayChunkFill`. The LLM returns one item per day in
    the chunk so the caller can extract each day's ``ExpandedContent``
    and merge it into the final itinerary.
    """

    day: int = Field(..., description="Day number (1-indexed, must match the skeleton)")
    expanded_content: ExpandedContent = Field(
        ...,
        alias="expandedContent",
        description="Activities + travel bars + tip for this day",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class DayChunkFill(BaseModel):
    """Stage-2 output: ``ExpandedContent`` for a CHUNK of consecutive days (#1140).

    Replacing one-call-per-day with one-call-per-chunk means Stage 2
    always fires exactly ``min(num_days, TWO_STAGE_PARALLEL_LIMIT)``
    calls, regardless of trip length. For a 30-day trip at cap=7 this
    reduces from 30 sequential LLM calls (5 batches × 6) to 7 calls
    in a single parallel batch — cutting stage-2 latency from ~50s to
    ~8-10s.

    Each item in ``days`` covers one calendar day; the LLM is prompted
    to generate coherent activities for all chunk days together, which
    also improves day-to-day coherence compared to independent per-day
    calls (adjacent days share hotel / neighbourhood / transport context
    within the same context window).
    """

    days: list[DayChunkFillItem] = Field(
        ...,
        description="One entry per day in this chunk, in ascending day order",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


# ---------------------------------------------------------------------------
# Internal LLM helpers
# ---------------------------------------------------------------------------


def _build_itinerary_chain(llm: Any, formatted_prompt: str) -> Any:
    """Build the ``prompt | llm.with_structured_output(...)`` chain.

    Factored out of :func:`_generate_itinerary_with_llm` so tests can
    swap a controllable chain (custom ``.astream`` / ``.ainvoke``) in
    without having to defeat LangChain's pipe-operator plumbing.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", formatted_prompt),
            ("human", "Generate the structured itinerary."),
        ]
    )
    return prompt | llm.with_structured_output(StructuredItineraryResult)


def _build_skeleton_chain(llm: Any, formatted_prompt: str) -> Any:
    """Stage-1 chain builder (#1053 Phase 4 O1).

    Symmetry with :func:`_build_itinerary_chain` so tests can swap a
    controllable chain in. Returns a chain that produces a
    :class:`StructuredItinerarySkeleton`.

    ``method="function_calling"`` avoids OpenAI's strict JSON-schema
    mode, which requires ``additionalProperties: false`` on every
    nested object — Pydantic v2's default schema generation doesn't
    emit that on un-``extra='forbid'`` models, and our nested types
    (BudgetSnapshot, LocalExperience, etc.) are shared with the legacy
    single-call path so flipping ``extra`` there is risky. Function
    calling is the same wire format minus the strict validation, which
    is fine — the Pydantic model still validates the LLM output on the
    way back.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", formatted_prompt),
            ("human", "Generate the itinerary skeleton (no activities)."),
        ]
    )
    return prompt | llm.with_structured_output(
        StructuredItinerarySkeleton, method="function_calling"
    )


def _build_chunk_fill_chain(llm: Any, formatted_prompt: str) -> Any:
    """Stage-2 chunk chain builder (#1140).

    Returns a chain that produces a :class:`DayChunkFill` covering
    multiple consecutive days. One chain per chunk, all fired in
    parallel via ``asyncio.gather`` — exactly
    ``min(num_days, TWO_STAGE_PARALLEL_LIMIT)`` chains regardless of
    trip length so Stage 2 always finishes in one parallel batch.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", formatted_prompt),
            ("human", "Generate the activities + tips for all days in this chunk."),
        ]
    )
    return prompt | llm.with_structured_output(DayChunkFill, method="function_calling")


def _chunk_skeleton_days(
    items: list[ItineraryDaySkeleton],
    n_chunks: int,
) -> list[list[ItineraryDaySkeleton]]:
    """Split skeleton days into at most ``n_chunks`` consecutive groups (#1140).

    The number of chunks is ``min(len(items), n_chunks)`` — for a 5-day
    trip with cap=7 this gives 5 chunks of 1 day each (same as before).
    For a 30-day trip with cap=7 this gives 7 chunks of 4-5 days each,
    all running in a single parallel batch.

    Distributes days as evenly as possible: the first ``len(items) % k``
    chunks get one extra day.

    Examples:
        30 days, cap=7 → [5, 5, 4, 4, 4, 4, 4]  (7 chunks)
        14 days, cap=7 → [2, 2, 2, 2, 2, 2, 2]  (7 chunks)
         7 days, cap=7 → [1, 1, 1, 1, 1, 1, 1]  (7 chunks = 1/chunk)
         5 days, cap=7 → [1, 1, 1, 1, 1]         (5 chunks, cap not reached)
    """
    n = len(items)
    if n == 0:
        return []
    k = min(n, n_chunks)
    base, extra = divmod(n, k)
    chunks: list[list[ItineraryDaySkeleton]] = []
    start = 0
    for i in range(k):
        size = base + (1 if i < extra else 0)
        chunks.append(items[start : start + size])
        start += size
    return chunks


def _format_chunk_context_bridge(prev_chunk: list[ItineraryDaySkeleton]) -> str:
    """One-line summary of the previous chunk for cross-chunk coherence (#1140).

    Injected as ``{context_bridge}`` in ITINERARY_CHUNK_FILL_PROMPT.
    When the chunk is the first one, returns an empty string so the
    prompt placeholder simply disappears.

    Example output:
      "**Context from the previous days** (Days 1-4): Arrival & Shibuya
       Night Stroll, Asakusa Temples & Old Tokyo Flavors, Meiji Shrine …"
    """
    if not prev_chunk:
        return ""
    day_range = (
        f"Day {prev_chunk[0].day}"
        if len(prev_chunk) == 1
        else f"Days {prev_chunk[0].day}-{prev_chunk[-1].day}"
    )
    titles = ", ".join(d.title for d in prev_chunk)
    # Chunks fire in parallel, so the bridge carries only skeleton titles
    # (thematic context already visible in skeleton_summary), NOT actual
    # hotel or activity data — those don't exist yet when this string is
    # built. The value is prompting the LLM to maintain thematic flow
    # (e.g. don't jump from a beach theme back to a city museum theme
    # without a transition day) rather than referencing specific venues.
    return (
        f"**Thematic context from the preceding chunk** ({day_range}): {titles}. "
        "Use this to maintain thematic flow across chunk boundaries — "
        "avoid jarring theme reversals and keep the overall trip arc coherent."
    )


def _format_chunk_days_spec(chunk: list[ItineraryDaySkeleton], total_days: int) -> str:
    """Structured day-list for the ``{chunk_days_spec}`` prompt variable.

    Gives the LLM explicit day numbers, titles, descriptions, and
    position labels so it doesn't have to infer them from arithmetic.
    """
    lines: list[str] = []
    for d in chunk:
        position = _day_position(d.day, total_days)
        lines.append(f"  • Day {d.day} [{position}] — {d.title}: {d.description}")
    return "\n".join(lines)


async def _generate_itinerary_with_llm(
    destination: str,
    origin: str | None,
    departure_date: str | None,
    return_date: str | None,
    num_days: int,
    adults: int,
    children: int,
    infants: int,
    interests: list[str],
    modification_notes: str | None = None,
    user_preferences: str | None = None,
) -> StructuredItineraryResult:
    """Call LLM with structured output to generate itinerary.

    Uses the same ITINERARY_GENERATION_PROMPT and StructuredItineraryResult schema
    as V1 (planning_agent.py) so both produce identical frontend JSON.

    Piece 3 of #1117 — when invoked from within a streaming graph
    context (``graph.astream(...)``), each incremental partial of the
    structured-output parse is forwarded as an ``itinerary_partial``
    custom event so the FE can render day cards as titles come in and
    then fill activities as each day populates. The non-streaming
    caller path (``graph.ainvoke``, V1 ``planning_agent.py``) is
    unchanged — the function still returns the same fully-populated
    :class:`StructuredItineraryResult`.

    Phase 4 O1 — when ``settings.TWO_STAGE_ITINERARY_ENABLED`` is True,
    delegates to :func:`_generate_itinerary_two_stage` which splits the
    single LLM call into a fast skeleton call + N parallel per-day fill
    calls (Skeleton-of-Thought pattern). Same return type so callers
    are unchanged; flag-gated for safe rollback.
    """
    if settings.TWO_STAGE_ITINERARY_ENABLED:
        return await _generate_itinerary_two_stage(
            destination=destination,
            origin=origin,
            departure_date=departure_date,
            return_date=return_date,
            num_days=num_days,
            adults=adults,
            children=children,
            infants=infants,
            interests=interests,
            modification_notes=modification_notes,
            user_preferences=user_preferences,
        )

    llm = _get_itinerary_llm()

    # Use same prompt as V1 (from Langfuse with hardcoded fallback)
    itinerary_prompt_template = get_itinerary_generation_prompt()
    formatted_prompt = itinerary_prompt_template.format(
        origin=origin or "not provided",
        destination=destination,
        departure_date=departure_date or "Flexible",
        return_date=return_date or "TBD",
        num_days=num_days,
        adults=adults,
        children=children,
        infants=infants,
        interests=", ".join(interests) if interests else "general tourism",
        user_preferences=user_preferences
        or "No specific preferences set — use general defaults.",
    )

    if modification_notes:
        formatted_prompt += f"\n\n<user_modification>{modification_notes}</user_modification>\nAdjust the itinerary to reflect the modification request above while keeping the same destination, dates, and traveler count."

    chain = _build_itinerary_chain(llm, formatted_prompt)

    # When running inside ``invoke_supervisor_v2_streaming``,
    # ``get_stream_writer`` returns a callable that emits ``("custom",
    # payload)`` events into the graph stream. The supervisor wrapper
    # passes those through verbatim and ChatService routes them as
    # ``itinerary_partial`` SSE events to the FE.
    writer = _safe_get_stream_writer()

    final: StructuredItineraryResult | None = None
    last_dict: dict[str, Any] | None = None

    try:
        async for partial in chain.astream({}):
            # ``partial`` shape depends on the LLM provider: OpenAI
            # structured outputs yields incrementally-complete dicts,
            # some Gemini paths yield Pydantic instances with partial
            # fields, the final iteration produces the fully-populated
            # ``StructuredItineraryResult``. Handle either form so the
            # writer always emits a snapshot dict the FE can render.
            if isinstance(partial, StructuredItineraryResult):
                final = partial
                last_dict = partial.model_dump(by_alias=True, exclude_none=True)
            elif isinstance(partial, dict):
                last_dict = partial
            else:
                continue

            if writer is not None and last_dict:
                try:
                    writer({"type": "itinerary_partial", "data": last_dict})
                except Exception:
                    # Stream writer is best-effort — never break itinerary
                    # generation if it raises (e.g. graph torn down, queue
                    # full). The final result still ships via the return.
                    logger.debug(
                        "itinerary_partial stream writer raised",
                        exc_info=True,
                    )
    except Exception:
        # ``astream`` failed (provider doesn't support streaming on this
        # combo, network blip, parser failure). Fall back to the
        # non-streaming call so the FE still gets the final itinerary.
        logger.warning(
            "with_structured_output().astream() failed for itinerary — "
            "falling back to ainvoke",
            exc_info=True,
        )
        return await chain.ainvoke({})

    if final is not None:
        return final

    if last_dict is not None:
        # Stream yielded dicts only — coerce the final dict to the typed
        # model so the caller sees the same return type as the
        # non-streaming path.
        try:
            return StructuredItineraryResult.model_validate(last_dict)
        except Exception:
            # IMPORTANT: this triggers a SECOND full LLM call (see
            # below). Surface at WARN with a payload-shape snippet so
            # we can pivot in prod metrics — if this fires regularly
            # the provider's streaming parser is producing malformed
            # finals and we should switch to ainvoke-only for that
            # provider rather than silently doubling cost + latency.
            keys_snippet = (
                sorted(last_dict.keys())[:8] if isinstance(last_dict, dict) else None
            )
            logger.warning(
                "itinerary final partial dict failed StructuredItineraryResult "
                "validation — issuing a second LLM call via ainvoke. "
                "last_dict keys=%r",
                keys_snippet,
                exc_info=True,
            )

    # Defensive fallback — astream yielded nothing usable. Should be
    # unreachable in practice but keeps the function's return contract
    # honest. Same WARN concern as above: this is a second full LLM
    # call; if it fires often there's a bug upstream.
    logger.warning(
        "itinerary astream completed with no usable partials — falling "
        "back to a second ainvoke call",
    )
    return await chain.ainvoke({})


# ---------------------------------------------------------------------------
# Two-stage generation (#1053 Phase 4 O1)
# ---------------------------------------------------------------------------


def _format_skeleton_summary(skeleton: StructuredItinerarySkeleton) -> str:
    """Compact day-list string for stage-2 cross-day coherence context.

    Each stage-2 call receives this so it can avoid duplicating landmarks
    or activities other days plausibly cover. Kept short — every token
    here is duplicated across N parallel calls.
    """
    lines: list[str] = []
    for d in skeleton.itinerary_items:
        lines.append(f"  Day {d.day}: {d.title} — {d.description}")
    return "\n".join(lines)


def _day_position(day: int, total: int) -> str:
    """Stage-2 prompt variable: arrival / middle / departure classifier.

    Pulls the arrival + departure day rules out of conditionals in the
    prompt itself so the LLM has an explicit position label rather than
    inferring from day-number arithmetic.
    """
    if day == 1:
        return "ARRIVAL"
    if day == total:
        return "DEPARTURE"
    return "MIDDLE"


async def _fill_chunk_activities(
    *,
    llm: Any,
    skeleton: StructuredItinerarySkeleton,
    chunk: list[ItineraryDaySkeleton],
    prev_chunk: list[ItineraryDaySkeleton],
    common_vars: dict[str, Any],
    modification_notes: str | None,
    semaphore: asyncio.Semaphore,
    writer: Callable[[Any], None] | None,
    chunk_fill_prompt_template: str | None = None,
) -> list[tuple[int, ExpandedContent | None]]:
    """Run one stage-2 LLM call for a CHUNK of consecutive days (#1140).

    Returns a list of ``(day_number, expanded_content)`` tuples — one per
    day in the chunk. ``expanded_content`` is ``None`` for any day that
    the LLM omitted or that failed validation; the merge step substitutes
    a placeholder so the FE still renders a complete N-day layout.

    One retry per chunk on transient failures (same jittered backoff as
    the per-day helper). On unrecoverable failure all days in the chunk
    return ``(day_number, None)`` so the rest of the itinerary still ships.
    """
    from app.ai.graph.prompts.itinerary_agent import ITINERARY_CHUNK_FILL_PROMPT

    skeleton_summary = _format_skeleton_summary(skeleton)
    context_bridge = _format_chunk_context_bridge(prev_chunk)
    chunk_days_spec = _format_chunk_days_spec(chunk, common_vars["num_days"])

    # Use the pre-fetched template when provided (passed from the
    # orchestrator to avoid N blocking Langfuse calls inside gather).
    if chunk_fill_prompt_template is not None:
        prompt_template = chunk_fill_prompt_template
    else:
        try:
            prompt_template = get_itinerary_chunk_fill_prompt()
        except Exception:
            prompt_template = ITINERARY_CHUNK_FILL_PROMPT

    formatted = prompt_template.format(
        **common_vars,
        chunk_size=len(chunk),
        context_bridge=context_bridge,
        skeleton_summary=skeleton_summary,
        chunk_days_spec=chunk_days_spec,
    )
    if modification_notes:
        formatted += (
            f"\n\n<user_modification>{modification_notes}</user_modification>\n"
            "Apply the modification when relevant to any of the days in this chunk."
        )

    chain = _build_chunk_fill_chain(llm, formatted)

    async with semaphore:
        for attempt in (1, 2):
            try:
                result: DayChunkFill = await chain.ainvoke({})
                # Build a lookup keyed by day number for robust merging
                filled: dict[int, ExpandedContent] = {}
                for item in result.days:
                    filled[item.day] = item.expanded_content
                    if writer is not None:
                        try:
                            writer(
                                {
                                    "type": "itinerary_partial",
                                    "data": {
                                        "day_filled": item.day,
                                        "expandedContent": item.expanded_content.model_dump(
                                            by_alias=True, exclude_none=True
                                        ),
                                    },
                                }
                            )
                        except Exception:
                            logger.debug(
                                "chunk_fill writer raised for day %d",
                                item.day,
                                exc_info=True,
                            )
                return [(d.day, filled.get(d.day)) for d in chunk]
            except Exception as e:
                from app.ai.errors import classify_exception

                classified = classify_exception(e)
                chunk_range = f"{chunk[0].day}-{chunk[-1].day}"
                logger.warning(
                    "two-stage chunk days %s attempt %d failed (class=%s)",
                    chunk_range,
                    attempt,
                    classified.cls.value,
                    exc_info=True,
                )
                if attempt == 1 and classified.is_retryable:
                    sleep_for = 0.5 + random.uniform(0.0, 0.5)  # noqa: S311
                    await asyncio.sleep(sleep_for)
                else:
                    break

    return [(d.day, None) for d in chunk]


def _placeholder_expanded_content(day: ItineraryDaySkeleton) -> ExpandedContent:
    """Minimal valid ``ExpandedContent`` when stage-2 fails for one day.

    Renders a single "We couldn't generate activities for this day —
    try regenerating just this day" placeholder so the FE shows a
    consistent N-day layout instead of a missing card.
    """
    return ExpandedContent(
        activities=[
            ItineraryActivity(
                location=day.title,
                description=(
                    f"We hit a snag generating activities for this day. "
                    f"Tell me to regenerate day {day.day} and we'll try again."
                ),
                duration="—",
            )
        ],
        tip=DayTip(
            text="Regenerate this day if you'd like fresh suggestions.",
        ),
    )


async def _generate_itinerary_two_stage(
    *,
    destination: str,
    origin: str | None,
    departure_date: str | None,
    return_date: str | None,
    num_days: int,
    adults: int,
    children: int,
    infants: int,
    interests: list[str],
    modification_notes: str | None = None,
    user_preferences: str | None = None,
) -> StructuredItineraryResult:
    """Skeleton-of-Thought two-stage generation (#1053 Phase 4 O1).

    Stage 1: one LLM call produces the trip skeleton (day titles +
    descriptions + budget + experiences). ~5 s on gpt-5.4-mini.

    Stage 2: N parallel LLM calls each fill ``ExpandedContent`` for one
    day. Parallel concurrency bounded by
    ``settings.TWO_STAGE_PARALLEL_LIMIT`` to stay within OpenAI tier
    rate limits. ~5 s wall when N ≤ limit; multiple batches for
    longer trips (e.g. 30-day at cap=7 = 5 batches ≈ 25 s).

    Per-day failure handling: 1 retry per failed day inside
    ``_fill_day_activities``; if both attempts fail, a placeholder is
    substituted so the FE still renders the full N-day layout.

    Streaming integration: when called from within ``graph.astream``,
    the stage-1 chain emits ``itinerary_partial`` events as titles
    parse (Phase 3 wiring); each completed stage-2 day emits an
    ``itinerary_partial`` event with ``{day_filled: N, expandedContent: ...}``
    so the FE merges each day's activities as they land.
    """
    llm = _get_itinerary_llm()

    # ----- common prompt vars (shared between stage 1 + stage 2) -----
    common_vars: dict[str, Any] = {
        "origin": origin or "not provided",
        "destination": destination,
        "departure_date": departure_date or "Flexible",
        "return_date": return_date or "TBD",
        "num_days": num_days,
        "adults": adults,
        "children": children,
        "infants": infants,
        "interests": ", ".join(interests) if interests else "general tourism",
        "user_preferences": user_preferences
        or "No specific preferences set — use general defaults.",
    }

    # ----- stage 1: skeleton -----
    skeleton_prompt_template = get_itinerary_skeleton_prompt()
    skeleton_prompt = skeleton_prompt_template.format(**common_vars)
    if modification_notes:
        skeleton_prompt += (
            f"\n\n<user_modification>{modification_notes}</user_modification>\n"
            "Adjust the skeleton (titles + descriptions + budget) accordingly; "
            "keep the same destination, dates, and traveler count."
        )

    skeleton_chain = _build_skeleton_chain(llm, skeleton_prompt)
    writer = _safe_get_stream_writer()

    skeleton: StructuredItinerarySkeleton | None = None
    last_skeleton_dict: dict[str, Any] | None = None
    try:
        async for partial in skeleton_chain.astream({}):
            if isinstance(partial, StructuredItinerarySkeleton):
                skeleton = partial
                last_skeleton_dict = partial.model_dump(
                    by_alias=True, exclude_none=True
                )
            elif isinstance(partial, dict):
                last_skeleton_dict = partial
            else:
                continue
            if writer is not None and last_skeleton_dict:
                try:
                    writer({"type": "itinerary_partial", "data": last_skeleton_dict})
                except Exception:
                    # Stream writer is best-effort — never break itinerary
                    # generation if it raises (e.g. graph torn down, queue
                    # full). The final result still ships via the return.
                    logger.debug("skeleton stream writer raised", exc_info=True)
    except Exception:
        logger.warning(
            "two-stage stage-1 astream failed — falling back to ainvoke",
            exc_info=True,
        )
        skeleton = await skeleton_chain.ainvoke({})

    if skeleton is None and last_skeleton_dict is not None:
        try:
            skeleton = StructuredItinerarySkeleton.model_validate(last_skeleton_dict)
        except Exception:
            logger.warning(
                "stage-1 final partial failed validation — falling back to ainvoke",
                exc_info=True,
            )
    if skeleton is None:
        skeleton = await skeleton_chain.ainvoke({})

    # ----- stage 2: chunk-based parallel fills (#1140) -----
    # Split all N days into exactly min(N, cap) chunks so Stage 2 always
    # finishes in ONE parallel batch regardless of trip length. For a
    # 30-day trip (cap=10) this produces 10 chunks of 3 days each — one
    # asyncio.gather call, ~8-10s, vs the old 5-batch ×7 scheme (~50-60s)
    # that caused AWS ALB timeout in production.
    #
    # Adjacent days within a chunk share the LLM context window, improving
    # hotel / neighbourhood / transport continuity compared to independent
    # per-day calls.

    # Fetch the chunk-fill prompt template ONCE here at the orchestration
    # level rather than inside each ``_fill_chunk_activities`` call.
    # ``get_itinerary_chunk_fill_prompt()`` calls Langfuse synchronously
    # (blocking HTTP). If called inside each chunk task it serialises all N
    # tasks despite ``asyncio.gather`` — observed as N sequential Langfuse
    # round-trips adding ~2s × N = ~20s of overhead on a 10-chunk turn.
    # Fetching once and passing the result as a parameter eliminates that.
    try:
        _chunk_fill_prompt_template = get_itinerary_chunk_fill_prompt()
    except Exception:
        from app.ai.graph.prompts.itinerary_agent import ITINERARY_CHUNK_FILL_PROMPT

        _chunk_fill_prompt_template = ITINERARY_CHUNK_FILL_PROMPT

    chunks = _chunk_skeleton_days(
        skeleton.itinerary_items, settings.TWO_STAGE_PARALLEL_LIMIT
    )
    # ``_chunk_skeleton_days`` guarantees len(chunks) ≤ cap, so the
    # semaphore never blocks in normal use — all chunks acquire it
    # immediately and run concurrently.  It is retained so that callers
    # invoking ``_fill_chunk_activities`` directly (e.g. tests or future
    # code) still have concurrency protection if they pass more tasks
    # than the cap.
    semaphore = asyncio.Semaphore(settings.TWO_STAGE_PARALLEL_LIMIT)
    chunk_tasks = [
        _fill_chunk_activities(
            llm=llm,
            skeleton=skeleton,
            chunk=chunk,
            prev_chunk=chunks[i - 1] if i > 0 else [],
            common_vars=common_vars,
            modification_notes=modification_notes,
            semaphore=semaphore,
            writer=writer,
            chunk_fill_prompt_template=_chunk_fill_prompt_template,
        )
        for i, chunk in enumerate(chunks)
    ]
    # return_exceptions=True: one failing chunk doesn't cancel the rest;
    # failed chunks produce (day, None) tuples that the merge step replaces
    # with placeholder activities so the FE still renders the full layout.
    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

    # Flatten chunk results into a flat day→content mapping
    fill_by_day: dict[int, ExpandedContent | None] = {}
    for chunk, chunk_result in zip(chunks, chunk_results, strict=False):
        if isinstance(chunk_result, BaseException):
            day_range = (
                f"day {chunk[0].day}"
                if len(chunk) == 1
                else f"days {chunk[0].day}-{chunk[-1].day}"
            )
            logger.error(
                "two-stage chunk task raised unhandled exception "
                "(%s will be placeholders)",
                day_range,
                exc_info=chunk_result,
            )
            continue
        for day_num, content in chunk_result:
            fill_by_day[day_num] = content
    merged_days: list[ItineraryDay] = []
    for day_skeleton in skeleton.itinerary_items:
        expanded = fill_by_day.get(day_skeleton.day)
        if expanded is None:
            expanded = _placeholder_expanded_content(day_skeleton)
        merged_days.append(
            ItineraryDay(
                day=day_skeleton.day,
                title=day_skeleton.title,
                description=day_skeleton.description,
                image_url=day_skeleton.image_url,
                expanded_content=expanded,
            )
        )

    return StructuredItineraryResult(
        itinerary_items=merged_days,
        footer_section_title=skeleton.footer_section_title,
        budget_snapshot=skeleton.budget_snapshot,
        local_experiences=skeleton.local_experiences,
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_itinerary(result: StructuredItineraryResult) -> dict[str, Any]:
    """Validate generated itinerary for logical consistency."""
    warnings: list[str] = []

    if not result.itinerary_items:
        warnings.append("No itinerary days generated")

    day_numbers = [d.day for d in result.itinerary_items]
    expected = list(range(1, len(result.itinerary_items) + 1))
    if day_numbers != expected:
        warnings.append(f"Day numbers not sequential: {day_numbers}")

    for day in result.itinerary_items:
        if not day.expanded_content.activities:
            warnings.append(f"Day {day.day} has no activities")

    return {"valid": len(warnings) == 0, "warnings": warnings}


# ---------------------------------------------------------------------------
# Tool input schemas
# ---------------------------------------------------------------------------


class GenerateItineraryInput(BaseModel):
    """Input schema for itinerary generation."""

    destination: str = Field(
        description="Trip destination — city name only, no country (e.g., 'Tokyo', 'Cancún', 'Barcelona')"
    )
    origin: str | None = Field(
        None,
        description=(
            "OPTIONAL — city name where the traveler is departing from "
            "(e.g., 'Amsterdam'). When provided the flight side-search fires; "
            "when absent the itinerary generates without flights. "
            "Pass the city only, never a country."
        ),
    )
    departure_date: str | None = Field(
        None, description="Departure date in YYYY-MM-DD format"
    )
    return_date: str | None = Field(
        None, description="Return date in YYYY-MM-DD format"
    )
    num_days: int = Field(
        default=0,
        description=(
            "Number of days for the trip. ALWAYS pass the actual number when the user "
            "stated a duration (e.g. '5 day trip' → 5, 'a week' → 7, 'long weekend' → 3). "
            "Pass 0 ONLY if no duration was mentioned and you have no way to know."
        ),
        ge=0,
        le=30,
    )
    adults: int = Field(default=1, description="Number of adult travelers", ge=1)
    children: int = Field(default=0, description="Number of child travelers", ge=0)
    infants: int = Field(
        default=0, description="Number of infant travelers (under 2)", ge=0
    )
    interests: list[str] = Field(
        default_factory=list,
        description="Trip interests (e.g., ['food', 'temples', 'hiking'])",
    )
    modification_notes: str | None = Field(
        None,
        description="User's modification request when regenerating (e.g., 'make it more relaxed', 'add a museum', 'less walking')",
    )


# ---------------------------------------------------------------------------
# Smart tools (with internal LLM + validation)
# ---------------------------------------------------------------------------


@tool(
    "generate_itinerary",
    args_schema=GenerateItineraryInput,
    response_format="content_and_artifact",
)
async def generate_itinerary(
    destination: str,
    num_days: int = 0,
    origin: str | None = None,
    departure_date: str | None = None,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    interests: list[str] | None = None,
    modification_notes: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # type: ignore[assignment]
) -> tuple[str, dict[str, Any]]:
    """Generate a structured day-by-day travel itinerary.

    Use this tool when you have enough trip details (at minimum: destination and
    duration) to generate a complete itinerary. Returns a validated, structured
    plan with activities, meals, local experiences, and a budget snapshot.

    The tool uses an internal LLM call with structured output for consistent
    formatting that matches the frontend itinerary card component.

    Args:
        destination: Where the trip is going — city name only (e.g., "Tokyo", "Cancún")
        num_days: Days for the trip. When BOTH `departure_date` and `return_date` are provided, the tool ALWAYS uses the inclusive day count between them (Jun 4 → Jun 7 = 4 days) — your `num_days` value is ignored in that case. Only pass `num_days` when one or both dates are missing.
        origin: Where traveling from. OPTIONAL — when provided the flight side-search fires; when absent the itinerary generates without flights.
        departure_date: Departure date YYYY-MM-DD (optional)
        return_date: Return date YYYY-MM-DD (optional)
        adults: Number of adults (default 1)
        children: Number of children (default 0)
        infants: Number of infants under 2 (default 0)
        interests: List of interests like ["food", "temples"] (optional)
        modification_notes: User's modification request when regenerating (optional)

    Returns:
        Tuple of (compact_json_str, full_itinerary_dict).
    """
    interests = interests or []

    # Hard guard: reject generation when the supervisor detected a
    # duration-without-date pattern (e.g. "Plan a 4-day trip to Rome"
    # with no departure date).  The LLM sometimes auto-picks a date
    # despite prompt instructions; this guard makes the rejection
    # deterministic.  modification_notes → re-generation of an existing
    # plan where dates are already confirmed.
    configurable = (config or {}).get("configurable", {})
    if not modification_notes and configurable.get("block_dateless_generation", False):
        return (
            json.dumps(
                {
                    "status": "error",
                    "error": "Departure date has not been confirmed by the user.",
                    "instruction": (
                        "The user has not provided a departure date yet. "
                        "Ask ONLY for the departure date — do NOT pick one yourself. "
                        "Example: 'When would you like to depart?'"
                    ),
                }
            ),
            {},
        )

    # #1053 Phase 2 R5/R6 fix: hard guard for continent/region destinations.
    # The Phase 2 O11 prompt rule asks the LLM to suggest specific cities
    # when the user names a vague region ("Europe city break"), but the LLM
    # ignores the rule ~1 in 3 runs and generates a "4-day Europe itinerary"
    # treating the continent as a literal city. This tool-level gate makes
    # the refusal deterministic, mirroring ``block_country_only_origin``.
    #
    # Regeneration carve-out: the existing-itinerary case is identified by
    # the supervisor-supplied ``itinerary_already_generated`` flag (NOT by
    # the LLM-supplied ``modification_notes`` — that string can be
    # hallucinated on a first call to silently bypass the gate, same risk
    # as the country-only-origin gate).
    itinerary_already_generated_for_region = bool(
        configurable.get("itinerary_already_generated", False)
    )
    if not itinerary_already_generated_for_region and _destination_is_region(
        destination
    ):
        return (
            json.dumps(
                {
                    "status": "error",
                    "error": (
                        f"{destination!r} is a region, not a specific city — "
                        "cannot generate an itinerary for a continent or region."
                    ),
                    "instruction": (
                        f"{destination!r} is too broad for an itinerary. "
                        "Suggest 2-3 specific cities that match the user's vibe "
                        "(e.g. for Europe: Paris 🗼, Barcelona 🌊, Prague 🏰; "
                        "for the Caribbean: Barbados 🏖️, Aruba ☀️, Jamaica 🌴) "
                        "and ASK the user to pick one. Do NOT retry "
                        "generate_itinerary with the same destination."
                    ),
                }
            ),
            {},
        )

    # #1105: hard guard for country-only origins. The supervisor sets this
    # flag when the geocoder resolved ``origin`` to a country (e.g. "the US")
    # rather than a city. Prompt-level BLOCKING is unreliable here — the
    # LLM often skips it and generates anyway because the itinerary's own
    # "required fields" (destination + dates) are filled. Returning an
    # error from the tool itself is deterministic: the agent receives it,
    # MUST ask the user for a specific city, and the gate releases once
    # ``origin_iata`` is set (or ``origin_is_country`` flips to False).
    #
    # Regeneration carve-out: the existing-itinerary case is identified by
    # the supervisor-supplied ``itinerary_already_generated`` flag (NOT by
    # the LLM-supplied ``modification_notes`` — that string can be
    # hallucinated on a first call to silently bypass the gate).
    itinerary_already_generated = bool(
        configurable.get("itinerary_already_generated", False)
    )
    if not itinerary_already_generated and configurable.get(
        "block_country_only_origin", False
    ):
        country_label = configurable.get("country_only_origin_value", "") or origin
        return (
            json.dumps(
                {
                    "status": "error",
                    "error": (
                        f"Origin {country_label!r} is a country, not a specific city."
                    ),
                    "instruction": (
                        f"Ask the user which city of {country_label} they are "
                        "flying from. Suggest 3-5 well-known cities of that "
                        "country with their major airport IATA codes in "
                        "parentheses (e.g. for the US: 'JFK/EWR for NYC, LAX "
                        "for Los Angeles, ORD for Chicago, SFO for San "
                        "Francisco, MIA for Miami'; adapt to whichever "
                        "country the origin refers to). Combine the question "
                        "with any other missing fields in the SAME numbered "
                        "response. Do NOT retry generate_itinerary until the "
                        "user provides a specific city."
                    ),
                }
            ),
            {},
        )

    # Origin is optional — the itinerary day-plan generates without it.
    # When origin is present the flight side-search fires; when absent
    # it silently skips (Flights tab stays empty but the day-plan ships).

    # Derive num_days from dates, or return_date from num_days + departure.
    # Uses inclusive counting: Apr 17-19 = 3 days (17th, 18th, 19th).
    # When BOTH dates are provided, the date range is authoritative — override
    # any agent-passed num_days. This prevents drift when the user says "3-day
    # trip" but provides "June 4 to June 7" (which is 4 days inclusive).
    if departure_date and return_date:
        with contextlib.suppress(ValueError):
            derived = (
                date.fromisoformat(return_date) - date.fromisoformat(departure_date)
            ).days + 1
            if derived > 0:
                if num_days and num_days != derived:
                    logger.info(
                        "generate_itinerary: agent passed num_days=%d but date range "
                        "%s → %s spans %d days. Using date range as authoritative.",
                        num_days,
                        departure_date,
                        return_date,
                        derived,
                    )
                num_days = derived

    if num_days == 0:
        return (
            json.dumps(
                {
                    "status": "error",
                    "error": "Cannot determine trip duration.",
                    "instruction": (
                        "Ask the user how many days they want to travel, "
                        "or ask for a return date so the duration can be calculated."
                    ),
                }
            ),
            {},
        )

    # Derive return_date when agent passed num_days + departure but no return_date.
    # Day 1 is inclusive, so return = departure + (num_days - 1).
    if not return_date and departure_date and num_days > 0:
        with contextlib.suppress(ValueError):
            return_date = str(
                date.fromisoformat(departure_date) + timedelta(days=num_days - 1)
            )

    # Read pre-fetched preferences from RunnableConfig (set by supervisor_v2).
    # Avoids a duplicate DB call — supervisor already fetched and formatted them.
    user_preferences_text: str | None = None
    prefs_from_config = configurable.get("user_preferences_context", "")
    if prefs_from_config:
        user_preferences_text = prefs_from_config

    try:
        itinerary = await _generate_itinerary_with_llm(
            destination=destination,
            origin=origin,
            departure_date=departure_date,
            return_date=return_date,
            num_days=num_days,
            adults=adults,
            children=children,
            infants=infants,
            interests=interests,
            modification_notes=modification_notes,
            user_preferences=user_preferences_text,
        )
    except Exception as e:
        logger.error(
            "Itinerary generation failed for %s: %s", destination, e, exc_info=True
        )
        return (
            json.dumps(
                {
                    "status": "error",
                    "error": "Could not generate itinerary due to an internal error.",
                    "instruction": "Inform the user the itinerary could not be generated "
                    "and ask if they'd like to try again or adjust their request.",
                }
            ),
            {},
        )

    # Enrich with Google Places images and Google Routes travel bars
    # (same post-processing as V1 planning_agent).
    #
    # #1053 Phase 1 O6: cap enrichment at ENRICHMENT_TIMEOUT_S so slow Google
    # API calls don't dominate the critical path. Both enrichment steps run in
    # parallel (asyncio.gather) so the budget covers whichever takes longer.
    # 4s observed to cover p95 for 7-14 day trips (~35 image + ~20 route calls
    # at Semaphore(10)). Override via ENRICHMENT_TIMEOUT_S env-var if needed.
    # Partial enrichment is acceptable — FE usePlacesImage hook fills gaps.
    from app.ai.graph.enrichment import enrich_itinerary

    ENRICHMENT_TIMEOUT_S = float(os.environ.get("ENRICHMENT_TIMEOUT_S", "4.0"))
    try:
        itinerary = await asyncio.wait_for(
            enrich_itinerary(itinerary, destination),
            timeout=ENRICHMENT_TIMEOUT_S,
        )
    except TimeoutError:
        logger.info(
            "Enrichment did not complete within %.1fs for %s — returning "
            "partially-enriched itinerary",
            ENRICHMENT_TIMEOUT_S,
            destination,
        )

    validation = _validate_itinerary(itinerary)
    # Serialize with by_alias=True so frontend gets camelCase (itineraryItems, expandedContent, etc.)
    itinerary_dict = itinerary.model_dump(by_alias=True)

    if validation["warnings"]:
        logger.warning(
            "Itinerary validation warnings for %s: %s",
            destination,
            validation["warnings"],
        )

    actual_days = len(itinerary.itinerary_items)
    logger.info(
        "Generated %d-day itinerary for %s (requested %d days)%s",
        actual_days,
        destination,
        num_days,
        f" [modification: {modification_notes}]" if modification_notes else "",
    )

    activity_count = sum(
        len(day.expanded_content.activities) for day in itinerary.itinerary_items
    )

    # content — the only part the LLM sees. Compact string, no itinerary JSON.
    content = json.dumps(
        {
            "status": "success",
            "destination": destination,
            "validation": validation,
            "summary": (
                f"{actual_days}-day itinerary for {destination} generated successfully "
                f"with {activity_count} activities across {actual_days} days."
            ),
            "instruction": "The itinerary has been generated and will be displayed as interactive cards. "
            "Respond with a SHORT confirmation like: 'Here's your [N]-day itinerary for [destination]!' "
            "Do NOT list activities, days, or any itinerary content — the frontend renders it as cards. "
            "Ask if they'd like any modifications, or if they're ready to proceed with booking.",
        }
    )

    # artifact — full itinerary dict stored on ToolMessage.artifact, never sent to LLM.
    # process_itinerary_messages reads msg.artifact to build the frontend response.
    return content, itinerary_dict


__all__ = [
    "BudgetSnapshot",
    "DayTip",
    "ExpandedContent",
    "GenerateItineraryInput",
    "ItineraryActivity",
    "ItineraryDay",
    "LatLng",
    "LocalExperience",
    "StructuredItineraryResult",
    "generate_itinerary",
]
