"""Google Places API (New) integration.

Provides:
- Text Search API for place discovery (by name/query)
- Place Photos API for image retrieval (proxied through backend to keep API key hidden)
"""

from .client import GooglePlacesClient, get_places_client

__all__ = ["GooglePlacesClient", "get_places_client"]
