"""Pre-LLM trip-parameter extractor for the itinerary path.

Closes the cold-first-turn gap described in
``docs/PERSONALIZED_ITINERARY_PLAN.md`` step ①: on a brand-new chat the user's
first message contains everything needed (origin, destination, dates,
passengers) — but the itinerary LLM hasn't run yet, so ``shared_context.trip``
is empty and the side-search orchestrator can't fire. This module runs **before**
the itinerary agent dispatches: one small LLM call extracts the candidate
fields, then ``parse_dates`` + ``resolve_airport`` (existing tools) resolve them
to ISO dates + IATA codes ready for the side-searches.

Net cost: ~2-3s on the cold turn. After this node runs, the existing
orchestrator (``itinerary_orchestrator.py``) fires flight + hotel searches in
parallel with the itinerary LLM and finishes inside its ~40-50s window —
matching the doc's "~0s overhead" claim modulo this 2-3s pre-step.

Graceful degradation: if extraction fails (LLM error, ambiguous city,
unparseable dates, etc.) we return an empty dict and let the existing flow
proceed unchanged. Worst case = today's behaviour (itinerary ships, no inline
cards).
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 3 O4 — regex fast-path
# ---------------------------------------------------------------------------
# About ~30% of cold-turn messages take the canonical shape
# *"Plan a 5-day trip to Paris"* / *"5 days in Tokyo"* / *"I want a 3-day trip
# to Rome from London"*. These don't need the small-LLM extraction call — a
# strict regex can pull out (days, destination, optional origin) directly,
# saving ~2-3s on the cold-turn critical path.
#
# Misses (anything with extra date info, vibe phrasing, multi-city, etc.)
# fall through to ``_extract_with_llm`` as before. The regex is intentionally
# conservative — false positives would degrade the LLM-handled cases.
_FAST_PATH_REGEX = re.compile(
    r"""
    ^
    \s*
    (?:plan\s+(?:a\s+|an\s+)?)?                        # "plan a" / "plan an"
    (?:i\s+(?:want|need|would\s+like)\s+(?:a\s+|an\s+)?)?  # "I want a" / "I need a"
    (?P<days>\d{1,3})                                  # 1-3 digit duration
    \s*[-\s]\s*                                        # hyphen or space
    days?                                              # "day" / "days"
    (?:\s+trip)?                                       # optional "trip"
    \s+(?:in|to)\s+
    (?P<dest>[\w'-]+(?:\s+(?!from\b)[\w'-]+){0,3})     # 1-4 word destination; cannot
                                                        # absorb "from" (that starts origin)
    (?:\s+from\s+(?P<origin>[\w'-]+(?:\s+[\w'-]+){0,3}))?  # optional "from <origin>"
    [\s.!?]*
    $
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)


def _is_title_case_chain(s: str) -> bool:
    """True when every whitespace-separated word in ``s`` starts with an
    uppercase letter.  Used to reject lowercase / vague phrases like
    ``"somewhere warm"`` AND to prevent the destination chain from
    accidentally absorbing trailing connective words like ``"in"`` /
    ``"during"`` (as in *"Plan a 5-day trip to Tokyo in June"* — that
    phrase should defer to the LLM so ``parse_dates`` can read "in June").
    """
    return all(word and word[0].isupper() for word in s.split())


def _try_fast_path(message: str) -> TripParamsExtraction | None:
    """Regex fast-path for the canonical cold-turn shape.

    Returns a populated :class:`TripParamsExtraction` (with ``date_expression``
    set to ``"<N> days"`` so ``parse_dates`` handles the duration the same way
    it does for the LLM-extracted case), or ``None`` if the message doesn't
    match the strict shape. ``None`` is the safe signal — caller falls back to
    :func:`_extract_with_llm`.

    Strict acceptance criteria (designed to keep false-positive rate low):
    - Canonical shape only — "Plan a N-day trip to X" / "N days in X" /
      optional "from Y".
    - Destination + optional origin must be Title-Case (every word starts
      with uppercase). This rejects vague phrasing ("somewhere warm"),
      lowercase typing, and prevents the multi-word destination from
      accidentally absorbing connectors like "in" / "during" in phrases
      like "to Tokyo in June".
    """
    if not message:
        return None
    m = _FAST_PATH_REGEX.match(message.strip())
    if not m:
        return None
    days = m.group("days")
    dest = (m.group("dest") or "").strip()
    origin = (m.group("origin") or "").strip() or None
    if not days or not dest:
        return None
    if not _is_title_case_chain(dest):
        return None
    if origin is not None and not _is_title_case_chain(origin):
        return None
    return TripParamsExtraction(
        origin_city=origin,
        destination_city=dest,
        date_expression=f"{days} days",
        adults=None,
        children=None,
        infants=None,
        trip_type=None,
    )


# ---------------------------------------------------------------------------
# #1127 — origin-only follow-up reply detector
# ---------------------------------------------------------------------------
# After ``block_missing_origin`` fires on a cold turn, the agent asks the user
# *"Departing from?"* and the user typically replies with a 1-3 word location
# string ("Dubai", "New York City", "DXB"). The trip-parameter extractor LLM
# sees that bare reply in isolation — no conversation history — and often
# can't tell whether the location is meant as origin or destination. This
# helper treats a location-shaped bare reply as an ORIGIN candidate ONLY when
# the existing trip context shows we're explicitly waiting for origin
# (destination + dates already collected, no ``origin_iata`` yet).
# Determinism comes from the airport DB lookup downstream, NOT from the LLM.
_BARE_LOCATION_REJECT_WORDS: frozenset[str] = frozenset(
    {
        # Pronouns / subject words
        "i",
        "im",
        "we",
        "us",
        "me",
        "my",
        "you",
        "your",
        "our",
        # Common copula / aux verbs
        "am",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        # Prepositions / connectors
        "to",
        "from",
        "in",
        "at",
        "on",
        "for",
        "with",
        "of",
        # Travel verbs / intent
        "going",
        "go",
        "fly",
        "flying",
        "leave",
        "leaving",
        "depart",
        "departing",
        "want",
        "need",
        "would",
        "like",
        "prefer",
        # Articles
        "the",
        "a",
        "an",
        # Conversational acks (still reject so we don't fire on these)
        "yes",
        "yep",
        "yeah",
        "no",
        "nope",
        "ok",
        "okay",
        "sure",
        "thanks",
        "thank",
        "skip",
        "cancel",
        "stop",
        "wait",
        "please",
        # Greetings — common one-word messages we must NOT mistake for cities
        "hello",
        "hi",
        "hey",
        "greetings",
        "morning",
        "evening",
        "afternoon",
        "help",
        # Time references — "later" / "tomorrow" / "soon" / "now" / "next"
        # are often replies to "when?" not "where from?"
        "later",
        "soon",
        "now",
        "tomorrow",
        "today",
        "tonight",
        "next",
        "any",
        "anywhere",
        # Hedging / unclear replies
        "maybe",
        "perhaps",
        "dunno",
        "idk",
        # Location-shaped but ambiguous / not-an-origin
        "home",
        "work",
        "office",
        "everywhere",
        "somewhere",
        # Common booking-flow nouns the user might say bare
        "book",
        "search",
        "find",
        "hotel",
        "hotels",
        "flight",
        "flights",
        "trip",
        "itinerary",
    }
)

# Conservative upper bound on a "short location reply" — longer messages
# are almost always sentences the LLM should interpret. 40 chars covers
# the longest reasonable airport / metro names (e.g.
# "Kuala Lumpur International" = 25, "São Paulo Guarulhos" = 19).
_BARE_LOCATION_MAX_CHARS: int = 40


def _looks_like_bare_location_reply(message: str) -> bool:
    """Heuristic gate for the origin fallback: is this a short location-shaped
    reply that we should hand straight to ``resolve_airport``?

    Conservative on purpose — false positives waste a DB lookup but won't
    break anything (``resolve_airport`` returns ``not_found`` cleanly), while
    false negatives just leave the user waiting on the same prompt for one
    more LLM round-trip.

    Accepts: ``"Dubai"`` · ``"New York"`` · ``"São Paulo"`` · ``"DXB"`` ·
    ``"Kuala Lumpur"`` · ``"Mumbai International"``
    Rejects: ``"yes"`` · ``"I'm in Dubai"`` · ``"flying from Dubai"`` ·
    ``"to Dubai please"`` · long sentences · anything with ``?`` / ``!``.
    """
    if not message:
        return False
    s = message.strip()
    if not s or len(s) > _BARE_LOCATION_MAX_CHARS:
        return False
    if "?" in s or "!" in s:
        return False
    if not s[0].isalpha():
        return False
    words = s.split()
    if not 1 <= len(words) <= 4:
        return False
    # Reject if ANY word is a common conversational / connector word — the
    # presence of those signals a sentence rather than a bare location string.
    for word in words:
        clean = re.sub(r"[^a-zA-Z]", "", word).lower()
        if clean in _BARE_LOCATION_REJECT_WORDS:
            return False
    return True


def _waiting_for_origin(existing_trip: dict[str, Any] | None) -> bool:
    """True when the trip context shows we already collected destination + dates
    but origin still needs resolving — i.e. the ``block_missing_origin`` gate
    or the agent's "Departing from?" question is in flight."""
    if not existing_trip:
        return False
    return bool(
        existing_trip.get("destination")
        and existing_trip.get("departure_date")
        and not existing_trip.get("origin_iata")
    )


# ---------------------------------------------------------------------------
# #1133 follow-up: deterministic duration extraction for the hotel-search gate
# ---------------------------------------------------------------------------
# When the extractor LLM splits a combined date_expression like *"7 day trip
# starting 30 days from now"* into just *"30 days from now"*, ``parse_dates``
# returns only a ``departure_date`` and the hotel side-search silently skips
# because ``_HOTEL_REQUIRED`` needs ``return_date``. This regex recovers the
# duration directly from the user's full message so we can derive
# ``return_date = departure + duration``.
#
# Negative lookahead rejects anchor phrases ("30 days from now", "5 days ago",
# "2 weeks later") — those are NOT durations, they're offsets relative to
# today. Bound: 1-30 (matches generate_itinerary's ``num_days`` cap).
_DURATION_FALLBACK_NUM_WORDS: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
}

_DURATION_FALLBACK_PATTERN = re.compile(
    r"\b(?P<num>\d{1,2}|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|"
    r"a|an)"
    r"\s*[-]?\s*"
    r"(?P<unit>day|week)s?\b"
    # Reject POST-position anchors: "N days from now", "N days ago", etc.
    r"(?!\s+(?:from|ago|later|before|after|since|prior|past|away))",
    re.IGNORECASE,
)

# PRE-position anchor words — when one of these directly precedes the
# matched number, the phrase is an offset / relative anchor ("leaving in
# 5 days", "after 2 weeks", "by 3 days") and NOT a trip-length spec.
# Checked in code rather than as a lookbehind because Python's `re` doesn't
# support variable-width lookbehinds inside one expression.
_DURATION_FALLBACK_ANCHOR_PRE_WORDS: frozenset[str] = frozenset(
    {
        "in",
        "after",
        "before",
        "by",
        "around",
        "about",
        "within",
        "since",
        "from",
    }
)


def _extract_trip_duration_days(message: str) -> int | None:
    """Recover trip duration (inclusive day count) from a free-form message.

    Returns ``None`` when no clear duration is mentioned, or when the match
    looks like a relative anchor ("5 days ago", "3 days from now") rather
    than a trip-length spec. Conservative cap at 30 days matches the
    ``generate_itinerary`` tool's ``num_days`` upper bound.

    Examples:
      "7 day trip"              → 7
      "5-day Tokyo trip"        → 5
      "stay for 10 days"        → 10
      "2 weeks in Bali"         → 14
      "a week in Tokyo"         → 7
      "30 days from now"        → None  (anchor, not duration)
      "5 days ago I went"       → None  (anchor)
      "Plan a trip to Tokyo"    → None  (no duration mentioned)
    """
    if not message:
        return None
    match = _DURATION_FALLBACK_PATTERN.search(message)
    if not match:
        return None
    # Pre-position anchor check: phrases like "in 5 days" / "after 2 weeks"
    # / "by 3 days" are RELATIVE anchors (offset from today), NOT trip
    # duration. The post-position case ("N days from now / ago / later")
    # is handled by the regex's negative lookahead; pre-position has to
    # be checked here because Python's stdlib ``re`` can't combine
    # variable-width lookbehinds inside one pattern cleanly.
    preceding = message[: match.start()].rstrip()
    if preceding:
        last_word = preceding.split()[-1].lower().rstrip(",.;:!?")
        if last_word in _DURATION_FALLBACK_ANCHOR_PRE_WORDS:
            return None
    num_str = match.group("num").lower()
    if num_str.isdigit():
        n = int(num_str)
    else:
        n = _DURATION_FALLBACK_NUM_WORDS.get(num_str)
        if n is None:
            return None
    if match.group("unit").lower() == "week":
        n *= 7
    if not 1 <= n <= 30:
        return None
    return n


def _derive_return_date(departure_iso: str, duration_days: int) -> str | None:
    """Compute ``return_date = departure + (duration - 1)`` (inclusive count).

    Inclusive-day convention matches ``trip_duration_days`` everywhere else:
    "7 day trip starting Jun 1" → return Jun 7 (7 calendar days incl. both
    endpoints). Returns ``None`` on parse failure or non-positive duration.
    """
    if not departure_iso or duration_days < 1:
        return None
    try:
        dep = date.fromisoformat(departure_iso)
    except (TypeError, ValueError):
        return None
    return (dep + timedelta(days=duration_days - 1)).isoformat()


class TripParamsExtraction(BaseModel):
    """Structured extraction of trip parameters from a single user message."""

    origin_city: str | None = Field(
        default=None,
        description="Origin city or airport name the user mentioned (e.g. 'London', 'JFK'). Null if not mentioned.",
    )
    destination_city: str | None = Field(
        default=None,
        description="Destination city or airport name (e.g. 'Paris', 'Tokyo'). Null if not mentioned.",
    )
    date_expression: str | None = Field(
        default=None,
        description=(
            "Natural-language date or date range as the user wrote it. "
            "CRITICAL: include BOTH the departure anchor AND the duration when "
            "present. Examples of CORRECT extraction:\n"
            "  - 'Plan a 7 day trip starting July 1' → '7 day trip starting July 1' "
            "(NOT just 'July 1')\n"
            "  - 'Plan a 5-day Tokyo trip 30 days from now' → '5 day trip 30 days "
            "from now' (NOT just '30 days from now')\n"
            "  - 'Plan a 2 weeks Bali trip in autumn' → '2 weeks in autumn'\n"
            "  - 'June 20-25' → 'June 20 to 25'\n"
            "  - 'next Tuesday for a week' → 'next Tuesday for a week'\n"
            "Splitting the duration off causes the parser to return no return_date, "
            "which breaks downstream hotel/flight search. Always keep them together. "
            "Null if the user did not mention any date or duration."
        ),
    )
    adults: int | None = Field(
        default=None,
        description="Number of adult travellers if stated. Null if not stated.",
    )
    children: int | None = Field(
        default=None,
        description="Number of children if stated. Null if not stated.",
    )
    infants: int | None = Field(
        default=None,
        description="Number of infants if stated. Null if not stated.",
    )
    trip_type: Literal["one-way", "round-trip"] | None = Field(
        default=None,
        description=(
            "'one-way' if the user said so explicitly; 'round-trip' if they said "
            "'round trip' or gave a date range with both ends. Null if unclear."
        ),
    )


_EXTRACTION_SYSTEM_PROMPT = """\
You are a trip-parameter extractor. The user just sent a message asking to plan
a trip. Pull out the fields below from THIS message ONLY — do not invent values.

Required: origin_city, destination_city, date_expression.
Optional: adults, children, infants, trip_type.

Rules:
- Use null for any field the user did not state. NEVER guess.
- Use the EXACT words the user said for ``origin_city`` / ``destination_city``
  (e.g. "London" not "LHR"; "Costa Rica" not "San Jose"). A later tool resolves
  these to IATA codes.
- **IMPORTANT — country-only origins still count.** When the user says only a
  country / region (e.g. "from the US", "flying from UK", "from India") with
  no specific city, ALWAYS extract that label as ``origin_city`` (including
  the article: "the US", "the UK"). A downstream step uses Google Geocoding
  to detect that the value resolves to a country and asks the user for a
  specific departure city. If you return null here, that whole disambiguation
  pipeline is bypassed and the user gets a worse experience. Never null
  origin_city just because the user was vague — preserve their exact wording.
- ``date_expression`` is the natural-language date phrase the user wrote — keep
  it verbatim so the date-parsing tool can interpret it (handles "next week",
  "June 20-25", "5 days in autumn", etc.).
- **CRITICAL — combine duration with the anchor date in ONE date_expression.**
  When the user mentions BOTH a duration AND a departure / anchor date, return
  the combined phrase, NOT either half:
    "Plan a 7 day trip starting 30 days from now" → "7 day trip starting 30 days from now"
    "5-day Tokyo trip in June"                    → "5 day trip in June"
    "2 weeks in Bali starting Jul 1"              → "2 weeks starting Jul 1"
  Splitting them ("30 days from now" alone) makes the parser return only a
  departure date with no return_date, which silently breaks downstream
  hotel/flight side-search.
- Treat "2 pax", "couple", "two of us", "we" as adults=2; "just me", "solo",
  "I" as adults=1. Treat ambiguous phrasing as null (let the agent ask).
- "round trip" / "return" / a date RANGE → trip_type="round-trip". Explicit
  "one way" / "oneway" → trip_type="one-way". Otherwise null.

Return null fields when in doubt — the downstream flow handles missing data
gracefully. False positives are worse than missing values.
"""


async def _extract_with_llm(message: str) -> TripParamsExtraction:
    """One LLM call returning structured trip parameters.

    Uses the small/fast model configured for ``tool_trip_extraction`` (falls
    back to the supervisor model if unconfigured) so this stays cheap on the
    cold-turn latency budget.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.ai.graph.llm_factory import create_llm

    try:
        llm = create_llm("tool_trip_extraction", temperature=0.0)
    except (KeyError, ValueError):
        # No dedicated config — reuse the supervisor's lightweight model.
        llm = create_llm("supervisor", temperature=0.0)

    structured = llm.with_structured_output(TripParamsExtraction)
    result = await structured.ainvoke(
        [
            SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
    )
    # ``with_structured_output`` returns the pydantic model directly (or a
    # dict in some provider paths); normalize to the model for type safety.
    if isinstance(result, dict):
        return TripParamsExtraction(**result)
    if isinstance(result, TripParamsExtraction):
        return result
    # Some providers return a generic BaseModel — round-trip through dict.
    return TripParamsExtraction(**result.model_dump())


async def _resolve_airport(city: str, role: str) -> dict[str, Any] | None:
    """Call ``resolve_airport`` directly (no agent loop).

    Returns the tool's result dict on success / disambiguation / not_found, or
    None on exception. Caller decides what to do with each status.
    """
    try:
        from app.ai.graph.tools.airport import resolve_airport

        return await resolve_airport.ainvoke({"query": city, "role": role})
    except Exception:
        logger.warning(
            "pre_resolve: resolve_airport(%r, role=%s) raised",
            city,
            role,
            exc_info=True,
        )
        return None


async def _parse_dates(date_expression: str) -> dict[str, Any] | None:
    """Call ``parse_dates`` directly (no agent loop)."""
    try:
        from app.ai.graph.tools.dates import parse_dates

        return await parse_dates.ainvoke({"text": date_expression})
    except Exception:
        logger.warning(
            "pre_resolve: parse_dates(%r) raised", date_expression, exc_info=True
        )
        return None


def _is_resolved(airport_result: dict[str, Any] | None) -> bool:
    """``resolve_airport`` is usable only when status='resolved'.

    ``needs_disambiguation`` and ``not_found`` mean the user has to clarify;
    in that case we leave the IATA field empty and let the itinerary agent
    do the resolution as it does today.
    """
    if airport_result is None:
        return False
    return airport_result.get("status") == "resolved"


async def _is_country_only(value: str) -> bool:
    """Geocoder-based check: does ``value`` resolve to a country, not a city?

    Uses Google Geocoding's top-level ``types`` field — the documented
    disambiguation surface for this question. A city geocode returns
    ``["locality", "political"]``; a country returns
    ``["country", "political"]``.

    We use ``GeocodingService.get_location_types`` rather than
    ``geocode_city`` because the latter filters out results that lack a
    ``locality`` component — exactly the case we need to detect.

    The geocoder normalises spelling variants natively — "the US",
    "U.S.", "USA", "United States", and "Estados Unidos" all resolve
    to the same country result. That's why this approach replaced the
    hardcoded English-only country list (#1105).

    Returns False on any failure (no API key, network, quota, no
    results, or non-country type). False is the safe default — the
    caller's downstream flow handles missing data without breaking.
    """
    if not value or not value.strip():
        return False
    try:
        from app.shared.geocoding import GeocodingService

        types = await GeocodingService().get_location_types(value)
    except Exception:
        logger.warning(
            "pre_resolve: country-check geocode failed for value=%r",
            value,
            exc_info=True,
        )
        return False

    return "country" in types and "locality" not in types


# Backwards-compatible alias — used by tests and previously by the origin
# side of ``extract_and_resolve``. New code should call ``_is_country_only``
# directly so the same helper covers origin and destination uniformly.
_is_origin_country_only = _is_country_only


async def _is_destination_country_only(destination: str) -> bool:
    """Geocoder country-check for the destination side (#1127).

    Same logic as :func:`_is_country_only`; named distinctly so callers and
    test mocks can target ``destination`` vs ``origin`` independently — the
    two flows treat a country result very differently (origin → block + ask
    for a city; destination → resolve a tourist hub for the side-searches
    while keeping the country label on the itinerary itself).
    """
    return await _is_country_only(destination)


async def extract_and_resolve(
    message: str,
    existing_trip: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract trip params from the user message + resolve to IATA codes / ISO dates.

    Returns a dict shaped for merging into ``shared_context.trip``. Keys that
    could not be resolved are omitted (NOT set to None) so a merge into the
    existing trip dict doesn't overwrite previously-collected values.

    ``existing_trip`` is an optional snapshot of the in-progress trip context
    used to skip redundant resolution work: when the extracted origin /
    destination matches one already paired with an ``*_iata`` value, the
    matching ``resolve_airport`` call AND the country-check geocode are
    short-circuited. The caller still re-runs ``parse_dates`` per turn
    because the user may refine dates mid-conversation.

    Possible keys in the returned dict:
    - ``origin`` (str): city name as user wrote it (e.g. "London")
    - ``origin_iata`` (str): IATA from resolve_airport (e.g. "LHR")
    - ``destination`` (str): city name (e.g. "Paris")
    - ``destination_iata`` (str): IATA (e.g. "CDG")
    - ``destination_country`` (str): country code from resolve_airport
    - ``departure_date`` (str): ISO date
    - ``return_date`` (str): ISO date (only when parse_dates returned both)
    - ``adults`` / ``children`` / ``infants`` (int)
    - ``trip_type`` (str): "one-way" or "round-trip"

    Empty dict is a valid response — caller treats it as "nothing extracted,
    fall back to today's behaviour".
    """
    if not message or not message.strip():
        return {}

    existing_trip = existing_trip or {}

    # 1) Extract candidate fields from the user message.
    # Phase 3 O4: try the regex fast-path first ("Plan a N-day trip to X").
    # Saves the ~2-3s extraction-LLM call on ~30% of cold-turns. On any
    # miss the function returns None and we fall back to the LLM.
    extracted = _try_fast_path(message)
    if extracted is not None:
        logger.info(
            "pre_resolve: fast-path matched — dest=%r origin=%r days=%r "
            "(skipped extraction LLM)",
            extracted.destination_city,
            extracted.origin_city,
            extracted.date_expression,
        )
    elif _waiting_for_origin(existing_trip) and _looks_like_bare_location_reply(
        message
    ):
        # #1127: dedicated fast-path for the "Departing from?" follow-up
        # reply. We're explicitly waiting for origin (destination + dates
        # already in trip_ctx), the user reply is location-shaped — so skip
        # the extractor LLM entirely and hand the bare string straight to
        # ``resolve_airport`` downstream. Resolution is deterministic via the
        # mwgg/Airports DB; if it fails, the existing `block_missing_origin`
        # gate re-fires and the agent asks again.
        extracted = TripParamsExtraction(
            origin_city=message.strip(),
            destination_city=None,
            date_expression=None,
            adults=None,
            children=None,
            infants=None,
            trip_type=None,
        )
        logger.info(
            "pre_resolve: origin-fallback fired — treating bare reply %r as "
            "origin candidate (skipped extraction LLM)",
            message.strip(),
        )
    else:
        try:
            extracted = await _extract_with_llm(message)
        except Exception:
            logger.warning(
                "pre_resolve: extraction LLM call failed for message=%r",
                message[:200],
                exc_info=True,
            )
            return {}

        # Post-LLM origin fallback: if the LLM extracted other fields but
        # missed origin while we're waiting for it, fold the bare reply in
        # as an origin candidate.  Covers cases like "Dubai, leaving July 20"
        # where the LLM picks up the date but not the location.
        if (
            not extracted.origin_city
            and _waiting_for_origin(existing_trip)
            and _looks_like_bare_location_reply(message)
        ):
            extracted = extracted.model_copy(update={"origin_city": message.strip()})
            logger.info(
                "pre_resolve: post-LLM origin-fallback fired — folded %r in "
                "as origin candidate",
                message.strip(),
            )

        logger.info(
            "pre_resolve: extracted origin=%s destination=%s dates=%s "
            "adults=%s children=%s trip_type=%s",
            extracted.origin_city,
            extracted.destination_city,
            extracted.date_expression,
            extracted.adults,
            extracted.children,
            extracted.trip_type,
        )

    # 2) Run parse_dates + resolve_airport + origin country-check in parallel
    #    — they're independent so no point sequencing them.
    #
    #    Skip the airport + country-check work for origin / destination
    #    cities that the existing trip context already resolved to an IATA
    #    (case-insensitive name match). This avoids a redundant
    #    resolve_airport + Google Geocoding call on every follow-up turn
    #    once the city is locked in.
    def _already_resolved(name: str | None, iata_key: str) -> bool:
        if not name:
            return False
        cached_name = existing_trip.get(iata_key.removesuffix("_iata"))
        cached_iata = existing_trip.get(iata_key)
        return bool(
            cached_iata
            and isinstance(cached_name, str)
            and cached_name.strip().casefold() == name.strip().casefold()
        )

    origin_already_resolved = _already_resolved(extracted.origin_city, "origin_iata")
    dest_already_resolved = _already_resolved(
        extracted.destination_city, "destination_iata"
    )

    parse_task = (
        asyncio.create_task(_parse_dates(extracted.date_expression))
        if extracted.date_expression
        else None
    )
    origin_task = (
        asyncio.create_task(_resolve_airport(extracted.origin_city, role="origin"))
        if extracted.origin_city and not origin_already_resolved
        else None
    )
    dest_task = (
        asyncio.create_task(
            _resolve_airport(extracted.destination_city, role="destination")
        )
        if extracted.destination_city and not dest_already_resolved
        else None
    )
    # Country-check via geocoder (#1105): when the user said only a country
    # name as origin ("the US"), Google Geocoding returns
    # ``result_types=["country", "political"]`` for the geocode. A specific
    # city returns ``["locality", "political"]``. Cache the boolean on
    # ``shared_context.trip`` so the supervisor can inject a BLOCKING ASK
    # without re-geocoding on every subsequent turn. Once ``origin_iata``
    # is set the answer is settled (the city resolved) — skip the call.
    origin_country_task = (
        asyncio.create_task(_is_country_only(extracted.origin_city))
        if extracted.origin_city and not origin_already_resolved
        else None
    )
    # #1127: same check on the destination side. When the user names a
    # country ("Montenegro"), ``resolve_airport`` often fuzzy-matches the
    # country name to an unrelated airport (in dev, "Montenegro" → QGF in
    # Brazil) — we use this flag to discard that bogus IATA and resolve
    # the country's tourist hub instead. Skip when the destination already
    # has a resolved IATA on a prior turn.
    dest_country_task = (
        asyncio.create_task(_is_destination_country_only(extracted.destination_city))
        if extracted.destination_city and not dest_already_resolved
        else None
    )

    parse_result = await parse_task if parse_task else None
    origin_result = await origin_task if origin_task else None
    dest_result = await dest_task if dest_task else None
    origin_is_country = await origin_country_task if origin_country_task else False
    destination_is_country = await dest_country_task if dest_country_task else False

    # 3) Assemble the trip_ctx-shaped dict. Only include keys we successfully
    #    resolved — missing values stay absent so the existing trip_ctx merge
    #    doesn't accidentally null-out fields the LLM picks up later.
    trip_update: dict[str, Any] = {}

    if extracted.origin_city:
        trip_update["origin"] = extracted.origin_city
        trip_update["origin_is_country"] = origin_is_country
    if extracted.destination_city:
        trip_update["destination"] = extracted.destination_city

    if _is_resolved(origin_result):
        assert origin_result is not None  # for mypy
        iata = origin_result.get("iata")
        if iata:
            trip_update["origin_iata"] = iata

    if _is_resolved(dest_result) and not destination_is_country:
        assert dest_result is not None  # for mypy
        iata = dest_result.get("iata")
        if iata:
            trip_update["destination_iata"] = iata
        country = dest_result.get("country")
        if country:
            trip_update["destination_country"] = country

    # #1127: destination resolved to a country, not a city. The airport
    # resolver may have produced a wrong IATA via fuzzy-matching the country
    # name (e.g. "Montenegro" → QGF in Brazil) — discard it and resolve the
    # country's tourist hub instead. The original ``destination`` label
    # stays put so the itinerary LLM still produces a multi-city
    # country-wide plan; the new ``destination_search_city`` is what
    # ``_safe_hotel_search`` / ``_safe_flight_search`` consume.
    if destination_is_country and extracted.destination_city:
        from app.ai.graph.country_to_city import lookup_country_tourist_hubs

        trip_update["destination_is_country"] = True
        hubs_result = lookup_country_tourist_hubs(extracted.destination_city)
        if hubs_result is not None:
            hub_country_name, hubs = hubs_result
            primary_city, primary_iata = hubs[0]
            # Primary hub — backward-compat fields used by single-hub code paths.
            trip_update["destination_search_city"] = primary_city
            trip_update["destination_iata"] = primary_iata
            trip_update["destination_country"] = hub_country_name
            # Full hub list for multi-hub side-searches (#1152).
            trip_update["destination_hub_list"] = [
                {"city": city, "iata": iata} for city, iata in hubs
            ]
            logger.info(
                "pre_resolve: destination %r is a country — using hub %r "
                "(IATA=%s) for side-searches; %d hub(s) total: %s",
                extracted.destination_city,
                primary_city,
                primary_iata,
                len(hubs),
                [f"{c}/{i}" for c, i in hubs],
            )
        else:
            # Long-tail country not in the static map. Drop any IATA/country
            # the resolver may have set (likely a bad fuzzy match) so the
            # side-searches skip silently instead of hitting wrong airports.
            trip_update.pop("destination_iata", None)
            trip_update.pop("destination_country", None)
            logger.info(
                "pre_resolve: destination %r is a country but has no static "
                "tourist-hub mapping — side-searches will skip",
                extracted.destination_city,
            )

    if parse_result and not parse_result.get("error"):
        dep = parse_result.get("departure_date")
        ret = parse_result.get("return_date")
        duration = parse_result.get("trip_duration_days")
        if dep:
            trip_update["departure_date"] = dep
        if ret:
            trip_update["return_date"] = ret
        if duration:
            trip_update["trip_duration_days"] = duration

    # #1133 follow-up: deterministic duration fallback. The extractor LLM
    # sometimes drops the duration ("7 day trip") from the date_expression
    # and only forwards the anchor ("30 days from now") to parse_dates,
    # which then returns no return_date / no trip_duration_days. Without
    # ``return_date`` the hotel side-search skips ("missing required
    # fields") even though the user clearly stated a trip length.
    #
    # Recover by regex-scanning the user's full message for "<N> days/weeks"
    # phrases (rejecting anchor phrases like "30 days from now") and
    # deriving ``return_date = departure + duration - 1``. Acts as a
    # belt-and-suspenders next to the tightened extractor prompt.
    if (
        "departure_date" in trip_update
        and "return_date" not in trip_update
        and "trip_duration_days" not in trip_update
    ):
        fallback_days = _extract_trip_duration_days(message)
        if fallback_days:
            derived = _derive_return_date(trip_update["departure_date"], fallback_days)
            if derived:
                trip_update["return_date"] = derived
                trip_update["trip_duration_days"] = fallback_days
                logger.info(
                    "pre_resolve: duration-fallback fired — extracted %d days "
                    "from message, derived return_date=%s",
                    fallback_days,
                    derived,
                )

    if extracted.adults is not None:
        trip_update["adults"] = extracted.adults
    if extracted.children is not None:
        trip_update["children"] = extracted.children
    if extracted.infants is not None:
        trip_update["infants"] = extracted.infants
    if extracted.trip_type is not None:
        trip_update["trip_type"] = extracted.trip_type

    logger.info(
        "pre_resolve: produced trip_update keys=%s",
        sorted(trip_update.keys()),
    )
    return trip_update


__all__ = ["TripParamsExtraction", "extract_and_resolve"]
