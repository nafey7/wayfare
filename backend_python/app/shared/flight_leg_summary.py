"""Flight leg snapshot model (shared by DB, bookings domain, flight API schemas)."""

from datetime import date

from pydantic import BaseModel, Field


class FlightLegSummary(BaseModel):
    """One booked origin–destination leg (trip_details → booking_events / list APIs)."""

    departure_date: date = Field(
        ...,
        description="UTC calendar date of the first segment's departure on this leg",
    )
    origin_iata: str = Field(..., min_length=3, max_length=3)
    destination_iata: str = Field(..., min_length=3, max_length=3)
