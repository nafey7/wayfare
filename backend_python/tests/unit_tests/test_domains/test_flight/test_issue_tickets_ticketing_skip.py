"""Tests for issue_tickets when FlightLogic trip details already show TICKETED."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.bookings import BookingService
from app.domains.common import AuthProvider
from app.domains.flight.enums import FlightAPIEnvironment, TicketStatus
from app.domains.flight.schemas import TicketOrderRequest
from app.domains.flight.service import FlightService
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


def _minimal_user() -> UserPublic:
    now = datetime.now(UTC)
    return UserPublic(
        id="user-issue-ticket-test",
        email="test@example.com",
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
class TestIssueTicketsTicketingSkip:
    """When trip_details.ticket_status is TICKETED, FlightLogic issue API is not called."""

    async def test_skips_client_issue_tickets_when_already_ticketed(self) -> None:
        user = _minimal_user()
        service = FlightService(current_user=user)
        mock_client = MagicMock()
        mock_client.issue_tickets = AsyncMock()
        service.client = mock_client

        trip = MagicMock()
        trip.fare_type = MagicMock(value="Public")
        trip.ticket_status = TicketStatus.TICKETED
        trip.environment = FlightAPIEnvironment.TEST

        with (
            patch.object(
                BookingService,
                "validate_user_owns_booking",
                new_callable=AsyncMock,
            ),
            patch.object(
                FlightService,
                "_ensure_external_reference",
                new_callable=AsyncMock,
                return_value="EXT-REF-1",
            ),
            patch.object(
                BookingService,
                "get_latest_booking_by_voya_reference",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                FlightService,
                "get_trip_details",
                new_callable=AsyncMock,
                return_value=trip,
            ),
        ):
            req = TicketOrderRequest(
                voya_booking_reference="VOYA-1",
                payment_id="pi_test_1234567890",
            )
            resp = await service.issue_tickets(req)

        assert resp.success is True
        mock_client.issue_tickets.assert_not_called()
