"""Ticket status string parsing shared by FlightLogic adapters."""

from app.domains.flight.enums import TicketStatus


def parse_ticket_status_from_flightlogic_string(ticket_raw: str) -> TicketStatus:
    """Map FlightLogic TicketStatus string to TicketStatus."""
    ticket_lower = ticket_raw.lower()
    if "cancelled" in ticket_lower:
        return TicketStatus.CANCELLED
    if "not_issued" in ticket_lower or ticket_lower == "unknown":
        # FlightLogic sends literal "Unknown" when the status is undetermined; not yet issued.
        return TicketStatus.NOT_ISSUED
    if "ticketed" in ticket_lower or "issued" in ticket_lower:
        return TicketStatus.TICKETED
    if "process" in ticket_lower or "pending" in ticket_lower:
        return TicketStatus.IN_PROCESS
    return TicketStatus.NOT_ISSUED
