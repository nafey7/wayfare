"""City resolution tool for LangGraph hotel agent.

This tool wraps the GeocodingService to resolve city names to
city/country pairs needed for hotel search.
"""

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ResolveCityInput(BaseModel):
    """Input schema for city resolution."""

    query: str = Field(
        description="City name or location to resolve (e.g., 'Paris', 'Birmingham', 'New York')"
    )


@tool("resolve_city", args_schema=ResolveCityInput)
async def resolve_city(query: str) -> dict[str, Any]:
    """Resolve a city name to city/country for hotel search.

    Use this tool to:
    1. Validate a city exists
    2. Get the country name for the city
    3. Handle ambiguous city names (e.g., Birmingham UK vs Birmingham USA)

    Returns:
    - status: "resolved" | "needs_disambiguation" | "not_found"
    - If resolved: city, country, country_code, lat, lng
    - If needs_disambiguation: options list with city/country pairs
    - If not_found: instruction to ask user for clarification
    """
    from app.shared.geocoding import GeocodingService

    service = GeocodingService()
    results = await service.geocode_city(query)

    if not results:
        return {
            "status": "not_found",
            "query": query,
            "instruction": "Ask the user to clarify the city name or check for spelling errors.",
        }

    # Check if we have multiple distinct cities (different countries or regions)
    if len(results) > 1:
        # Check if all results are in the same country
        countries = {r.country for r in results}
        if len(countries) > 1:
            # Multiple countries - needs disambiguation
            options = [
                {
                    "city": r.city,
                    "country": r.country,
                    "country_code": r.country_code,
                    "formatted_address": r.formatted_address,
                }
                for r in results[:5]  # Limit to 5 options
            ]
            return {
                "status": "needs_disambiguation",
                "query": query,
                "options": options,
                "instruction": "Present these options to the user and ask which one they meant.",
            }

    # Single result or all in same country - use first result
    result = results[0]
    return {
        "status": "resolved",
        "city": result.city,
        "country": result.country,
        "country_code": result.country_code,
        "lat": result.lat,
        "lng": result.lng,
        "formatted_address": result.formatted_address,
        "instruction": f"City resolved: {result.city}, {result.country}. Proceed with hotel search using this city/country pair.",
    }


__all__ = ["ResolveCityInput", "resolve_city"]
