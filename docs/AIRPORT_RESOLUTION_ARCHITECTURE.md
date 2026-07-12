# Airport Resolution Architecture

> **Status:** Design Complete - Implementation Pending
> **Date:** 2025-12-11
> **See Also:** [AIRPORT_RESOLUTION_PROPOSAL.md](./AIRPORT_RESOLUTION_PROPOSAL.md) for detailed rationale

---

## Overview

This document describes the practical architecture for implementing the new AirportService. It focuses on **what we'd build**, not why.

The Airport Resolution system provides a unified interface for resolving user location input (city names, airport codes, airport names) to specific airports. It integrates with the existing `GeocodingService` to handle ambiguous city names.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI / Conversation Layer                    │
│  - Calls AirportService.resolve()                               │
│  - Handles disambiguation questions (stores in session)         │
│  - Processes user responses to disambiguation                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AirportService                            │
│  resolve(query, context?) → AirportResolution                   │
│  get_airports_in_city(city, country?) → list[Airport]           │
│  get_nearby_airports(lat, lon, radius?, limit?) → [Airport, km] │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────────┐
│    AirportRepository      │   │      GeocodingService           │
│  get_by_iata(code)        │   │  geocode(query)                 │
│  get_by_icao(code)        │   │    → list[GeocodingResult]      │
│  get_by_city(city,country)│   │                                 │
│  search_by_name(query)    │   │  Existing service in            │
│  search(query, limit)     │   │  app/shared/geocoding.py        │
│  find_nearby(lat,lon,...) │   │                                 │
│                           │   │  Wraps Google Geocoding API     │
│  Data: mwgg/Airports      │   │                                 │
│  (29K airports)           │   │                                 │
└───────────────────────────┘   └─────────────────────────────────┘
```

## Module Structure

```
app/domains/airport/
├── __init__.py              # Exports and get_airport_service() factory
├── models.py                # Airport, AirportResolution, AirportOption, etc.
├── repository.py            # AirportRepository (data access layer)
├── service.py               # AirportService (orchestration)
└── data/
    └── airports_cache.json  # mwgg airport data (existing)

app/shared/
└── geocoding.py             # GeocodingService (existing, shared with hotels)
```

## Key Models

### Airport

```python
@dataclass
class Airport:
    iata: str                    # "LHR"
    icao: str | None             # "EGLL"
    name: str                    # "London Heathrow"
    city: str                    # "London"
    country: str                 # "United Kingdom"
    lat: float                   # 51.4700
    lon: float                   # -0.4543
    tz: str | None = None        # "Europe/London"
```

### DisambiguationType

```python
class DisambiguationType(str, Enum):
    MULTI_CITY = "multi_city"           # Same city name, different countries
    MULTI_AIRPORT = "multi_airport"     # Same city, multiple airports
    CODE_VS_CITY = "code_vs_city"       # Input matches IATA code AND city name
```

### AirportOption

```python
@dataclass
class AirportOption:
    display_name: str                   # "Birmingham, UK" or "Goa, India"
    airports: list[Airport]             # May have multiple for multi-airport cities
    match_type: Literal["iata", "icao", "airport_name", "city"]
    confidence: float                   # 0.0 - 1.0
```

### AirportResolution

```python
@dataclass
class AirportResolution:
    status: Literal["resolved", "needs_disambiguation", "not_found"]

    # For resolved (unambiguous)
    airport: Airport | None = None
    all_airports: list[Airport] = field(default_factory=list)
    needs_airport_preference: bool = False  # True for multi-airport cities

    # For disambiguation
    disambiguation_type: DisambiguationType | None = None
    options: list[AirportOption] = field(default_factory=list)
    suggested_prompt: str | None = None     # "Which Birmingham did you mean?"

    # Metadata
    original_query: str = ""
```

### ResolveContext

```python
@dataclass
class ResolveContext:
    country_hint: str | None = None          # From previous disambiguation
    prefer_major_airports: bool = True       # LHR over LTN for "London"
```

## Resolution Strategy

`AirportService.resolve()` collects ALL possible interpretations, then decides what to return:

### Resolution Order

1. **Exact IATA code** (3 uppercase letters) → immediate match
2. **Exact ICAO code** (4 uppercase letters) → convert to IATA
3. **Airport name match** ("London Heathrow", "Charles de Gaulle")
4. **Partial airport name** ("Heathrow", "Gatwick")
5. **City name** → may trigger geocoding if ambiguous
6. **Fuzzy/partial match** → fallback search

### Disambiguation Types

| Type | Example Input | What Happens |
|------|---------------|--------------|
| `MULTI_CITY` | "Birmingham" | Geocoding returns UK + USA options |
| `MULTI_AIRPORT` | "London" | Single city, multiple airports (LHR, LGW, STN, etc.) |
| `CODE_VS_CITY` | "GOA" | Matches IATA "GOA" (Genoa) AND city "Goa" (India) |

## Example Resolutions

### Exact IATA Code

```python
result = await airport_service.resolve("LHR")
# AirportResolution(
#     status="resolved",
#     airport=Airport(iata="LHR", name="London Heathrow", ...),
#     original_query="LHR"
# )
```

### Multi-Airport City

```python
result = await airport_service.resolve("London")
# AirportResolution(
#     status="resolved",
#     airport=Airport(iata="LHR", ...),  # Primary airport
#     all_airports=[LHR, LGW, STN, LTN, LCY],
#     needs_airport_preference=True,
#     original_query="London"
# )
```

### Multi-City Disambiguation

```python
result = await airport_service.resolve("Birmingham")
# AirportResolution(
#     status="needs_disambiguation",
#     disambiguation_type=DisambiguationType.MULTI_CITY,
#     options=[
#         AirportOption(display_name="Birmingham, UK", airports=[BHX], ...),
#         AirportOption(display_name="Birmingham, Alabama, USA", airports=[BHM], ...),
#     ],
#     suggested_prompt="Which Birmingham did you mean?\n  1. Birmingham, UK\n  2. Birmingham, Alabama, USA",
#     original_query="Birmingham"
# )
```

### Code vs City Disambiguation

```python
result = await airport_service.resolve("GOA")
# AirportResolution(
#     status="needs_disambiguation",
#     disambiguation_type=DisambiguationType.CODE_VS_CITY,
#     options=[
#         AirportOption(display_name="Genoa, Italy (GOA)", airports=[GOA], match_type="iata"),
#         AirportOption(display_name="Goa, India", airports=[GOI, GOX], match_type="city"),
#     ],
#     suggested_prompt="Did you mean the airport code or the city?\n  1. Genoa, Italy (GOA)\n  2. Goa, India (GOI/GOX)",
#     original_query="GOA"
# )
```

### With Country Hint (After Disambiguation)

```python
result = await airport_service.resolve(
    "Birmingham",
    context=ResolveContext(country_hint="United Kingdom")
)
# AirportResolution(
#     status="resolved",
#     airport=Airport(iata="BHX", city="Birmingham", country="United Kingdom", ...),
#     original_query="Birmingham"
# )
```

## Conversation Flow

The AI layer handles the conversation flow for disambiguation:

```
User: "flights to Birmingham"
    │
    ▼
AI Layer calls: airport_service.resolve("Birmingham")
    │
    ▼
AirportResolution(status="needs_disambiguation", ...)
    │
    ▼
AI Layer stores in session: session.pending_disambiguation = resolution
AI Layer returns: "Which Birmingham did you mean?
  1. Birmingham, UK
  2. Birmingham, Alabama, USA"
    │
    ▼
User: "UK"
    │
    ▼
AI Layer matches "UK" to option 1
AI Layer calls: airport_service.resolve("Birmingham", ResolveContext(country_hint="United Kingdom"))
    │
    ▼
AirportResolution(status="resolved", airport=BHX)
    │
    ▼
AI Layer clears: session.pending_disambiguation = None
AI Layer sets: session.destination = "BHX"
Continue booking flow...
```

## Responsibility Boundaries

| Layer | Responsibility | Does NOT Do |
|-------|----------------|-------------|
| **AirportService** | Resolve location strings to airports | Manage conversation state |
| **AirportService** | Integrate geocoding for ambiguous cities | Ask user questions |
| **AirportService** | Return disambiguation options with suggested prompts | Store session data |
| **AirportRepository** | Data access (IATA, ICAO, city lookups) | Business logic |
| **AI Layer** | Handle conversation flow | Resolve airports directly |
| **AI Layer** | Store disambiguation state in session | Call geocoding directly |
| **AI Layer** | Ask user questions, process responses | |
| **Field Collector** | Extract location text from user messages | Resolve to airport codes |
| **Field Collector** | Strip keywords ("flights", "show me") | Handle disambiguation |

## What AirportService Does NOT Handle

The following should be handled by the AI layer BEFORE calling AirportService:

- **Events**: "soccer world cup" → AI determines location first
- **Landmarks**: "near the Eiffel Tower" → AI geocodes landmark, then calls `get_nearby_airports()`
- **Concepts**: "somewhere warm" → AI determines user intent
- **User context**: "my usual airport" → AI looks up user preferences

AirportService only handles explicit location references:
- City names: "London", "Paris", "Birmingham"
- Airport codes: "LHR", "CDG", "GOA"
- Airport names: "Heathrow", "Charles de Gaulle", "London Gatwick"

## Interface Summary

### AirportService

```python
class AirportService:
    def __init__(self, repository: AirportRepository, geocoding: GeocodingService): ...

    async def resolve(
        self,
        query: str,
        context: ResolveContext | None = None
    ) -> AirportResolution:
        """Main entry point. Resolves user input to airport(s)."""

    def get_airports_in_city(
        self,
        city: str,
        country: str | None = None
    ) -> list[Airport]:
        """Get all airports serving a city."""

    def get_nearby_airports(
        self,
        lat: float,
        lon: float,
        radius_km: int | None = None,
        limit: int = 10
    ) -> list[tuple[Airport, float]]:
        """
        Find airports near coordinates. Returns (airport, distance_km).

        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Optional max radius. If None, returns closest `limit` airports.
            limit: Max number of results (default 10)

        Examples:
            # Find 5 closest airports to a city (no radius limit)
            get_nearby_airports(51.5, -0.12, limit=5)

            # Find airports within 50km
            get_nearby_airports(51.5, -0.12, radius_km=50)

            # Find up to 3 airports within 100km
            get_nearby_airports(51.5, -0.12, radius_km=100, limit=3)
        """
```

### AirportRepository

```python
class AirportRepository:
    def __init__(self, data_path: Path | None = None): ...

    def get_by_iata(self, code: str) -> Airport | None: ...
    def get_by_icao(self, code: str) -> Airport | None: ...
    def get_by_city(self, city: str, country: str | None = None) -> list[Airport]: ...
    def search_by_name(self, query: str, limit: int = 10) -> list[Airport]: ...
    def search(self, query: str, limit: int = 10) -> list[Airport]: ...
    def find_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: int | None = None,
        limit: int = 10
    ) -> list[tuple[Airport, float]]:
        """
        Find airports near coordinates. Returns (airport, distance_km) sorted by distance.

        If radius_km is None, returns the closest `limit` airports regardless of distance.
        If radius_km is set, returns up to `limit` airports within that radius.
        """
```

## Migration Path

### Current State (Scattered)

```
enhanced_flight_handler.py     → 818 lines of disambiguation logic
flight_field_collector.py      → _resolve_airport() + hardcoded fallback map
airport_resolver.py            → Core resolution with 3x duplicate priority maps
geocoding.py                   → Used by hotels only
```

### Target State (Unified)

```
app/domains/airport/
├── service.py      → AirportService (single entry point)
├── repository.py   → AirportRepository (data access)
└── models.py       → Clean data models

AI layer           → Handles conversation flow only
Field Collector    → Extracts text only, no resolution
```

### Implementation Order

1. **#149**: Create `AirportService`, `AirportRepository`, models
2. **#150**: Refactor AI layer to use `AirportService`, handle disambiguation
3. **#151**: Clean up Field Collector, remove duplicate resolution

## Related Documentation

- [AIRPORT_RESOLUTION_PROPOSAL.md](./AIRPORT_RESOLUTION_PROPOSAL.md) - Detailed rationale and decision matrix
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [FLIGHT_FEATURES.md](./FLIGHT_FEATURES.md) - Flight booking features

## Related Issues

- #149 - Create unified AirportService with clean interface
- #150 - Refactor AI layer to use AirportService
- #151 - Clean up Field Collector
- #21 - Origin/Destination regex bug (Field Collector)
- #22 - Keyword stripping bug (Field Collector)
