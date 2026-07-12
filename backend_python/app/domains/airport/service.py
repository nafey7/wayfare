"""Airport service for unified resolution with geocoding.

This module provides the main entry point for resolving user location input
to airports. It orchestrates the AirportRepository with GeocodingService
to handle all disambiguation scenarios:

- MULTI_CITY: Same city name in multiple countries (Birmingham UK vs USA)
- MULTI_AIRPORT: City has multiple airports (London → LHR, LGW, STN...)
- CODE_VS_CITY: Input matches both IATA code and city name (GOA)

Usage:
    from app.domains.airport import get_airport_service

    service = get_airport_service()
    result = await service.resolve("Birmingham")

    if result.status == "needs_disambiguation":
        # Present options to user
        print(result.suggested_prompt)
    elif result.status == "resolved":
        print(f"Resolved to {result.airport.iata}")
"""

import logging

from app.domains.airport.models import (
    Airport,
    AirportOption,
    AirportResolution,
    DisambiguationType,
    ResolveContext,
)
from app.domains.airport.repository import AirportRepository
from app.shared.geocoding import GeocodingResult, GeocodingService

logger = logging.getLogger(__name__)

_CITY_SUFFIXES = (" city", " town", " metro", " municipality", " province")


class AirportService:
    """Orchestrates airport resolution with geocoding integration.

    This service provides a unified interface for resolving location strings
    to airports, handling all disambiguation scenarios automatically.

    The resolution strategy follows this order:
    1. Exact IATA code (3 letters)
    2. Exact ICAO code (4 letters)
    3. Airport name match (full or partial)
    4. City name (with geocoding for ambiguous cities)
    5. Fuzzy/partial match fallback

    Attributes:
        repository: AirportRepository for data access
        geocoding: GeocodingService for city disambiguation
    """

    def __init__(
        self,
        repository: AirportRepository,
        geocoding: GeocodingService,
    ) -> None:
        """Initialize the airport service.

        Args:
            repository: AirportRepository for airport lookups
            geocoding: GeocodingService for city disambiguation
        """
        self.repository = repository
        self.geocoding = geocoding

    async def resolve(
        self,
        query: str,
        context: ResolveContext | None = None,
    ) -> AirportResolution:
        """Resolve user location input to airport(s).

        This is the main entry point. It handles:
        - Direct IATA/ICAO codes
        - Airport names
        - City names (with geocoding for ambiguous cities)
        - Multi-airport cities

        Args:
            query: User input (city name, airport code, or airport name)
            context: Optional context hints (country_hint, prefer_major_airports)

        Returns:
            AirportResolution with status and disambiguation info if needed

        Examples:
            # Simple IATA code
            await service.resolve("LHR")
            # → resolved, airport=LHR

            # Ambiguous city
            await service.resolve("Birmingham")
            # → needs_disambiguation, options=[UK, USA]

            # With country hint (after user selects)
            await service.resolve("Birmingham", ResolveContext(country_hint="United Kingdom"))
            # → resolved, airport=BHX

            # Multi-airport city
            await service.resolve("London")
            # → resolved, airport=LHR, all_airports=[LHR,LGW,STN...], needs_airport_preference=True
        """
        await self.repository.ensure_loaded()

        if not query:
            return AirportResolution(status="not_found", original_query=query)

        query = query.strip()

        # Check again after stripping whitespace
        if not query:
            return AirportResolution(status="not_found", original_query="")

        query_upper = query.upper()

        # Strategy 1: Exact IATA code (3 letters)
        if len(query) == 3 and query.isalpha():
            airport = self.repository.get_by_iata(query_upper)
            if airport:
                # Check for CODE_VS_CITY ambiguity (e.g., "GOA")
                code_vs_city = await self._check_code_vs_city(query, airport)
                if code_vs_city:
                    return code_vs_city

                return AirportResolution(
                    status="resolved",
                    airport=airport,
                    all_airports=[airport],
                    original_query=query,
                )

        # Strategy 2: Exact ICAO code (4 letters)
        if len(query) == 4 and query.isalpha():
            airport = self.repository.get_by_icao(query_upper)
            if airport:
                return AirportResolution(
                    status="resolved",
                    airport=airport,
                    all_airports=[airport],
                    original_query=query,
                )

        # Strategy 3: Check for strong airport name matches first
        # This handles queries like "Heathrow" which should resolve to LHR
        # before geocoding tries to find a city called "Heathrow"
        name_matches = self.repository.search_by_name(query, limit=5)
        if len(name_matches) == 1:
            # Before auto-resolving, check if the query is also a city name
            # with airports in multiple countries. e.g. "Venice" matches
            # "Venice Municipal Airport" (VNC/US) by name, but the city
            # "Venice" also has VCE (IT). Don't let a partial name match
            # short-circuit multi-country disambiguation.
            city_codes = self.repository.city_to_airports.get(query.lower().strip(), [])
            if len(city_codes) > 1:
                city_airports = [
                    self.repository.get_by_iata(c)
                    for c in city_codes
                    if self.repository.get_by_iata(c)
                ]
                countries = {a.country for a in city_airports if a}
                if len(countries) > 1:
                    # City name spans countries — skip name match,
                    # fall through to city-based resolution (Strategy 4)
                    pass
                else:
                    return AirportResolution(
                        status="resolved",
                        airport=name_matches[0],
                        all_airports=[name_matches[0]],
                        original_query=query,
                    )
            else:
                # Single strong match, no multi-country conflict
                return AirportResolution(
                    status="resolved",
                    airport=name_matches[0],
                    all_airports=[name_matches[0]],
                    original_query=query,
                )

        # Strategy 4: City-based resolution (with geocoding)
        # This handles city names like "New York" which have multiple airports
        city_resolution = await self._resolve_city(query, context)
        if city_resolution:
            return city_resolution

        # Strategy 5: Multiple airport name matches - return best match
        if name_matches:
            return AirportResolution(
                status="resolved",
                airport=name_matches[0],
                all_airports=name_matches[:1],
                original_query=query,
            )

        # Strategy 6: Fuzzy match fallback
        fuzzy_matches = self.repository.search(query, limit=5)
        if fuzzy_matches:
            return AirportResolution(
                status="resolved",
                airport=fuzzy_matches[0],
                all_airports=fuzzy_matches[:1],
                original_query=query,
            )

        # No match found
        logger.warning(f"No airport found for query: {query}")
        return AirportResolution(status="not_found", original_query=query)

    async def _check_code_vs_city(
        self, query: str, iata_airport: Airport
    ) -> AirportResolution | None:
        """Check if query matches both IATA code and city name.

        Example: "GOA" is both an IATA code (Genoa) and city name (Goa, India).

        Args:
            query: Original query (3 letters)
            iata_airport: Airport matched by IATA code

        Returns:
            AirportResolution for disambiguation, or None if no ambiguity
        """
        # Check if this could also be a city name
        geocoding_results = await self.geocoding.geocode_city(query)

        if not geocoding_results:
            return None

        # Check if any geocoding result is in a different location than the IATA match
        for geo_result in geocoding_results:
            # If the geocoded city is in a different country, we have ambiguity
            # Compare using ISO codes (airport data uses ISO, geocoding provides country_code)
            if geo_result.country_code.upper() != iata_airport.country.upper():
                # Find airports for the geocoded city
                city_airports = self.repository.get_by_city(
                    geo_result.city, geo_result.country_code
                )

                if city_airports:
                    # Build disambiguation options
                    options = [
                        AirportOption(
                            display_name=f"{iata_airport.city}, {iata_airport.country} ({iata_airport.iata})",
                            airports=[iata_airport],
                            match_type="iata",
                            confidence=1.0,
                        ),
                        AirportOption(
                            display_name=f"{geo_result.city}, {geo_result.country}",
                            airports=city_airports,
                            match_type="city",
                            confidence=0.9,
                        ),
                    ]

                    prompt = self._build_prompt(
                        options, DisambiguationType.CODE_VS_CITY
                    )

                    logger.info(
                        f"CODE_VS_CITY ambiguity for '{query}': "
                        f"{iata_airport.iata} ({iata_airport.country}) vs "
                        f"{geo_result.city} ({geo_result.country})"
                    )

                    return AirportResolution(
                        status="needs_disambiguation",
                        disambiguation_type=DisambiguationType.CODE_VS_CITY,
                        options=options,
                        suggested_prompt=prompt,
                        original_query=query,
                    )

        return None

    async def _resolve_city(
        self, query: str, context: ResolveContext | None
    ) -> AirportResolution | None:
        """Resolve query as a city name with geocoding.

        Args:
            query: City name to resolve
            context: Resolution context with hints

        Returns:
            AirportResolution or None if not resolved
        """
        # If we have a country hint, try direct lookup first
        if context and context.country_hint:
            airports = self.repository.get_by_city(query, context.country_hint)
            if airports:
                return self._build_city_resolution(airports, query)

        # Use geocoding to find the city
        geocoding_results = await self.geocoding.geocode_city(query)

        if not geocoding_results:
            # Try direct city lookup without geocoding
            airports = self.repository.get_by_city(query)
            if airports:
                # Check if airports span multiple countries — if so,
                # disambiguate instead of silently picking the first one.
                # e.g. "Venice" has VNC (Florida, US) and VCE (Italy) —
                # without this guard the first one wins arbitrarily.
                countries = {a.country for a in airports}
                if len(countries) > 1:
                    return self._build_multi_country_from_airports(airports, query)
                return self._build_city_resolution(airports, query)
            return None

        # Guard: If Google says this is a country (not a city), don't resolve.
        # e.g., "Costa Rica" → types=["country","political"] — no "locality".
        if all(
            "country" in r.result_types and "locality" not in r.result_types
            for r in geocoding_results
        ):
            logger.info(
                "Query '%s' is a country (geocoding types=%s) — returning not_found",
                query,
                geocoding_results[0].result_types,
            )
            return AirportResolution(status="not_found", original_query=query)

        # Check for MULTI_CITY ambiguity (same city name, different countries)
        unique_countries = {r.country for r in geocoding_results}
        if len(unique_countries) > 1:
            return self._build_multi_city_resolution(geocoding_results, query)

        geo_result = geocoding_results[0]
        all_airports = self.repository.get_by_city(geo_result.city)

        # Filter by country to exclude same-named cities in other countries
        # (e.g., London UK vs London Ontario CA)
        # Compare both country name and country_code for compatibility
        # (Airport data may use ISO codes "FR" or full names "France")
        airports = [
            a
            for a in all_airports
            if (
                a.country.lower() == geo_result.country.lower()
                or a.country.lower() == geo_result.country_code.lower()
            )
        ]

        # Also filter out military/non-commercial airports
        airports = [
            a
            for a in airports
            if not any(
                term in a.name.lower()
                for term in ["raf ", "afb ", "air force", "air base", "military"]
            )
        ]

        if airports:
            return self._build_city_resolution(airports, query)

        # Retry with stripped city-suffix variants (e.g. "Tacloban City" → "Tacloban").
        # Geocoding APIs often append "City"/"Town"/"Metro" that the airport DB doesn't use.
        geo_city_lower = geo_result.city.lower()
        for suffix in _CITY_SUFFIXES:
            if geo_city_lower.endswith(suffix):
                stripped_city = geo_result.city[: -len(suffix)].strip()
                retry_airports = self.repository.get_by_city(stripped_city)
                retry_airports = [
                    a
                    for a in retry_airports
                    if (
                        a.country.lower() == geo_result.country.lower()
                        or a.country.lower() == geo_result.country_code.lower()
                    )
                    and not any(
                        term in a.name.lower()
                        for term in [
                            "raf ",
                            "afb ",
                            "air force",
                            "air base",
                            "military",
                        ]
                    )
                ]
                if retry_airports:
                    logger.info(
                        "City suffix strip: '%s' -> '%s', found %s",
                        geo_result.city,
                        stripped_city,
                        [a.iata for a in retry_airports],
                    )
                    return self._build_city_resolution(retry_airports, query)
                break  # Only try the first matching suffix

        # No airports in city - find nearby airports using geocoding coordinates
        # This handles cases like Utrecht (no airport, but AMS is ~35km away)
        # 250km radius covers island nations where the main international hub
        # may be far from smaller islands (e.g. Vaadhoo Island → Malé = 159km)
        if geo_result.lat and geo_result.lng:
            nearby = self.repository.find_nearby(
                geo_result.lat, geo_result.lng, radius_km=250, limit=10
            )
            if nearby:
                # Filter out military/non-commercial airports from nearby results
                # and keep distance info for later use
                military_terms = ["raf ", "afb ", "air force", "air base", "military"]
                nearby_pairs = [
                    (airport, dist)
                    for airport, dist in nearby
                    if not any(term in airport.name.lower() for term in military_terms)
                ]
                if nearby_pairs:
                    nearby_airports = [airport for airport, _ in nearby_pairs]
                    logger.info(
                        f"No airport in {geo_result.city}, using nearby: "
                        f"{[(a.iata, f'{d:.0f}km') for a, d in nearby_pairs[:3]]}"
                    )
                    resolution = self._build_city_resolution(nearby_airports, query)
                    resolution.is_nearby_fallback = True
                    return resolution

        return None

    def _build_city_resolution(
        self, airports: list[Airport], query: str
    ) -> AirportResolution:
        """Build resolution for a city with one or more airports.

        Args:
            airports: List of airports in the city
            query: Original query

        Returns:
            AirportResolution (resolved, possibly with needs_airport_preference)
        """
        primary_airport = airports[0]  # Already sorted with priority first
        needs_preference = len(airports) > 1

        if needs_preference:
            logger.info(f"MULTI_AIRPORT city '{query}': {[a.iata for a in airports]}")

        return AirportResolution(
            status="resolved",
            airport=primary_airport,
            all_airports=airports,
            needs_airport_preference=needs_preference,
            disambiguation_type=DisambiguationType.MULTI_AIRPORT
            if needs_preference
            else None,
            original_query=query,
        )

    def _build_multi_city_resolution(
        self, geocoding_results: list[GeocodingResult], query: str
    ) -> AirportResolution:
        """Build disambiguation resolution for multi-city scenario.

        Handles both different-country (Birmingham UK vs USA) and same-country
        different-state (Springfield IL vs MA vs MO) ambiguities.

        Args:
            geocoding_results: Geocoding results (may include same-country cities)
            query: Original query

        Returns:
            AirportResolution with disambiguation options
        """
        options: list[AirportOption] = []
        seen_locations: set[str] = set()

        for geo_result in geocoding_results:
            # Use formatted_address for deduplication to handle same-country cities
            # (e.g., Springfield, IL vs Springfield, MA vs Springfield, MO)
            location_key = geo_result.formatted_address
            if location_key in seen_locations:
                continue
            seen_locations.add(location_key)

            # For same-country cities (like Springfield in different US states),
            # we need to use coordinates to find nearby airports rather than
            # city/country lookup (which would return all same-named cities)
            airports: list[Airport] = []

            # First, try city/country lookup (use ISO code for country)
            city_airports = self.repository.get_by_city(
                geo_result.city, geo_result.country_code
            )

            if city_airports:
                # If there are multiple locations in same country, filter by proximity
                # (50km radius from geocoded coordinates)
                if len(geocoding_results) > 1 and geo_result.lat and geo_result.lng:
                    same_country_count = sum(
                        1 for r in geocoding_results if r.country == geo_result.country
                    )
                    if same_country_count > 1:
                        # Use nearby search to get airports for this specific location
                        nearby = self.repository.find_nearby(
                            geo_result.lat, geo_result.lng, radius_km=100, limit=5
                        )
                        airports = [airport for airport, _ in nearby]
                    else:
                        airports = city_airports
                else:
                    airports = city_airports

            # Fallback to nearby if no direct match
            if not airports and geo_result.lat and geo_result.lng:
                nearby = self.repository.find_nearby(
                    geo_result.lat, geo_result.lng, radius_km=100, limit=5
                )
                airports = [airport for airport, _ in nearby]

            if airports:
                options.append(
                    AirportOption(
                        display_name=geo_result.formatted_address,
                        airports=airports,
                        match_type="city",
                        confidence=1.0,
                    )
                )

        if len(options) <= 1:
            # Not actually ambiguous, return resolved
            if options:
                return self._build_city_resolution(options[0].airports, query)
            return AirportResolution(status="not_found", original_query=query)

        prompt = self._build_prompt(options, DisambiguationType.MULTI_CITY)

        logger.info(
            f"MULTI_CITY ambiguity for '{query}': "
            f"{[opt.display_name for opt in options]}"
        )

        return AirportResolution(
            status="needs_disambiguation",
            disambiguation_type=DisambiguationType.MULTI_CITY,
            options=options,
            suggested_prompt=prompt,
            original_query=query,
        )

    def _build_multi_country_from_airports(
        self, airports: list[Airport], query: str
    ) -> AirportResolution:
        """Build disambiguation when a city name has airports in multiple countries.

        This is the fallback path when geocoding is unavailable. Groups airports
        by country and asks the user which country they meant.

        Example: "Venice" → VNC (US) vs VCE (IT) → ask user.
        """
        # Group airports by country
        country_groups: dict[str, list[Airport]] = {}
        for airport in airports:
            country_groups.setdefault(airport.country, []).append(airport)

        options: list[AirportOption] = []
        for country, country_airports in country_groups.items():
            # Use the first airport's city for the display name
            city = country_airports[0].city
            options.append(
                AirportOption(
                    display_name=f"{city}, {country}",
                    airports=country_airports,
                    match_type="city",
                    confidence=1.0,
                )
            )

        if len(options) <= 1:
            # Only one country after grouping — not ambiguous
            if options:
                return self._build_city_resolution(options[0].airports, query)
            return AirportResolution(status="not_found", original_query=query)

        prompt = self._build_prompt(options, DisambiguationType.MULTI_CITY)

        logger.info(
            "MULTI_COUNTRY fallback for '%s': %s",
            query,
            [opt.display_name for opt in options],
        )

        return AirportResolution(
            status="needs_disambiguation",
            disambiguation_type=DisambiguationType.MULTI_CITY,
            options=options,
            suggested_prompt=prompt,
            original_query=query,
        )

    def _build_prompt(
        self, options: list[AirportOption], disambiguation_type: DisambiguationType
    ) -> str:
        """Build a user-friendly prompt for disambiguation.

        Args:
            options: Disambiguation options
            disambiguation_type: Type of disambiguation

        Returns:
            Formatted prompt string
        """
        if disambiguation_type == DisambiguationType.CODE_VS_CITY:
            header = "Did you mean the airport code or the city?"
        elif disambiguation_type == DisambiguationType.MULTI_CITY:
            header = "Which city did you mean?"
        else:
            header = "Which option did you mean?"

        lines = [header]
        for i, option in enumerate(options, 1):
            # Add airport codes if available
            if option.airports:
                codes = "/".join(a.iata for a in option.airports[:3])
                if len(option.airports) > 3:
                    codes += "/..."
                lines.append(f"  {i}. {option.display_name} ({codes})")
            else:
                lines.append(f"  {i}. {option.display_name}")

        return "\n".join(lines)

    def get_airports_in_city(
        self, city: str, country: str | None = None
    ) -> list[Airport]:
        """Get all airports serving a city.

        Args:
            city: City name
            country: Optional country filter

        Returns:
            List of airports in the city
        """
        return self.repository.get_by_city(city, country)

    def get_nearby_airports(
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
            radius_km: Optional max radius. If None, returns closest airports.
            limit: Maximum results

        Returns:
            List of (Airport, distance_km) tuples, sorted by distance
        """
        return self.repository.find_nearby(lat, lon, radius_km, limit)


__all__ = ["AirportService"]
