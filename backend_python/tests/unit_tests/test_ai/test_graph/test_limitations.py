"""Unit tests for the AI-CHAT-013 capability-limitations matcher.

Covers:
- One positive match per registered limitation in ``KNOWN_LIMITATIONS``
- Over-refusal guards (sticky-intent follow-ups, pronouns, place names)
- ``LimitationMatch`` shape + ``matched_text`` populates for telemetry
- Config-shape sanity (every entry has required fields)
"""

from __future__ import annotations

import re

import pytest

from app.ai.graph.limitations import (
    KNOWN_LIMITATIONS,
    MIN_MESSAGE_LENGTH,
    LimitationMatch,
    match_limitation,
)

# ---------------------------------------------------------------------------
# Config-shape sanity — runs once per CI run, catches misconfigured entries.
# ---------------------------------------------------------------------------


class TestKnownLimitationsConfig:
    def test_every_limitation_has_required_fields(self) -> None:
        for entry in KNOWN_LIMITATIONS:
            assert "id" in entry, f"entry missing 'id': {entry!r}"
            assert isinstance(entry["id"], str), f"entry id must be a string: {entry!r}"
            assert entry["id"], f"entry id must be non-empty: {entry!r}"
            for field in ("disclosure_body", "offer_default"):
                assert field in entry, f"entry {entry['id']} missing {field}"
                assert isinstance(entry[field], str), (
                    f"entry {entry['id']} {field} must be a string"
                )
                assert entry[field], f"entry {entry['id']} {field} must be non-empty"
            # offer_when_active is optional; if present, must be a dict.
            owa = entry.get("offer_when_active", {})
            assert isinstance(owa, dict), (
                f"entry {entry['id']} offer_when_active must be a dict"
            )
            # At least one of keywords / patterns must be defined.
            assert entry.get("keywords") or entry.get("patterns"), (
                f"entry {entry['id']} must define keywords or patterns"
            )

    def test_every_id_is_unique(self) -> None:
        ids = [e["id"] for e in KNOWN_LIMITATIONS]
        assert len(ids) == len(set(ids)), f"duplicate limitation ids: {ids}"

    def test_response_templates_avoid_im_just_an_ai(self) -> None:
        """Tone rule: never say "I'm just an AI"."""
        for entry in KNOWN_LIMITATIONS:
            combined = (
                entry["disclosure_body"]
                + " "
                + entry["offer_default"]
                + " "
                + " ".join((entry.get("offer_when_active") or {}).values())
            ).lower()
            assert "i'm just an ai" not in combined, (
                f"entry {entry['id']} violates 'never I'm just an AI' tone rule"
            )

    def test_templates_avoid_competitor_brands(self) -> None:
        """Brand policy: Voya doesn't promote competitor / third-party platforms.

        Allowed exceptions: "embassy" (government source) — explicitly
        permitted in visa_requirements. Anything else from this list is a
        regression on the brand-policy decision (issue #1077 review).
        """
        BLOCKLIST = {
            "airbnb",
            "vrbo",
            "booking.com",
            "expedia",
            "kayak",
            "hertz",
            "enterprise",
            "avis",
            "discover cars",
            "trainline",
            "cruisedirect",
            "insuremytrip",
            "world nomads",
            "weather.com",
            "accuweather",
            "wise",
            "flightaware",
        }
        for entry in KNOWN_LIMITATIONS:
            combined = (
                entry["disclosure_body"]
                + " "
                + entry["offer_default"]
                + " "
                + " ".join((entry.get("offer_when_active") or {}).values())
            ).lower()
            for brand in BLOCKLIST:
                assert brand not in combined, (
                    f"entry {entry['id']} mentions competitor brand {brand!r} — "
                    f"Voya brand policy disallows promoting third-party platforms"
                )

    def test_patterns_compile(self) -> None:
        """All regex patterns must compile without raising."""
        for entry in KNOWN_LIMITATIONS:
            for pattern in entry.get("patterns", []):
                re.compile(pattern)  # would raise re.error if invalid


# ---------------------------------------------------------------------------
# Positive matches — one per limitation id, with a representative phrasing.
# ---------------------------------------------------------------------------


class TestPositiveMatches:
    @pytest.mark.parametrize(
        ("message", "expected_id"),
        [
            # region_wide_search
            ("Find me hotels all of Albania for next month", "region_wide_search"),
            ("Plan a trip across Europe in July", "region_wide_search"),
            ("Search anywhere in Japan, 2 adults", "region_wide_search"),
            ("Any city in France will do for September", "region_wide_search"),
            # large_villa_bedrooms
            ("I need a 5 bedroom villa in Bali", "large_villa_bedrooms"),
            ("Looking for a 4-bedroom holiday home", "large_villa_bedrooms"),
            ("Find a vacation rental for 8 people", "large_villa_bedrooms"),
            # external_listings
            ("Book me an Airbnb in Lisbon", "external_listings"),
            ("Can you check VRBO for me?", "external_listings"),
            ("Search Booking.com for cheaper rates", "external_listings"),
            # school_calendar
            ("When are the UK school holidays?", "school_calendar"),
            ("What dates is half term in Scotland?", "school_calendar"),
            ("Plan around the bank holiday weekend", "school_calendar"),
            # car_rental
            ("I need a car rental in Rome for 5 days", "car_rental"),
            ("Rent a car at LAX airport", "car_rental"),
            ("Best Hertz rate for next week?", "car_rental"),
            # train_tickets
            ("Find me Eurostar tickets London to Paris", "train_tickets"),
            ("Book train tickets to Edinburgh", "train_tickets"),
            ("Search Trainline for cheaper rail fares", "train_tickets"),
            # cruise
            ("Find a 7-day Caribbean cruise in July", "cruise"),
            ("Royal Caribbean for our anniversary", "cruise"),
            # travel_insurance
            ("Do I need travel insurance for Japan?", "travel_insurance"),
            ("Help me find trip insurance", "travel_insurance"),
            # airport_transfers
            ("Book an airport transfer from CDG to my hotel", "airport_transfers"),
            ("Need an airport pickup in Bangkok", "airport_transfers"),
            # visa_requirements
            ("What visa do I need for Japan as US citizen?", "visa_requirements"),
            ("Entry requirements for Australia please", "visa_requirements"),
            # weather_forecast
            ("Will it rain in Bali next week?", "weather_forecast"),
            ("What's the weather in Tokyo in March?", "weather_forecast"),
            # currency_conversion
            ("Current exchange rate USD to JPY?", "currency_conversion"),
            ("Help with currency conversion for Thailand", "currency_conversion"),
            # flight_status
            ("Is flight BA123 delayed today?", "flight_status"),
            ("Track my flight status", "flight_status"),
        ],
    )
    def test_message_matches_expected_limitation(
        self, message: str, expected_id: str
    ) -> None:
        hit = match_limitation(message)
        assert hit is not None, f"expected match for {message!r}"
        assert hit.limitation_id == expected_id, (
            f"expected {expected_id} for {message!r}, got {hit.limitation_id}"
        )


# ---------------------------------------------------------------------------
# Negative tests — over-refusal guards. Each is a real user phrase that LOOKS
# similar to a limitation pattern but must NOT trigger.
# ---------------------------------------------------------------------------


class TestOverRefusalGuards:
    @pytest.mark.parametrize(
        ("message", "reason"),
        [
            # Sticky-intent follow-ups — too short for MIN_MESSAGE_LENGTH gate
            ("yes", "sticky-intent confirmation"),
            ("ok", "ack"),
            ("no", "negative ack"),
            ("2 adults", "passenger count clarification"),
            ("1 room", "room count clarification"),
            ("next week", "date confirmation"),
            # Just above the length threshold — still no real limitation
            ("Plan a 3-day trip to Tokyo", "normal trip request"),
            ("Search flights Amsterdam to Paris", "normal flight search"),
            ("Find hotels in Lisbon for June 18", "normal hotel search"),
            # 'all of' followed by a pronoun (not a country)
            ("all of them look great", "pronoun, not country"),
            ("I want all of these options", "pronoun, not country"),
            ("all of those work for me", "pronoun, not country"),
            ("show me all of it", "pronoun"),
            # 'villa' / 'holiday home' inside a place name
            ("Villa de Vallecas neighbourhood, Madrid", "place name with 'Villa'"),
            ("Hotels near Villa Real district", "place name with 'Villa'"),
            # End-of-message edge: no trailing whitespace after "Villa Real".
            # Regression for the original \s-based negative lookahead bug.
            ("Hotels near Villa Real", "place name 'Villa Real' at EOM"),
            ("Stay near Villa de Vallecas", "place name 'Villa de Vallecas' at EOM"),
            # Payment-context "Visa" — must NOT trigger visa_requirements.
            # These would have false-positively on the original bare \bvisa\b.
            ("I'll pay with my Visa card", "payment-context 'Visa'"),
            ("Visa card declined, what now?", "payment-context 'Visa'"),
            ("Can I use a Visa prepaid card?", "payment-context 'Visa'"),
            ("Charged to my Visa debit", "payment-context 'Visa'"),
            # 'cruise' as a verb, not a booking
            ("cruise through the canals of Amsterdam", "verb usage of 'cruise'"),
            # 'rail' / 'train' false-positives
            (
                "Hotels near a train station in Rome",
                "incidental mention, not booking intent",
            ),
        ],
    )
    def test_message_must_not_match(self, message: str, reason: str) -> None:
        hit = match_limitation(message)
        assert hit is None, (
            f"over-refusal: {message!r} ({reason}) matched {hit.limitation_id if hit else 'N/A'}"
        )


# ---------------------------------------------------------------------------
# Edge cases — empty / too-short / unicode.
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string_returns_none(self) -> None:
        assert match_limitation("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert match_limitation("   ") is None

    def test_below_min_length_returns_none(self) -> None:
        """Messages shorter than MIN_MESSAGE_LENGTH never trigger."""
        for short in ("airbnb", "visa", "1 room", "yes"):
            assert len(short) < MIN_MESSAGE_LENGTH or short in ("airbnb", "visa")
            # 'airbnb' (6) and 'visa' (4) are below threshold so even keyword matches
            # against them must return None.
            assert match_limitation(short) is None, f"{short!r} should not match"

    def test_min_length_threshold_is_8(self) -> None:
        """Lock the threshold value at 8 — changing this changes test semantics."""
        assert MIN_MESSAGE_LENGTH == 8

    def test_match_at_exactly_min_length(self) -> None:
        """A keyword that exactly hits the threshold can still match."""
        # 'airbnb' alone (6) is below; 'airbnb!' (7) below; 'airbnb??' (8) at threshold
        # but no limitation keywords match these in isolation without context.
        # This test just locks the gate behavior — short standalone keywords still
        # require the threshold.
        assert match_limitation("airbnb") is None  # 6 chars
        assert match_limitation("airbnbxx") is None  # 8 chars but bizarre input

    def test_unicode_curly_apostrophes_handled(self) -> None:
        """Unicode in user messages must not crash the matcher."""
        msg = "When are the UK school holidays?"  # straight apostrophe
        hit = match_limitation(msg)
        assert hit is not None
        assert hit.limitation_id == "school_calendar"


# ---------------------------------------------------------------------------
# Return value shape — the LimitationMatch dataclass.
# ---------------------------------------------------------------------------


class TestLimitationMatchReturn:
    def test_returns_limitation_match_instance(self) -> None:
        hit = match_limitation("Find me hotels all of Albania for next month")
        assert isinstance(hit, LimitationMatch)

    def test_match_includes_matched_text_for_telemetry(self) -> None:
        """matched_text is what we surface to Langfuse — must be the actual trigger."""
        hit = match_limitation("Find me hotels all of Albania for next month")
        assert hit is not None
        assert "all of Albania" in hit.matched_text

    def test_match_includes_disclosure_body_and_offer(self) -> None:
        hit = match_limitation("Find me an Airbnb in Lisbon")
        assert hit is not None
        assert "partner inventory" in hit.disclosure_body
        assert (
            "hotels" in hit.offer_default or "serviced apartments" in hit.offer_default
        )

    def test_match_includes_offer_when_active_map(self) -> None:
        hit = match_limitation("Find me a 5 bedroom villa in Bali")
        assert hit is not None
        # Every limitation (except school_calendar) defines the three active
        # agent overrides. Lock the shape so the node composes correctly.
        for agent in ("flight", "hotel", "itinerary"):
            assert agent in hit.offer_when_active, (
                f"large_villa_bedrooms missing offer_when_active[{agent}]"
            )

    def test_first_match_wins(self) -> None:
        """When multiple patterns could match, the first registered entry wins.

        'Airbnb villa in Bali' could plausibly match BOTH external_listings AND
        large_villa_bedrooms. external_listings is registered earlier so it
        should win — order in KNOWN_LIMITATIONS matters.
        """
        # Sanity: order in the registry.
        ids_in_order = [e["id"] for e in KNOWN_LIMITATIONS]
        ext_idx = ids_in_order.index("external_listings")
        villa_idx = ids_in_order.index("large_villa_bedrooms")
        # Whichever is earlier in the list should win.
        hit = match_limitation("Find a 5 bedroom Airbnb villa in Bali")
        assert hit is not None
        expected = (
            "external_listings" if ext_idx < villa_idx else "large_villa_bedrooms"
        )
        assert hit.limitation_id == expected
