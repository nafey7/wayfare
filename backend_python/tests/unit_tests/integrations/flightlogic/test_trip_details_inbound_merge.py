"""TripDetailsResultInbound is merged into outbound FlightSegments (Indian domestic RT)."""

from integrations.flightlogic.adapter import FlightLogicSchemaAdapter


def test_merge_inbound_appends_reservation_items() -> None:
    adapter = FlightLogicSchemaAdapter()
    booking_data: dict = {
        "FlightSegments": [{"DepartureAirportLocationCode": "DEL", "idx": 0}]
    }
    adapter._merge_trip_details_inbound_segments(
        booking_data,
        trip_response={
            "TripDetailsResultInbound": {
                "TravelItinerary": {
                    "ItineraryInfo": {
                        "ReservationItems": [
                            {"ReservationItem": {"DepartureAirportLocationCode": "BOM"}}
                        ]
                    }
                }
            }
        },
    )
    assert len(booking_data["FlightSegments"]) == 2
    assert booking_data["FlightSegments"][1]["DepartureAirportLocationCode"] == "BOM"


def test_merge_inbound_from_dto_root() -> None:
    adapter = FlightLogicSchemaAdapter()
    from integrations.flightlogic.dto import FlightLogicTripDetailsResponse

    dto = FlightLogicTripDetailsResponse.model_validate(
        {
            "TripDetailsResult": {
                "UniqueID": "U1",
                "FlightSegments": [{"DepartureAirportLocationCode": "DEL"}],
            },
            "TripDetailsResultInbound": {
                "Segments": [{"DepartureAirportLocationCode": "BLR"}],
            },
        }
    )
    data = adapter._extract_booking_data(dto)
    assert len(data.get("FlightSegments", [])) == 2
