"""Known-limitation registry for proactive capability disclosure (AI-CHAT-013).

Each entry describes a class of user request Voya cannot fulfil today and the
response the supervisor should return when the user's message matches it.

Response shape
--------------
Every entry splits the user-facing response into two pieces:

- ``disclosure_body`` — what Voya can't do (one short sentence)
- ``offer_default`` — the question / next step when no agent is mid-flow
- ``offer_when_active`` — optional dict keyed by active agent name
  (``flight`` / ``hotel`` / ``itinerary`` / ``general``) giving a context-aware
  alternative that names BOTH the user's current flow and the limitation's
  fallback in a single question.

The graph node assembles ``f"{disclosure_body} {offer}"`` — one paragraph,
one question, no `\\n\\n`-split robot feel.

Brand policy
------------
Voya does not promote competitor or third-party booking platforms in its
disclosure text. Generic references ("a vacation-rental site", "your bank's
app", "the embassy site") are fine; named competitors are not.

Matching strategy
-----------------
``match_limitation`` is invoked by ``capability_check`` BEFORE
``route_or_classify``. Two-stage match for cheap rejection of unrelated
messages:

1. ``keywords`` — fast substring check (``str.lower()``). If none hit, skip.
2. ``patterns`` — regex pass, only if step 1 matched (or no keywords defined).

Tone rules baked into every template
------------------------------------
- One apology max (never three).
- Never say "I'm just an AI" — name the specific capability gap.
- Always pair the limitation with what Voya CAN do, when possible.
- Don't name competitors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MIN_MESSAGE_LENGTH = 8


@dataclass(frozen=True)
class LimitationMatch:
    """Result of a successful limitation match."""

    limitation_id: str
    matched_text: str  # for telemetry / debugging
    disclosure_body: str
    offer_default: str
    offer_when_active: dict[str, str]


KNOWN_LIMITATIONS: list[dict[str, Any]] = [
    {
        "id": "region_wide_search",
        "patterns": [
            r"\b(?:all|whole|entire) of (?-i:[A-Z])[a-zA-Z]+",
            r"\bacross (?:the )?(?-i:[A-Z])[a-zA-Z]+",
            r"\banywhere in (?-i:[A-Z])[a-zA-Z]+",
            r"\bany city (?:in|of) (?-i:[A-Z])[a-zA-Z]+",
        ],
        "disclosure_body": (
            "Voya searches one city at a time — country-wide or region-wide "
            "search isn't supported yet."
        ),
        "offer_default": (
            "Want me to suggest a specific starting city, or give me 2-3 cities "
            "and I'll compare them?"
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue with your itinerary, or pick a specific "
                "city and search there?"
            ),
            "hotel": (
                "Want me to continue your hotel search in one specific city, "
                "or compare 2-3 you have in mind?"
            ),
            "flight": ("Want me to continue your flight search to a specific city?"),
        },
    },
    {
        "id": "large_villa_bedrooms",
        "keywords": [
            "villa",
            "bedroom",
            "holiday home",
            "vacation rental",
            "private rental",
        ],
        # The negative lookahead uses \b (word boundary) instead of \s
        # (whitespace) so it correctly excludes "Villa Real" / "Villa de
        # Vallecas" even at end-of-message where there's no trailing space.
        "patterns": [
            r"\b\d+\+?\s?[-]?\s?bedrooms?\b",
            r"(?:^|\W)villa(?!\s*(?:de|real)\b)",
            r"\bholiday home\b",
            r"\bvacation rental\b",
            r"\bprivate rental\b",
        ],
        "disclosure_body": (
            "Voya doesn't have 4+ bedroom villas or holiday-rental inventory yet."
        ),
        "offer_default": (
            "I can search standard hotel rooms (up to 5 rooms) for the group — "
            "want me to do that?"
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary, or search standard hotel "
                "rooms for the group?"
            ),
            "hotel": (
                "Want me to keep searching, but with standard hotel rooms "
                "(up to 5 rooms)?"
            ),
            "flight": (
                "Want me to continue your flight search? I can pair it with "
                "standard hotel rooms after."
            ),
        },
    },
    {
        "id": "external_listings",
        "keywords": ["airbnb", "vrbo", "booking.com", "expedia", "kayak", "agoda"],
        "patterns": [
            r"\bairbnb\b",
            r"\bvrbo\b",
            r"\bbooking\.com\b",
            r"\bexpedia\b",
            r"\bkayak\b",
            r"\bagoda\b",
        ],
        "disclosure_body": (
            "Voya only books partner inventory — third-party listings from "
            "other platforms aren't available here."
        ),
        "offer_default": (
            "Want me to search hotels and serviced apartments for the same "
            "dates instead?"
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary, or search hotels and "
                "serviced apartments for the same dates?"
            ),
            "hotel": ("Want me to keep searching standard hotels for the same dates?"),
            "flight": (
                "Want me to continue your flight search? I can pair it with "
                "Voya hotels after."
            ),
        },
    },
    {
        "id": "school_calendar",
        "keywords": ["school holiday", "half term", "school break", "bank holiday"],
        "patterns": [
            r"\bschool holidays?\b",
            r"\bhalf term\b",
            r"\bschool break\b",
            r"\bbank holidays?\b",
            r"\bschool calendar\b",
        ],
        "disclosure_body": (
            "Voya doesn't have school-calendar or public-holiday data — "
            "UK summer school holidays roughly run mid-July to early September."
        ),
        "offer_default": ("If you tell me a specific date range, I'll plan around it."),
        # School calendar deliberately has no per-active-agent override —
        # the default already covers the resume hint ("tell me a date range").
        "offer_when_active": {},
    },
    {
        "id": "car_rental",
        "keywords": [
            "car rental",
            "rent a car",
            "rental car",
            "hertz",
            "enterprise rent",
            "avis",
        ],
        "patterns": [
            r"\bcar rentals?\b",
            r"\brent a car\b",
            r"\brental car\b",
            r"\b(?:hertz|enterprise|avis|sixt|europcar)\b",
        ],
        "disclosure_body": (
            "Voya plans flights, hotels, and day-by-day itineraries — "
            "car rentals aren't part of that yet."
        ),
        "offer_default": (
            "Want me to plan the rest of the trip and add a 'pick up rental "
            "car' note for Day 1?"
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary and add a 'pick up rental "
                "car' note for Day 1?"
            ),
            "hotel": (
                "Want me to continue your hotel search? You can sort the car "
                "rental separately."
            ),
            "flight": (
                "Want me to continue your flight search? You can sort the car "
                "rental separately."
            ),
        },
    },
    {
        "id": "train_tickets",
        "keywords": ["train ticket", "rail ticket", "eurostar", "amtrak", "trainline"],
        "patterns": [
            r"\btrain tickets?\b",
            r"\brail tickets?\b",
            r"\b(?:eurostar|amtrak|trainline|sncf|deutsche bahn)\b",
        ],
        "disclosure_body": (
            "Voya only books flights — train and rail tickets aren't supported."
        ),
        "offer_default": ("Want me to plan a flight to the nearest airport instead?"),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary with the flight option "
                "I'd already lined up?"
            ),
            "hotel": ("Want me to continue your hotel search?"),
            "flight": ("Want me to continue your flight search?"),
        },
    },
    {
        "id": "cruise",
        "keywords": ["cruise", "royal caribbean", "carnival cruise"],
        # Negative lookahead covers the common verb-usage phrasings:
        # "cruise through/past/along/around the canals/streets/coast" etc.
        # If a verb usage we haven't catalogued slips through, the matched
        # text gets surfaced in telemetry for follow-up.
        "patterns": [
            r"\bcruises?\b(?!\s+(?:through|past|along|around|down|up))",
            r"\b(?:royal caribbean|carnival cruise|norwegian cruise|disney cruise)\b",
        ],
        "disclosure_body": (
            "Voya plans land-based trips and flights — cruises aren't part of "
            "what I book."
        ),
        "offer_default": (
            "Want me to plan a land-based trip to one of the cruise stops instead?"
        ),
        "offer_when_active": {
            "itinerary": ("Want me to continue with your land-based itinerary?"),
            "hotel": (
                "Want me to continue your hotel search at one of the port cities?"
            ),
            "flight": (
                "Want me to continue your flight search to the embarkation city?"
            ),
        },
    },
    {
        "id": "travel_insurance",
        "keywords": ["travel insurance", "trip insurance", "travel coverage"],
        "patterns": [
            r"\btravel insurance\b",
            r"\btrip insurance\b",
            r"\btravel coverage\b",
        ],
        "disclosure_body": (
            "Voya doesn't sell travel insurance — that's outside what I do."
        ),
        "offer_default": (
            "I can still plan the trip itself — insurance you'll need to "
            "arrange separately before you travel."
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary? Insurance you'll sort "
                "separately before you travel."
            ),
            "hotel": (
                "Want me to continue your hotel search? Insurance you'll "
                "sort separately."
            ),
            "flight": (
                "Want me to continue your flight search? Insurance you'll "
                "sort separately."
            ),
        },
    },
    {
        "id": "airport_transfers",
        "keywords": ["airport transfer", "airport pickup", "airport taxi"],
        "patterns": [
            r"\bairport transfers?\b",
            r"\bairport pickups?\b",
            r"\b(?:taxi|uber|lyft) from (?:the )?airport\b",
            r"\bpickup from (?:the )?airport\b",
        ],
        "disclosure_body": ("Voya doesn't book airport transfers."),
        "offer_default": (
            "Want me to add a 'plan your transfer' note to your itinerary's Day 1?"
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary and add a 'plan your "
                "transfer' note for Day 1?"
            ),
            "hotel": ("Want me to continue your hotel search?"),
            "flight": ("Want me to continue your flight search?"),
        },
    },
    {
        "id": "visa_requirements",
        "keywords": ["visa", "passport requirement", "entry requirement", "embassy"],
        # The bare \bvisa\b pattern would false-positive on payment phrasing
        # ("pay with Visa", "Visa card declined") — interrupting a live
        # booking flow with an unrelated disclosure is worse than missing a
        # genuine visa question. Require document-context phrasing instead.
        "patterns": [
            r"\bdo i need (?:a )?visa\b",
            r"\bneed (?:a )?visa\b",
            r"\bvisa requirements?\b",
            r"\bvisa rules?\b",
            r"\bvisa polic(?:y|ies)\b",
            r"\bvisa-free\b",
            r"\bvisa-on-arrival\b",
            r"\bwhat['']?s? the visa\b",
            r"\bwhat (?:kind of |type of )?visa\b",
            r"\bvisas? (?:for|to enter|to visit|required)\b",
            r"\bpassport requirements?\b",
            r"\bentry requirements?\b",
        ],
        "disclosure_body": (
            "Voya doesn't check live visa or entry requirements — those "
            "change too often for me to keep accurate. Check the destination "
            "country's official embassy site."
        ),
        "offer_default": (
            "I can still plan the trip — visa requirements are something "
            "you'll need to verify on your own before you travel."
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary? Visa requirements you'll "
                "need to verify on your own."
            ),
            "hotel": (
                "Want me to continue your hotel search? Visa requirements "
                "you'll need to verify on your own."
            ),
            "flight": (
                "Want me to continue your flight search? Visa requirements "
                "you'll need to verify on your own."
            ),
        },
    },
    {
        "id": "weather_forecast",
        # Tightened from the previous keyword list — bare "rain" / "climate"
        # / "temperature" matched too many unrelated substrings (rainforest,
        # raincoat, climate change, room temperature). Phrase-keywords keep
        # the regex stage entry low without false-triggering.
        "keywords": [
            "weather",
            "forecast",
            "will it rain",
            "temperature in",
            "climate in",
        ],
        "patterns": [
            r"\bweather forecast\b",
            r"\bwill it (?:rain|snow)\b",
            r"\bwhat'?s the weather\b",
            r"\btemperature in [A-Z][a-zA-Z]+",
        ],
        "disclosure_body": (
            "Voya doesn't have live weather data — your usual weather app "
            "will have the forecast."
        ),
        "offer_default": (
            "I can plan around a season if you tell me what you're after "
            "(warm beach / cool city / ski)."
        ),
        "offer_when_active": {
            "itinerary": ("Want me to continue your itinerary?"),
            "hotel": ("Want me to continue your hotel search?"),
            "flight": ("Want me to continue your flight search?"),
        },
    },
    {
        "id": "currency_conversion",
        "keywords": [
            "exchange rate",
            "currency conversion",
            "convert to usd",
            "convert to eur",
        ],
        "patterns": [
            r"\bexchange rate\b",
            r"\bcurrency conversion\b",
            r"\bconvert .{1,30}? (?:usd|eur|gbp|jpy)\b",
        ],
        "disclosure_body": (
            "Voya doesn't have live exchange rates — check your bank's app "
            "for an up-to-date conversion."
        ),
        "offer_default": (
            "My budgets are estimates in USD — happy to recalculate if you "
            "tell me a target currency."
        ),
        "offer_when_active": {
            "itinerary": (
                "Want me to continue your itinerary in USD, or recalculate "
                "in another currency?"
            ),
            "hotel": ("Want me to continue your hotel search in USD?"),
            "flight": ("Want me to continue your flight search in USD?"),
        },
    },
    {
        "id": "flight_status",
        "keywords": [
            "flight status",
            "delayed",
            "track flight",
            "flight tracker",
        ],
        "patterns": [
            r"\bflight status\b",
            r"\bis (?:flight )?[A-Za-z]+\s?\d+ delayed\b",
            r"\bflight\s+[A-Za-z]+\s?\d+\s+delayed\b",
            r"\btrack (?:my )?flight\b",
            r"\bflight tracker\b",
        ],
        "disclosure_body": (
            "Voya doesn't track live flight status or delays — your airline's "
            "own app or boarding pass will have real-time gate info."
        ),
        "offer_default": ("Want me to help with something else for the trip?"),
        "offer_when_active": {
            "itinerary": ("Want me to continue your itinerary?"),
            "hotel": ("Want me to continue your hotel search?"),
            "flight": ("Want me to continue your flight search?"),
        },
    },
]


# Pre-compile patterns at module import.
_COMPILED: list[dict[str, Any]] = []
for _entry in KNOWN_LIMITATIONS:
    _COMPILED.append(
        {
            "id": _entry["id"],
            "keywords": tuple(k.lower() for k in _entry.get("keywords", [])),
            "patterns": [
                re.compile(p, re.IGNORECASE) for p in _entry.get("patterns", [])
            ],
            "disclosure_body": _entry["disclosure_body"],
            "offer_default": _entry["offer_default"],
            "offer_when_active": _entry.get("offer_when_active", {}),
        }
    )


def match_limitation(user_message: str) -> LimitationMatch | None:
    """Return the first matching limitation, or None.

    Pure-Python regex/keyword matcher — no LLM call, runs in microseconds.

    Args:
        user_message: Raw user text. Patterns are compiled with
            ``re.IGNORECASE``; keywords are compared against
            ``user_message.lower()``.

    Returns:
        ``LimitationMatch`` (frozen dataclass) on first hit, or ``None``.
        First-match-wins — order ``KNOWN_LIMITATIONS`` from most to least
        specific.
    """
    if not user_message or len(user_message) < MIN_MESSAGE_LENGTH:
        return None

    lower = user_message.lower()

    for entry in _COMPILED:
        if entry["keywords"]:
            if not any(kw in lower for kw in entry["keywords"]):
                continue
            if not entry["patterns"]:
                return LimitationMatch(
                    limitation_id=entry["id"],
                    matched_text=next(kw for kw in entry["keywords"] if kw in lower),
                    disclosure_body=entry["disclosure_body"],
                    offer_default=entry["offer_default"],
                    offer_when_active=entry["offer_when_active"],
                )

        for pattern in entry["patterns"]:
            m = pattern.search(user_message)
            if m:
                return LimitationMatch(
                    limitation_id=entry["id"],
                    matched_text=m.group(0),
                    disclosure_body=entry["disclosure_body"],
                    offer_default=entry["offer_default"],
                    offer_when_active=entry["offer_when_active"],
                )

    return None


__all__ = [
    "KNOWN_LIMITATIONS",
    "MIN_MESSAGE_LENGTH",
    "LimitationMatch",
    "match_limitation",
]
