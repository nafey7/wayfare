"""FlightLogic API integration package.

Minimal integration for FlightLogic flight booking API and Hotel API v6.
"""

from .client import FlightLogicClient, get_flights_client
from .hotel_adapter import HotelSchemaAdapter
from .hotel_dto import (
    HotelBookingRequestDTO,
    HotelBookingResponseDTO,
    HotelItineraryDTO,
    HotelRoomRatesRequestDTO,
    HotelRoomRatesResponseDTO,
    HotelSearchRequestDTO,
    HotelSearchResponseDTO,
    OccupancyDTO,
)

__all__ = [
    "FlightLogicClient",
    "HotelBookingRequestDTO",
    "HotelBookingResponseDTO",
    "HotelItineraryDTO",
    "HotelRoomRatesRequestDTO",
    "HotelRoomRatesResponseDTO",
    "HotelSchemaAdapter",
    "HotelSearchRequestDTO",
    "HotelSearchResponseDTO",
    "OccupancyDTO",
    "get_flights_client",
]
