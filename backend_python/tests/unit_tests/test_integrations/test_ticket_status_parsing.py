"""Unit tests for ticket status parsing in FlightLogic adapters.

Part of PLAN_GDS_TICKET_STATUS_GATE: ensure cancelled maps to TicketStatus.CANCELLED.
"""

from app.domains.flight.enums import TicketStatus
from integrations.flightlogic.adapter import FlightLogicSchemaAdapter


class TestParseTicketStatusCancelled:
    """Test that both adapters map 'Cancelled' to TicketStatus.CANCELLED."""

    def test_main_adapter_parse_ticket_status_cancelled(self) -> None:
        """Main adapter maps 'Cancelled' and 'cancelled' to TicketStatus.CANCELLED."""
        adapter = FlightLogicSchemaAdapter()
        assert (
            adapter._parse_ticket_status({"TicketStatus": "Cancelled"})
            == TicketStatus.CANCELLED
        )
        assert (
            adapter._parse_ticket_status({"TicketStatus": "cancelled"})
            == TicketStatus.CANCELLED
        )
        assert (
            adapter._parse_ticket_status({"TicketStatus": "CANCELLED"})
            == TicketStatus.CANCELLED
        )

    def test_main_adapter_parse_ticket_status_ticketed_issued(self) -> None:
        """Main adapter still maps ticketed/issued to TICKETED."""
        adapter = FlightLogicSchemaAdapter()
        assert (
            adapter._parse_ticket_status({"TicketStatus": "Ticketed"})
            == TicketStatus.TICKETED
        )
        assert (
            adapter._parse_ticket_status({"TicketStatus": "issued"})
            == TicketStatus.TICKETED
        )

    def test_main_adapter_parse_ticket_status_in_process(self) -> None:
        """Main adapter maps process/pending to IN_PROCESS."""
        adapter = FlightLogicSchemaAdapter()
        assert (
            adapter._parse_ticket_status({"TicketStatus": "TktInProcess"})
            == TicketStatus.IN_PROCESS
        )
        assert (
            adapter._parse_ticket_status({"TicketStatus": "pending"})
            == TicketStatus.IN_PROCESS
        )

    def test_main_adapter_parse_ticket_status_not_issued(self) -> None:
        """Main adapter defaults to NOT_ISSUED for unknown values."""
        adapter = FlightLogicSchemaAdapter()
        assert (
            adapter._parse_ticket_status({"TicketStatus": "not_issued"})
            == TicketStatus.NOT_ISSUED
        )
        assert (
            adapter._parse_ticket_status({"TicketStatus": "Unknown"})
            == TicketStatus.NOT_ISSUED
        )
        assert adapter._parse_ticket_status({}) == TicketStatus.NOT_ISSUED

    def test_trip_details_adapter_parse_ticket_status_cancelled(self) -> None:
        """Trip details adapter maps 'Cancelled' to TicketStatus.CANCELLED via full parse."""
        from integrations.flightlogic.trip_details_adapter import _parse_ticket_status

        assert (
            _parse_ticket_status({"TicketStatus": "Cancelled"})
            == TicketStatus.CANCELLED
        )
        assert (
            _parse_ticket_status({"TicketStatus": "cancelled"})
            == TicketStatus.CANCELLED
        )
