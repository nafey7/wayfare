"""Airport data repository for lookups and searches.

This module provides data access for airport information from the mwgg/Airports
database (~29K airports worldwide). It handles:
- Data loading from GitHub with local caching
- IATA/ICAO code lookups
- City-based airport searches
- Airport name searches with fuzzy matching
- Coordinate-based nearby airport searches

Usage:
    from app.domains.airport.repository import AirportRepository

    repo = AirportRepository()
    await repo.ensure_loaded()

    airport = repo.get_by_iata("LHR")
    london_airports = repo.get_by_city("London", country="United Kingdom")
"""

import asyncio
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

import aiohttp

from app.domains.airport.models import Airport
from app.shared.geo import haversine_km

logger = logging.getLogger(__name__)


def _strip_diacritics(text: str) -> str:
    """Strip diacritics so 'Cancún' matches 'Cancun' in lookups."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class AirportRepository:
    """Data access layer for airport lookups.

    Loads airport data from mwgg/Airports GitHub repository and provides
    efficient lookups by IATA code, ICAO code, city name, and airport name.

    The repository includes 70+ priority mappings for major cities to ensure
    the most common airports are returned first (e.g., "London" → LHR).
    """

    def __init__(self, data_path: Path | None = None) -> None:
        """Initialize the repository.

        Args:
            data_path: Optional path to cached airport data JSON file.
                      Defaults to airports_cache.json in current directory.
        """
        self.data_path = data_path or Path("airports_cache.json")
        self.airports_data: dict[str, Any] = {}
        self.city_to_airports: dict[str, list[str]] = {}
        self.name_to_code: dict[str, str] = {}
        self.priority_city_mappings: dict[str, str] = {}
        self._iata_index: dict[str, Airport] = {}
        self._icao_index: dict[str, Airport] = {}
        self.loaded = False

    async def ensure_loaded(self) -> None:
        """Ensure airport data is loaded. Safe to call multiple times."""
        if not self.loaded:
            await self._load_airport_data()

    async def _load_airport_data(self) -> None:
        """Load and process airport data from GitHub or local cache."""
        try:
            if self.data_path.exists():
                logger.info("Loading airports from local cache")

                def _load_cache() -> dict[str, Any]:
                    with open(self.data_path, encoding="utf-8") as f:
                        return json.load(f)

                self.airports_data = await asyncio.to_thread(_load_cache)
            else:
                await self._download_airport_data()

            self._process_airport_data()
            self._setup_priority_mappings()
            self.loaded = True
            logger.info(f"Loaded {len(self.airports_data)} airports successfully")

        except Exception as e:
            logger.error(f"Failed to load airport data: {e}")
            self._load_fallback_airports()

    async def _download_airport_data(self) -> None:
        """Download airport data from GitHub and cache locally."""
        url = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response,
        ):
            if response.status == 200:
                text_content = await response.text()
                self.airports_data = json.loads(text_content)

                def _save_cache() -> None:
                    with open(self.data_path, "w", encoding="utf-8") as f:
                        json.dump(self.airports_data, f, ensure_ascii=False)

                await asyncio.to_thread(_save_cache)
                logger.info(f"Downloaded and cached {len(self.airports_data)} airports")
            else:
                raise RuntimeError(
                    f"Failed to download airports: HTTP {response.status}"
                )

    def _process_airport_data(self) -> None:
        """Process raw airport data for efficient lookups."""
        self.city_to_airports.clear()
        self.name_to_code.clear()
        self._iata_index.clear()
        self._icao_index.clear()

        for _code, airport_data in self.airports_data.items():
            iata_code = airport_data.get("iata", "").strip()
            icao_code = airport_data.get("icao", "").strip()
            name = airport_data.get("name", "").strip()
            city = airport_data.get("city", "").strip()
            country = airport_data.get("country", "").strip()

            # Only process airports with valid IATA codes
            if not iata_code or len(iata_code) != 3:
                continue

            # Create Airport object
            airport = Airport(
                iata=iata_code.upper(),
                icao=icao_code.upper() if icao_code else None,
                name=name,
                city=city,
                country=country,
                lat=float(airport_data.get("lat", 0)),
                lon=float(airport_data.get("lon", 0)),
                tz=airport_data.get("tz"),
            )

            # Index by IATA
            self._iata_index[iata_code.upper()] = airport

            # Index by ICAO
            if icao_code and len(icao_code) == 4:
                self._icao_index[icao_code.upper()] = airport

            # Map city to airports (lowercase + diacritics-stripped for robust lookup)
            city_lower = _strip_diacritics(city.lower())
            if city_lower:
                if city_lower not in self.city_to_airports:
                    self.city_to_airports[city_lower] = []
                self.city_to_airports[city_lower].append(iata_code.upper())

            # Map airport name to IATA code
            name_lower = name.lower()
            if name_lower:
                self.name_to_code[name_lower] = iata_code.upper()

                # Also map without common suffixes
                name_clean = re.sub(
                    r"\s+(airport|international|intl|field|airfield|airbase|air base|municipal)$",
                    "",
                    name_lower,
                )
                if name_clean != name_lower:
                    self.name_to_code[name_clean] = iata_code.upper()

    def _setup_priority_mappings(self) -> None:
        """Setup priority mappings for major cities.

        These ensure the most common/major airport is returned for ambiguous
        city names (e.g., "London" → LHR, not some random London airport).
        """
        self.priority_city_mappings = {
            # Major US Cities
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
            # Major International Cities
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
            # Ambiguous city names (same name, different countries)
            "birmingham": "BHX",  # UK over US (BHM)
            "glasgow": "GLA",  # UK over US (GGW, GLW)
            "newcastle": "NCL",  # UK over US (ECS) and South Africa (NCS)
            "cambridge": "CBG",  # UK over US (CGE)
            "plymouth": "PLH",  # UK over US (PYM)
            "rochester": "RCS",  # UK over US (RCR, ROC, RST)
            "manchester": "MAN",  # UK over US (MHT)
            "lima": "LIM",  # Peru over US (AOH)
            "santiago": "SCL",  # Chile over Cuba (SCU) and others
            "hamilton": "BDA",  # Bermuda over Canada (YHM)
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
            "pcb": "ECP",  # Panama City Beach → Northwest Florida Beaches Intl
            "panama city beach": "ECP",
            "george bush airport": "IAH",  # Houston George Bush Intercontinental
            "george bush intercontinental": "IAH",
        }

        logger.debug(
            f"Set up {len(self.priority_city_mappings)} priority city mappings"
        )

    def _load_fallback_airports(self) -> None:
        """Load minimal hardcoded mapping as fallback when data unavailable."""
        logger.warning("Using fallback airport mapping - limited coverage")

        # Set up priority mappings first (normally done in _setup_priority_mappings)
        self._setup_priority_mappings()

        # Use priority mappings to populate city_to_airports
        for city_name, iata_code in self.priority_city_mappings.items():
            city_lower = city_name.lower()
            if city_lower not in self.city_to_airports:
                self.city_to_airports[city_lower] = [iata_code]

        self.loaded = True

    def get_by_iata(self, code: str) -> Airport | None:
        """Get airport by IATA code.

        Args:
            code: 3-letter IATA code (e.g., "LHR")

        Returns:
            Airport if found, None otherwise
        """
        return self._iata_index.get(code.upper())

    def get_by_icao(self, code: str) -> Airport | None:
        """Get airport by ICAO code.

        Args:
            code: 4-letter ICAO code (e.g., "EGLL")

        Returns:
            Airport if found, None otherwise
        """
        return self._icao_index.get(code.upper())

    def get_by_city(self, city: str, country: str | None = None) -> list[Airport]:
        """Get all airports in a city.

        Args:
            city: City name (case-insensitive)
            country: Optional country filter

        Returns:
            List of airports in the city, with priority airport first
        """
        city_key = _strip_diacritics(city.lower().strip())
        airport_codes = self.city_to_airports.get(city_key, [])

        if not airport_codes:
            return []

        # Get Airport objects
        airports: list[Airport] = []
        for code in airport_codes:
            airport = self._iata_index.get(code)
            if airport:
                # Filter by country if specified
                if country and airport.country.lower() != country.lower():
                    continue
                airports.append(airport)

        # Put priority airport first if exists
        priority_code = self.priority_city_mappings.get(city_key)
        if priority_code:
            airports.sort(key=lambda a: 0 if a.iata == priority_code else 1)

        return airports

    def get_priority_airport(self, city: str) -> str | None:
        """Get the priority (main) airport code for a city.

        Args:
            city: City name (case-insensitive)

        Returns:
            IATA code of priority airport, or None if no priority defined
        """
        return self.priority_city_mappings.get(_strip_diacritics(city.lower().strip()))

    def search_by_name(self, query: str, limit: int = 10) -> list[Airport]:
        """Search airports by name.

        Args:
            query: Airport name or partial name (e.g., "Heathrow")
            limit: Maximum results to return

        Returns:
            List of matching airports, best matches first
        """
        query_lower = query.lower().strip()
        results: list[tuple[Airport, int]] = []

        # Exact match gets highest score
        if query_lower in self.name_to_code:
            code = self.name_to_code[query_lower]
            airport = self._iata_index.get(code)
            if airport:
                results.append((airport, 100))

        # Partial matches
        for name, code in self.name_to_code.items():
            if query_lower in name and name != query_lower:
                airport = self._iata_index.get(code)
                if airport:
                    # Score based on how much of the name matches
                    score = int(len(query_lower) / len(name) * 50)
                    results.append((airport, score))

        # Sort by score and deduplicate
        results.sort(key=lambda x: x[1], reverse=True)
        seen: set[str] = set()
        unique_results: list[Airport] = []
        for airport, _ in results:
            if airport.iata not in seen:
                seen.add(airport.iata)
                unique_results.append(airport)
                if len(unique_results) >= limit:
                    break

        return unique_results

    def search(self, query: str, limit: int = 10) -> list[Airport]:
        """General search across cities and airport names.

        Args:
            query: Search query (city name, airport name, or partial)
            limit: Maximum results to return

        Returns:
            List of matching airports, best matches first
        """
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        results: list[tuple[Airport, int]] = []

        for airport in self._iata_index.values():
            score = 0
            city_lower = airport.city.lower()
            name_lower = airport.name.lower()

            # Exact city match
            if query_lower in (city_lower, name_lower):
                score = 100
            # Partial city match
            elif query_lower in city_lower or query_lower in name_lower:
                score = 50
            else:
                # Word-based matching — require majority of query words
                # to match.  Without this, "Dominican Republic" falsely
                # matches "Republic Airport" (FRG) via the single word
                # "republic".
                city_words = set(city_lower.split())
                name_words = set(name_lower.split())

                city_overlap = len(query_words & city_words)
                name_overlap = len(query_words & name_words)

                # Bidirectional: how much of query matched AND how much
                # of the target matched.  Prevents "Dominican Republic"
                # from matching "Republic Airport" via a single word.
                if city_overlap > 0:
                    combined = (city_overlap / len(query_words)) * (
                        city_overlap / len(city_words)
                    )
                    if combined > 0.5:
                        score = city_overlap * 20
                elif name_overlap > 0:
                    combined = (name_overlap / len(query_words)) * (
                        name_overlap / len(name_words)
                    )
                    if combined > 0.5:
                        score = name_overlap * 10

            if score > 0:
                results.append((airport, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        return [airport for airport, _ in results[:limit]]

    def find_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: int | None = None,
        limit: int = 10,
    ) -> list[tuple[Airport, float]]:
        """Find airports near coordinates.

        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Optional max radius in kilometers. If None, returns closest airports.
            limit: Maximum number of results

        Returns:
            List of (Airport, distance_km) tuples, sorted by distance
        """
        results: list[tuple[Airport, float]] = []

        for airport in self._iata_index.values():
            distance = self._haversine_distance(lat, lon, airport.lat, airport.lon)

            if radius_km is None or distance <= radius_km:
                results.append((airport, distance))

        # Sort by distance
        results.sort(key=lambda x: x[1])
        return results[:limit]

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in kilometers
        """
        return haversine_km(lat1, lon1, lat2, lon2)

    def get_airport_count(self) -> int:
        """Get total number of airports in the repository."""
        return len(self._iata_index)


__all__ = ["AirportRepository"]
