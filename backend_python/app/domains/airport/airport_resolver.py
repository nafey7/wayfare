"""
Comprehensive Airport Resolution Service

Resolves city names, airport names, IATA/ICAO codes to standardized IATA codes
using the comprehensive mwgg/Airports database (~29k airports).
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from app.shared.geo import haversine_km

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _SearchRow:
    """Pre-computed search index row.

    Uses ``slots=True`` to cut per-row memory overhead vs a plain dict
    (~600B → ~150B base), which materially matters at ~29K rows.
    """

    iata: str
    name: str
    city: str
    state: str
    country: str
    name_lower: str
    city_lower: str
    state_lower: str
    country_lower: str
    city_words: set[str] = field(default_factory=set)
    state_words: set[str] = field(default_factory=set)
    name_words: set[str] = field(default_factory=set)
    country_words: set[str] = field(default_factory=set)


class AirportResolver:
    """Comprehensive airport resolution using multiple strategies"""

    def __init__(self) -> None:
        self.airports_data: dict[str, Any] = {}
        self.city_to_airports: dict[str, list[str]] = {}
        self.name_to_code: dict[str, str] = {}
        self.priority_city_mappings: dict[str, str] = {}
        # Pre-computed search index built once at load time so /airports/search
        # avoids per-request .lower() over ~29K rows. See search_mwgg_sync.
        self._search_index: list[_SearchRow] = []
        self.loaded = False

    async def ensure_loaded(self) -> None:
        """Ensure airport data is loaded"""
        if not self.loaded:
            await self._load_airport_data()

    async def _load_airport_data(self) -> None:
        """Load and process airport data from GitHub or local cache"""
        cache_file = Path("airports_cache.json")

        try:
            # Try to load from local cache first
            if cache_file.exists():
                logger.info("Loading airports from local cache")

                # Use sync file operations in thread pool for async context
                def _load_cache() -> dict[str, Any]:
                    with open(cache_file, encoding="utf-8") as f:
                        return json.load(f)

                self.airports_data = await asyncio.to_thread(_load_cache)
            else:
                # Download from GitHub
                await self._download_airport_data(cache_file)

            # Process the data for faster lookups
            self._process_airport_data()
            self._setup_priority_mappings()
            self.loaded = True
            logger.info(f"Loaded {len(self.airports_data)} airports successfully")

        except Exception as e:
            logger.error(f"Failed to load airport data: {e}")
            # Fall back to basic manual mapping if download fails
            self._load_fallback_airports()

    async def _download_airport_data(self, cache_file: Path) -> None:
        """Download airport data from GitHub and cache it"""
        url = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response,
        ):
            if response.status == 200:
                # Get raw text and parse manually to avoid content-type issues
                text_content = await response.text()
                self.airports_data = json.loads(text_content)

                # Cache to local file using thread pool for async context
                def _save_cache() -> None:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(self.airports_data, f, ensure_ascii=False)

                await asyncio.to_thread(_save_cache)
            else:
                raise Exception(f"Failed to download airports: HTTP {response.status}")

    def _process_airport_data(self) -> None:
        """Process raw airport data for efficient lookups"""
        self.city_to_airports.clear()
        self.name_to_code.clear()
        self._search_index = []

        for _code, airport in self.airports_data.items():
            iata_code = airport.get("iata", "").strip()
            _icao_code = airport.get(
                "icao", ""
            ).strip()  # Available for future ICAO lookups
            name = airport.get("name", "").lower().strip()
            city = airport.get("city", "").lower().strip()
            # Only process airports with valid IATA codes
            if not iata_code or len(iata_code) != 3:
                continue

            # Map city to airports
            if city:
                if city not in self.city_to_airports:
                    self.city_to_airports[city] = []
                self.city_to_airports[city].append(iata_code)

            # Map airport name to IATA code
            if name:
                self.name_to_code[name] = iata_code

                # Also map without common suffixes
                name_clean = re.sub(
                    r"\s+(airport|international|intl|field|airfield|airbase|air base|municipal)$",
                    "",
                    name,
                )
                if name_clean != name:
                    self.name_to_code[name_clean] = iata_code

            # Build pre-lowercased search index row (used by search_mwgg_sync).
            self._search_index.append(
                self._build_search_row(
                    iata=iata_code.upper(),
                    name=airport.get("name", "") or "",
                    city=airport.get("city", "") or "",
                    state=airport.get("state", "") or "",
                    country=airport.get("country", "") or "",
                )
            )

    @staticmethod
    def _build_search_row(
        *, iata: str, name: str, city: str, state: str, country: str
    ) -> _SearchRow:
        name_lower = name.lower()
        city_lower = city.lower()
        state_lower = state.lower()
        country_lower = country.lower()
        return _SearchRow(
            iata=iata,
            name=name,
            city=city,
            state=state,
            country=country,
            name_lower=name_lower,
            city_lower=city_lower,
            state_lower=state_lower,
            country_lower=country_lower,
            city_words=set(city_lower.split()),
            state_words=set(state_lower.split()) if state_lower else set(),
            name_words=set(name_lower.split()),
            country_words=set(country_lower.split()),
        )

    def search_mwgg_sync(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Score airports against query using the pre-computed search index.

        Synchronous (CPU-bound). Callers in async contexts should wrap with
        ``await asyncio.to_thread(...)`` so the event loop is not blocked.

        Returns a list of result dicts with keys: iata, name, city, state, country.
        Scoring priorities match the previous inline implementation in
        ``app/api/airports.py::search_airports`` (mwgg branch).
        """
        query_lower = query.lower().strip()
        query_upper = query.upper().strip()
        query_words = set(query_lower.split())

        results: list[dict[str, Any]] = []

        for row in self._search_index:
            iata = row.iata
            name = row.name_lower
            city = row.city_lower
            state = row.state_lower
            country = row.country_lower

            score = 0

            if query_upper == iata:
                score = 200
            elif query_lower == city:
                score = 195
            elif state and query_lower == state:
                score = 190
            elif (
                name.startswith(query_lower)
                or f" {query_lower} " in f" {name} "
                or name.endswith(f" {query_lower}")
                or name.startswith(f"{query_lower} ")
            ):
                score = 130
            elif query_lower == country:
                score = 100
            elif state and state.startswith(query_lower):
                score = 115
            elif city.startswith(query_lower):
                score = 110
            elif query_upper in iata:
                score = 90
            elif country.startswith(query_lower):
                score = 80
            elif state and query_lower in state:
                score = 65
            elif query_lower in city:
                score = 60
            elif query_lower in country:
                score = 50
            elif query_lower in name:
                score = 35
            else:
                city_overlap = len(query_words & row.city_words)
                state_overlap = len(query_words & row.state_words)
                name_overlap = len(query_words & row.name_words)
                country_overlap = len(query_words & row.country_words)

                if city_overlap > 0:
                    score = city_overlap * 20
                elif state_overlap > 0:
                    score = state_overlap * 18
                elif country_overlap > 0:
                    score = country_overlap * 15
                elif name_overlap > 0:
                    score = name_overlap * 10

            if score > 0:
                results.append(
                    {
                        "score": score,
                        "iata": iata,
                        "name": row.name,
                        "city": row.city,
                        "state": row.state,
                        "country": row.country,
                    }
                )

        results.sort(key=lambda x: int(x["score"]), reverse=True)
        return results[:limit]

    def _setup_priority_mappings(self) -> None:
        """Setup priority mappings for major cities to override ambiguous database results"""
        self.priority_city_mappings = {
            # Major US Cities - use main international airports
            "new york": "JFK",
            "nyc": "JFK",
            "manhattan": "JFK",
            "los angeles": "LAX",
            "la": "LAX",
            "chicago": "ORD",
            "san francisco": "SFO",
            "sf": "SFO",
            "miami": "MIA",
            "boston": "BOS",
            "atlanta": "ATL",
            "seattle": "SEA",
            "dallas": "DFW",
            "denver": "DEN",
            "las vegas": "LAS",
            "vegas": "LAS",
            "orlando": "MCO",
            "washington": "DCA",
            "dc": "DCA",
            "austin": "AUS",
            # Major International Cities - use main international airports
            "london": "LHR",
            "paris": "CDG",
            "madrid": "MAD",
            "barcelona": "BCN",
            "rome": "FCO",
            "milan": "MXP",
            "amsterdam": "AMS",
            "eindhoven": "EIN",
            "rotterdam": "RTM",
            "frankfurt": "FRA",
            "munich": "MUC",
            "berlin": "BER",
            "zurich": "ZRH",
            "vienna": "VIE",
            "brussels": "BRU",
            "lisbon": "LIS",
            "athens": "ATH",
            "dublin": "DUB",
            "copenhagen": "CPH",
            "stockholm": "ARN",
            "oslo": "OSL",
            "tokyo": "NRT",
            "dubai": "DXB",
            "singapore": "SIN",
            "hong kong": "HKG",
            "beijing": "PEK",
            "shanghai": "PVG",
            "seoul": "ICN",
            "bangkok": "BKK",
            "delhi": "DEL",
            "mumbai": "BOM",
            "sydney": "SYD",
            "melbourne": "MEL",
            "toronto": "YYZ",
            "vancouver": "YVR",
            "montreal": "YUL",
            "calgary": "YYC",
            # Priority mappings for ambiguous city names (same name, different countries)
            "birmingham": "BHX",  # UK over US (BHM)
            "glasgow": "GLA",  # UK over US (GGW, GLW)
            "newcastle": "NCL",  # UK over US (ECS) and South Africa (NCS)
            "cambridge": "CBG",  # UK over US (CGE)
            "plymouth": "PLH",  # UK over US (PYM)
            "rochester": "RCS",  # UK over US (RCR, ROC, RST)
            "manchester": "MAN",  # UK over US (MHT) - already exists but keeping for clarity
            "lima": "LIM",  # Peru over US (AOH)
            "santiago": "SCL",  # Chile over Cuba (SCU) and others
            "hamilton": "BDA",  # Bermuda over Canada (YHM) and others (tourist destination)
            "kingston": "KIN",  # Jamaica over Canada (YGK)
            "perth": "PER",  # Australia over UK (PSL)
            "richmond": "RIC",  # US Virginia over Australia (XRH)
            "faro": "FAO",  # Portugal (fix data issue with ZFA)
            "venice": "VCE",  # Italy over US (VNC) — Marco Polo over FL Municipal
            "philadelphia": "PHL",  # International over Wings Field (BBX)
            "naples": "NAP",  # Italy over US (APF — Naples FL Municipal)
            "portland": "PDX",  # Oregon over Maine (PWM)
            "springfield": "SPI",  # Illinois (capital) over others
            # Common abbreviations and aliases
            "pcb": "ECP",  # Panama City Beach → Northwest Florida Beaches International
            "panama city beach": "ECP",  # Northwest Florida Beaches International
            "george bush airport": "IAH",  # Houston George Bush Intercontinental
            "george bush intercontinental": "IAH",
        }

        # Debug: Log that priority mappings are set up
        logger.info(
            f"Set up {len(self.priority_city_mappings)} priority city mappings, including london -> {self.priority_city_mappings.get('london', 'NOT FOUND')}"
        )

    def _load_fallback_airports(self) -> None:
        """Load basic airport mapping as fallback"""
        logger.warning("Using fallback airport mapping - limited coverage")
        # Keep existing manual mapping as fallback
        fallback_airports = {
            # Major US Cities
            "new york": "JFK",
            "New York": "JFK",
            "NYC": "JFK",
            "nyc": "JFK",
            "manhattan": "JFK",
            "los angeles": "LAX",
            "la": "LAX",
            "chicago": "ORD",
            "san francisco": "SFO",
            "sf": "SFO",
            "miami": "MIA",
            "boston": "BOS",
            "atlanta": "ATL",
            "seattle": "SEA",
            "dallas": "DFW",
            "denver": "DEN",
            "las vegas": "LAS",
            "vegas": "LAS",
            "orlando": "MCO",
            "washington": "DCA",
            "dc": "DCA",
            "austin": "AUS",
            # Major International Cities
            "london": "LHR",
            "London": "LHR",
            "LONDON": "LHR",
            "paris": "CDG",
            "madrid": "MAD",
            "barcelona": "BCN",
            "rome": "FCO",
            "milan": "MXP",
            "amsterdam": "AMS",
            "eindhoven": "EIN",
            "rotterdam": "RTM",
            "frankfurt": "FRA",
            "munich": "MUC",
            "berlin": "BER",
            "zurich": "ZRH",
            "vienna": "VIE",
            "brussels": "BRU",
            "lisbon": "LIS",
            "athens": "ATH",
            "dublin": "DUB",
            "copenhagen": "CPH",
            "stockholm": "ARN",
            "oslo": "OSL",
            "tokyo": "NRT",
            "dubai": "DXB",
            "singapore": "SIN",
            "hong kong": "HKG",
            "beijing": "PEK",
            "shanghai": "PVG",
            "seoul": "ICN",
            "bangkok": "BKK",
            "delhi": "DEL",
            "mumbai": "BOM",
            "sydney": "SYD",
            "melbourne": "MEL",
            "toronto": "YYZ",
            "vancouver": "YVR",
            "montreal": "YUL",
            "calgary": "YYC",
            # Priority mappings for ambiguous city names (same name, different countries)
            "birmingham": "BHX",  # UK over US (BHM)
            "glasgow": "GLA",  # UK over US (GGW, GLW)
            "newcastle": "NCL",  # UK over US (ECS) and South Africa (NCS)
            "cambridge": "CBG",  # UK over US (CGE)
            "plymouth": "PLH",  # UK over US (PYM)
            "rochester": "RCS",  # UK over US (RCR, ROC, RST)
            "manchester": "MAN",  # UK over US (MHT) - already exists but keeping for clarity
            "lima": "LIM",  # Peru over US (AOH)
            "santiago": "SCL",  # Chile over Cuba (SCU) and others
            "hamilton": "BDA",  # Bermuda over Canada (YHM) and others (tourist destination)
            "kingston": "KIN",  # Jamaica over Canada (YGK)
            "perth": "PER",  # Australia over UK (PSL)
            "richmond": "RIC",  # US Virginia over Australia (XRH)
            "faro": "FAO",  # Portugal (fix data issue with ZFA)
            "venice": "VCE",  # Italy over US (VNC) — Marco Polo over FL Municipal
            "philadelphia": "PHL",  # International over Wings Field (BBX)
            "naples": "NAP",  # Italy over US (APF — Naples FL Municipal)
            "portland": "PDX",  # Oregon over Maine (PWM)
            "springfield": "SPI",  # Illinois (capital) over others
            # Common abbreviations and aliases
            "pcb": "ECP",  # Panama City Beach → Northwest Florida Beaches International
            "panama city beach": "ECP",  # Northwest Florida Beaches International
            "george bush airport": "IAH",  # Houston George Bush Intercontinental
            "george bush intercontinental": "IAH",
        }

        # Convert to the expected format
        for city_name, iata_code in fallback_airports.items():
            if city_name not in self.city_to_airports:
                self.city_to_airports[city_name] = [iata_code]

        # Store priority mappings for major cities that might have conflicts
        self.priority_city_mappings = fallback_airports

        # Rebuild the search index from fallback data so /airports/search still
        # returns useful results when the GitHub download fails on cold start.
        # Without this, the index stays empty and search silently returns [].
        self._search_index = []
        seen_iatas: set[str] = set()
        for city_name, iata_code in fallback_airports.items():
            iata_upper = iata_code.upper()
            if iata_upper in seen_iatas:
                continue
            seen_iatas.add(iata_upper)
            self._search_index.append(
                self._build_search_row(
                    iata=iata_upper,
                    name=city_name.title(),
                    city=city_name,
                    state="",
                    country="",
                )
            )

        self.loaded = True

    async def resolve_airport(self, location: str) -> str | None:
        """
        Resolve location string to IATA airport code

        Supports:
        - City names (e.g., "Calgary", "New York")
        - Airport names (e.g., "John F Kennedy International")
        - IATA codes (e.g., "YYC", "JFK")
        - ICAO codes (e.g., "CYYC", "KJFK")

        Args:
            location: Location string to resolve

        Returns:
            IATA code if found, None otherwise
        """
        await self.ensure_loaded()

        if not location:
            return None

        location = location.strip()
        location_lower = location.lower()

        # Strategy 1: Direct IATA code (3 letters)
        if len(location) == 3 and location.upper().isalpha():
            # Verify it exists in our data
            for airport in self.airports_data.values():
                if airport.get("iata", "").upper() == location.upper():
                    return location.upper()

        # Strategy 2: ICAO code (4 letters) - convert to IATA
        if len(location) == 4 and location.upper().isalpha():
            for airport in self.airports_data.values():
                if airport.get("icao", "").upper() == location.upper():
                    iata = airport.get("iata", "").strip()
                    if iata and len(iata) == 3:
                        return iata.upper()

        # Strategy 2.5: Priority city mappings (check before general city lookup)
        # Force explicit check for known problematic cities to ensure priority mapping works
        priority_override = {
            "london": "LHR",
            "London": "LHR",
            "LONDON": "LHR",
            "paris": "CDG",
            "new york": "JFK",
            "nyc": "JFK",
            "New York": "JFK",
            "NYC": "JFK",
            "los angeles": "LAX",
            "la": "LAX",
        }

        if location_lower in priority_override:
            logger.info(
                f"Using explicit priority override for '{location}': {priority_override[location_lower]}"
            )
            return priority_override[location_lower]

        if location_lower in self.priority_city_mappings:
            priority_code = self.priority_city_mappings[location_lower]
            logger.info(f"Using priority mapping for '{location}': {priority_code}")
            return priority_code

        # Debug: Log what's in city_to_airports for london
        if location_lower == "london" and location_lower in self.city_to_airports:
            logger.warning(
                f"London found in city_to_airports but not in priority_city_mappings: {self.city_to_airports[location_lower]}"
            )
            logger.warning(
                f"Priority mappings loaded: {bool(self.priority_city_mappings)}, keys sample: {list(self.priority_city_mappings.keys())[:10]}"
            )  # Show first 10 keys

        # Strategy 3: City name lookup
        if location_lower in self.city_to_airports:
            airports = self.city_to_airports[location_lower]
            # Return the main airport (usually first or most important)
            return airports[0] if airports else None

        # Strategy 4: Airport name lookup
        if location_lower in self.name_to_code:
            return self.name_to_code[location_lower].upper()

        # Strategy 5: Partial matching for city names
        best_match = self._find_partial_city_match(location_lower)
        if best_match:
            return best_match

        # Strategy 6: Partial matching for airport names
        best_match = self._find_partial_airport_name_match(location_lower)
        if best_match:
            return best_match

        return None

    def _find_partial_city_match(self, search_term: str) -> str | None:
        """Find partial matches for city names"""
        search_words = set(search_term.split())
        best_match = None
        best_score = 0.0

        for city, airports in self.city_to_airports.items():
            city_words = set(city.split())

            # Calculate word overlap
            overlap = len(search_words & city_words)
            if overlap > 0:
                # Combined score: how much of the city name matched AND how
                # much of the search term matched.  Prevents country names
                # from falsely matching single-word city names.
                city_coverage = overlap / len(city_words)
                search_coverage = overlap / len(search_words)
                score = city_coverage * search_coverage
                if score > best_score and score > 0.5:  # Strict >50% combined match
                    best_score = score
                    best_match = airports[0] if airports else None

        return best_match

    def _find_partial_airport_name_match(self, search_term: str) -> str | None:
        """Find partial matches for airport names"""
        search_words = set(search_term.split())
        best_match = None
        best_score = 0.0

        for name, code in self.name_to_code.items():
            name_words = set(name.split())

            # Calculate word overlap
            overlap = len(search_words & name_words)
            if overlap > 0:
                # Score must account for BOTH directions: how much of the
                # airport name matched AND how much of the search term matched.
                # "Dominican republic" vs "Republic Airport" = 1/2 name + 1/2 search
                # = 0.25 combined → rejected.  Without this, country names like
                # "Dominican Republic" falsely match "Republic Airport" (FRG).
                name_coverage = overlap / len(name_words)
                search_coverage = overlap / len(search_words)
                score = name_coverage * search_coverage
                if score > best_score and score > 0.5:  # Strict >50% combined match
                    best_score = score
                    best_match = code

        return best_match

    async def get_airport_info(self, iata_code: str) -> dict[str, Any] | None:
        """Get detailed airport information by IATA code"""
        await self.ensure_loaded()

        for airport in self.airports_data.values():
            if airport.get("iata", "").upper() == iata_code.upper():
                return airport

        return None

    async def search_airports(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search airports by name or city with ranking"""
        await self.ensure_loaded()

        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for airport in self.airports_data.values():
            iata = airport.get("iata", "").strip()
            if not iata or len(iata) != 3:
                continue

            name = airport.get("name", "").lower()
            city = airport.get("city", "").lower()
            # Calculate relevance score
            score = 0

            # Exact matches get highest score
            if query_lower in (city, name):
                score = 100
            elif query_lower in city or query_lower in name:
                score = 50
            else:
                # Word-based matching
                city_words = set(city.split())
                name_words = set(name.split())

                city_overlap = len(query_words & city_words)
                name_overlap = len(query_words & name_words)

                if city_overlap > 0:
                    score = city_overlap * 20
                elif name_overlap > 0:
                    score = name_overlap * 10

            if score > 0:
                results.append(
                    {
                        "score": score,
                        "iata": iata.upper(),
                        "name": airport.get("name", ""),
                        "city": airport.get("city", ""),
                        "country": airport.get("country", ""),
                    }
                )
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def get_city_airports(self, city_name: str) -> list[dict[str, Any]]:
        """
        Get all airports for a given city with detailed information

        This method is used for multi-airport city preference flow (Issue #12).
        When a city has multiple airports, the system can present all options
        to the user for selection.

        Args:
            city_name: City name to look up (e.g., "London", "New York", "Paris")

        Returns:
            List of airport dictionaries with iata, name, city, country.
            Priority airports (from priority_city_mappings) appear first.
            Empty list if city not found or has no airports.

        Example:
            >>> await resolver.get_city_airports("London")
            [
                {"iata": "LHR", "name": "London Heathrow", "city": "London", "country": "United Kingdom"},
                {"iata": "LGW", "name": "London Gatwick", "city": "London", "country": "United Kingdom"},
                {"iata": "STN", "name": "London Stansted", "city": "London", "country": "United Kingdom"},
                {"iata": "LCY", "name": "London City Airport", "city": "London", "country": "United Kingdom"},
                {"iata": "LTN", "name": "London Luton", "city": "London", "country": "United Kingdom"}
            ]
        """
        await self.ensure_loaded()

        if not city_name:
            return []

        city_lower = city_name.lower().strip()
        airport_results = []

        # Check if this city has a priority mapping (main airport)
        priority_code = None
        if city_lower in self.priority_city_mappings:
            priority_code = self.priority_city_mappings[city_lower]

        # Get all airports for this city from database
        airport_codes = self.city_to_airports.get(city_lower, [])

        # ISSUE #12: Apply filtering for multi-airport cities
        # FILTER 1: Country filtering (Bug #2 fix)
        # If city has a priority mapping, only show airports from same country
        if (
            priority_code
            and city_lower in self.priority_city_mappings
            and airport_codes
        ):
            # Get country from priority airport
            target_country = None
            for airport in self.airports_data.values():
                if airport.get("iata", "").upper() == priority_code.upper():
                    target_country = airport.get("country")
                    break

            if target_country:
                # Filter to same country only
                filtered_by_country = []
                for code in airport_codes:
                    for apt in self.airports_data.values():
                        if apt.get("iata", "").upper() == code.upper():
                            if apt.get("country") == target_country:
                                filtered_by_country.append(code)
                            break

                if filtered_by_country:
                    logger.info(
                        f"Country filter: '{city_name}' reduced from {len(airport_codes)} "
                        f"to {len(filtered_by_country)} airports in {target_country}"
                    )
                    airport_codes = filtered_by_country

        # FILTER 2: Commercial airports only (Bug #4 fix)
        # Exclude military bases, seaplane bases, and general aviation airports
        # that FlightLogic API doesn't support
        if airport_codes:
            commercial_only = []
            for code in airport_codes:
                # Find airport data by iterating values (airports_data is keyed by ID, not IATA)
                airport_data = None
                for airport in self.airports_data.values():
                    if airport.get("iata", "").upper() == code.upper():
                        airport_data = airport
                        break

                if not airport_data:
                    # If we can't find data, keep the code (safety)
                    commercial_only.append(code)
                    continue

                name = airport_data.get("name", "").lower()

                # Exclude military airports
                if any(
                    military in name
                    for military in [
                        "raf ",
                        "air force base",
                        "afb ",
                        "military",
                        "naval air",
                        "mcas ",
                    ]
                ):
                    logger.debug(f"Excluding military airport: {code} - {name}")
                    continue

                # Exclude seaplane bases
                if "seaplane" in name:
                    logger.debug(f"Excluding seaplane base: {code} - {name}")
                    continue

                # Exclude general aviation (be conservative - only obvious ones)
                # Known general aviation airports: Biggin Hill, etc.
                if any(
                    ga in name
                    for ga in [
                        "airpark",
                        "airfield",
                        "executive airport",
                        "biggin hill",
                    ]
                ):
                    logger.debug(f"Excluding general aviation: {code} - {name}")
                    continue

                commercial_only.append(code)

            # Use commercial-only list if we filtered anything out
            if commercial_only and len(commercial_only) < len(airport_codes):
                logger.info(
                    f"Commercial filter: '{city_name}' reduced from {len(airport_codes)} "
                    f"to {len(commercial_only)} commercial airports"
                )
                airport_codes = commercial_only
            elif not commercial_only:
                # If all were filtered out, keep original list (safety fallback)
                logger.warning(
                    f"All airports filtered out for '{city_name}', keeping original {len(airport_codes)} airports"
                )

        # If no airports found in city_to_airports, check if input is already an airport code
        if not airport_codes and len(city_name) == 3 and city_name.upper().isalpha():
            # Single airport - check if it exists in database
            for airport in self.airports_data.values():
                if airport.get("iata", "").upper() == city_name.upper():
                    airport_codes = [city_name.upper()]
                    break

        if not airport_codes:
            logger.warning(f"No airports found for city: {city_name}")
            return []

        # Build list with priority airport first
        if priority_code:
            # Add priority airport first
            for airport in self.airports_data.values():
                if airport.get("iata", "").upper() == priority_code.upper():
                    airport_results.append(
                        {
                            "iata": priority_code.upper(),
                            "name": airport.get("name", ""),
                            "city": airport.get("city", ""),
                            "country": airport.get("country", ""),
                        }
                    )
                    break

        # Add remaining airports (excluding priority if already added)
        for code in airport_codes:
            if priority_code and code.upper() == priority_code.upper():
                continue  # Skip priority code, already added

            # Find full airport details
            for airport in self.airports_data.values():
                if airport.get("iata", "").upper() == code.upper():
                    airport_results.append(
                        {
                            "iata": code.upper(),
                            "name": airport.get("name", ""),
                            "city": airport.get("city", ""),
                            "country": airport.get("country", ""),
                        }
                    )
                    break

        logger.info(
            f"Found {len(airport_results)} airports for city '{city_name}': {[a['iata'] for a in airport_results]}"
        )
        return airport_results

    async def get_airports_by_city_name(self, city_name: str) -> list[str]:
        """
        Convenience method to get just IATA codes for a city

        This is a simpler version of get_city_airports() that returns only
        the airport codes without full details.

        Args:
            city_name: City name to look up

        Returns:
            List of IATA codes (e.g., ["LHR", "LGW", "STN", "LCY", "LTN"])
            Empty list if city not found

        Example:
            >>> await resolver.get_airports_by_city_name("New York")
            ["JFK", "LGA", "EWR"]
        """
        airports = await self.get_city_airports(city_name)
        return [airport["iata"] for airport in airports]

    async def find_nearby_airports(
        self,
        iata_code: str,
        radius_km: float = 200,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find airports within radius_km of the given IATA code, sorted by distance.

        Uses haversine formula on lat/lon coordinates from the mwgg/Airports database.
        Works purely on coordinates — not on city name — so it correctly finds
        alternatives even when nearby airports have different city names in the DB
        (e.g. IAG/Niagara Falls and ROC/Rochester are obvious BUF alternatives
        but have different city fields).

        Args:
            iata_code: Reference airport IATA code (e.g. "BUF")
            radius_km: Search radius in kilometres (default 200 ≈ 2-hour drive)
            limit: Maximum number of results to return (default 5)

        Returns:
            List of dicts sorted by distance ascending:
            [{"iata", "name", "city", "state", "country", "distance_km"}, ...]
            Empty list if reference airport has no coordinates or none found.
        """
        await self.ensure_loaded()

        # Find reference airport coordinates
        ref_airport = None
        for airport in self.airports_data.values():
            if airport.get("iata", "").upper() == iata_code.upper():
                ref_airport = airport
                break

        if ref_airport is None:
            logger.warning(
                "find_nearby_airports: IATA code '%s' not found in database", iata_code
            )
            return []

        ref_lat = ref_airport.get("lat")
        ref_lon = ref_airport.get("lon")
        if ref_lat is None or ref_lon is None:
            logger.warning("find_nearby_airports: no coordinates for '%s'", iata_code)
            return []

        ref_lat = float(ref_lat)
        ref_lon = float(ref_lon)

        nearby: list[dict[str, Any]] = []
        for airport in self.airports_data.values():
            code = airport.get("iata", "").strip()
            if not code or len(code) != 3:
                continue
            if code.upper() == iata_code.upper():
                continue  # skip the reference airport itself

            lat = airport.get("lat")
            lon = airport.get("lon")
            if lat is None or lon is None:
                continue

            dist = haversine_km(ref_lat, ref_lon, float(lat), float(lon))
            if dist <= radius_km:
                nearby.append(
                    {
                        "iata": code.upper(),
                        "name": airport.get("name", ""),
                        "city": airport.get("city", ""),
                        "state": airport.get("state", ""),
                        "country": airport.get("country", ""),
                        "distance_km": round(dist),
                    }
                )

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby[:limit]


# Create singleton instance that can be imported
airport_resolver = AirportResolver()


async def resolve_airport(location: str) -> str | None:
    """Convenience function for airport resolution"""
    return await airport_resolver.resolve_airport(location)
