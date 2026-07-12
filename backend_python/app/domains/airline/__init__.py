"""Airline domain module.

Provides airline information resolution and lookups.
"""

from .airline_resolver import get_airline_display_name, get_airline_name

__all__ = ["get_airline_display_name", "get_airline_name"]
