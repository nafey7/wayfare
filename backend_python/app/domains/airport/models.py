"""Airport domain models for resolution and disambiguation.

This module defines the core data structures for airport resolution:
- Airport: Represents a single airport with IATA/ICAO codes and location
- AirportResolution: Result of resolving user input to airport(s)
- AirportOption: A disambiguation option when multiple interpretations exist
- ResolveContext: Context hints for resolution (country, preferences)
- DisambiguationType: Types of disambiguation scenarios

Usage:
    from app.domains.airport.models import Airport, AirportResolution

    # After resolving "Birmingham"
    resolution = AirportResolution(
        status="needs_disambiguation",
        disambiguation_type=DisambiguationType.MULTI_CITY,
        options=[...],
        suggested_prompt="Which Birmingham did you mean?..."
    )
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class DisambiguationType(StrEnum):
    """Types of disambiguation scenarios.

    MULTI_CITY: Same city name exists in multiple countries
        Example: "Birmingham" → UK (BHX) or USA (BHM)

    MULTI_AIRPORT: City has multiple airports
        Example: "London" → LHR, LGW, STN, LTN, LCY

    CODE_VS_CITY: Input matches both IATA code AND city name
        Example: "GOA" → IATA code for Genoa OR city Goa, India
    """

    MULTI_CITY = "multi_city"
    MULTI_AIRPORT = "multi_airport"
    CODE_VS_CITY = "code_vs_city"


@dataclass
class Airport:
    """Represents an airport with location and identification details.

    Attributes:
        iata: 3-letter IATA code (e.g., "LHR")
        icao: 4-letter ICAO code (e.g., "EGLL"), optional
        name: Full airport name (e.g., "London Heathrow")
        city: City name (e.g., "London")
        country: Country name (e.g., "United Kingdom")
        lat: Latitude coordinate
        lon: Longitude coordinate
        tz: Timezone identifier (e.g., "Europe/London"), optional
    """

    iata: str
    icao: str | None
    name: str
    city: str
    country: str
    lat: float
    lon: float
    tz: str | None = None

    def __post_init__(self) -> None:
        """Normalize IATA code to uppercase."""
        self.iata = self.iata.upper()
        if self.icao:
            self.icao = self.icao.upper()


@dataclass
class AirportOption:
    """A disambiguation option representing one possible interpretation.

    Used when user input could match multiple airports or cities.

    Attributes:
        display_name: Human-readable label (e.g., "Birmingham, UK")
        airports: List of airports for this option (may have multiple for multi-airport cities)
        match_type: How this option was matched ("iata", "icao", "airport_name", "city")
        confidence: Confidence score 0.0-1.0 for ranking options
    """

    display_name: str
    airports: list[Airport]
    match_type: Literal["iata", "icao", "airport_name", "city"]
    confidence: float = 1.0


@dataclass
class ResolveContext:
    """Context hints to guide airport resolution.

    Passed to AirportService.resolve() to narrow down ambiguous queries.

    Attributes:
        country_hint: Country to prefer (e.g., "United Kingdom" from previous disambiguation)
        prefer_major_airports: Whether to prefer major international airports (default True)

    Example:
        # After user selects "UK" in disambiguation
        context = ResolveContext(country_hint="United Kingdom")
        result = await service.resolve("Birmingham", context)
        # Returns BHX (Birmingham, UK) instead of asking again
    """

    country_hint: str | None = None
    prefer_major_airports: bool = True


@dataclass
class AirportResolution:
    """Result of resolving user input to airport(s).

    The `status` field indicates the resolution outcome:
    - "resolved": Successfully resolved to a specific airport
    - "needs_disambiguation": Multiple interpretations, user must choose
    - "not_found": No matching airport found

    Attributes:
        status: Resolution outcome
        airport: Primary resolved airport (if status="resolved")
        all_airports: All airports in multi-airport cities (for preference flow)
        needs_airport_preference: True if user should pick specific airport
        disambiguation_type: Type of disambiguation needed
        options: Disambiguation options for user to choose from
        suggested_prompt: AI-friendly prompt to ask user for clarification
        original_query: The original input string

    Examples:
        # Unambiguous resolution
        AirportResolution(
            status="resolved",
            airport=Airport(iata="AMS", ...),
            original_query="Amsterdam"
        )

        # Multi-city disambiguation
        AirportResolution(
            status="needs_disambiguation",
            disambiguation_type=DisambiguationType.MULTI_CITY,
            options=[
                AirportOption(display_name="Birmingham, UK", ...),
                AirportOption(display_name="Birmingham, Alabama, USA", ...)
            ],
            suggested_prompt="Which Birmingham did you mean?\\n  1. Birmingham, UK\\n  2. Birmingham, Alabama, USA"
        )

        # Multi-airport city (resolved but with preference option)
        AirportResolution(
            status="resolved",
            airport=Airport(iata="LHR", ...),  # Primary airport
            all_airports=[LHR, LGW, STN, LTN, LCY],
            needs_airport_preference=True,
            original_query="London"
        )
    """

    status: Literal["resolved", "needs_disambiguation", "not_found"]

    # For resolved (unambiguous)
    airport: Airport | None = None
    all_airports: list[Airport] = field(default_factory=list)
    needs_airport_preference: bool = False

    # For disambiguation
    disambiguation_type: DisambiguationType | None = None
    options: list[AirportOption] = field(default_factory=list)
    suggested_prompt: str | None = None

    # Metadata
    original_query: str = ""

    # True when the resolved airport is NOT in the queried city but a nearby fallback.
    # Set by AirportService._resolve_city when no own airport exists (e.g. Calapan → MBO).
    is_nearby_fallback: bool = False


__all__ = [
    "Airport",
    "AirportOption",
    "AirportResolution",
    "DisambiguationType",
    "ResolveContext",
]
