"""Unit tests for authenticated email link URL generation (flight tickets issued, booking confirmation)."""

from unittest.mock import patch

from app.domains.email.builder import EmailBuilder


class TestGetAuthenticatedFrontendUrl:
    """Test _get_authenticated_frontend_url and related helpers."""

    def test_get_authenticated_frontend_url_without_user_id_returns_path_only(self):
        """Without user_id, URL has no auth_token param."""
        with patch.object(
            EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
        ):
            url = EmailBuilder._get_authenticated_frontend_url(
                "/flights/bookings/VOYA-ABC123", user_id=None
            )
        assert url == "https://app.voya.com/flights/bookings/VOYA-ABC123"
        assert "auth_token=" not in url

    def test_get_authenticated_frontend_url_with_user_id_includes_token(self):
        """With user_id, URL includes auth_token query param."""
        with (
            patch.object(
                EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
            ),
            patch.object(
                EmailBuilder,
                "_generate_booking_auth_token",
                return_value="fake_jwt_token",
            ),
        ):
            url = EmailBuilder._get_authenticated_frontend_url(
                "/flights/bookings/VOYA-ABC123", user_id="user_123"
            )
        assert url.startswith("https://app.voya.com/flights/bookings/VOYA-ABC123")
        assert "auth_token=fake_jwt_token" in url or "auth_token=" in url

    def test_get_payment_page_url_uses_frontend_v2_path(self):
        """Payment page URL uses /flights/payment/<ref> (frontend-v2)."""
        with (
            patch.object(
                EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
            ),
            patch.object(
                EmailBuilder,
                "_generate_booking_auth_token",
                return_value="token",
            ),
        ):
            url = EmailBuilder._get_payment_page_url(
                "VOYA-TESTREF01", user_id="user_456"
            )
        assert "/flights/payment/VOYA-TESTREF01" in url  # pragma: allowlist secret
        assert "auth_token=" in url


class TestTicketIssuedEmailLink:
    """Test ticket issued email uses authenticated view-tickets URL."""

    def test_ticket_issued_button_url_contains_flights_bookings_path(self):
        """Ticket issued 'View your tickets' uses /flights/bookings/<ref>."""
        context = {
            "voya_booking_reference": "VOYA-XYZ789",
            "ticket_numbers": ["1234567890"],
            "user_id": "user_789",
        }
        with (
            patch.object(
                EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
            ),
            patch.object(
                EmailBuilder, "_generate_booking_auth_token", return_value="ticket_jwt"
            ),
        ):
            spec = EmailBuilder._build_ticket_issued(context)
        assert "/flights/bookings/VOYA-XYZ789" in spec.button_url
        assert "auth_token=" in spec.button_url

    def test_ticket_issued_without_user_id_still_has_correct_path(self):
        """Without user_id, path is still /flights/bookings/<ref> (no token)."""
        context = {
            "voya_booking_reference": "VOYA-NOTOK",
            "ticket_numbers": [],
        }
        with patch.object(
            EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
        ):
            spec = EmailBuilder._build_ticket_issued(context)
        assert "/flights/bookings/VOYA-NOTOK" in spec.button_url


class TestBookingConfirmationEmailLink:
    """Test booking confirmation (FSC) payment link uses frontend-v2 payment URL."""

    def test_booking_confirmation_fsc_payment_url_format(self):
        """FSC booking confirmation 'Proceed to Checkout' uses /flights/payment/<ref>."""
        context = {
            "user_name": "Test",
            "user_id": "user_fsc",
            "tickets_issued": False,
            "voya_booking_reference": "VOYA-TESTREF01",  # pragma: allowlist secret
            "external_booking_reference": "ext-ref",
            "booking_details": {},
            "total_fare": 199.99,
            "currency": "USD",
        }
        with (
            patch.object(
                EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
            ),
            patch.object(
                EmailBuilder,
                "_generate_booking_auth_token",
                return_value="pay_jwt",  # pragma: allowlist secret
            ),
        ):
            spec = EmailBuilder._build_booking_confirmation(context)
        expected_path = "/flights/payment/VOYA-TESTREF01"  # pragma: allowlist secret
        assert expected_path in spec.button_url
        assert "auth_token=" in spec.button_url


class TestHotelBookingConfirmationEmailLink:
    """Test hotel booking confirmation uses frontend-v2 /hotels/bookings/<ref> URL."""

    def test_hotel_confirmation_uses_frontend_url_with_auth_token(self):
        """Hotel booking confirmation button uses /hotels/bookings/<ref> with auth_token."""
        context = {
            "user_name": "Test",
            "user_id": "user_hotel",
            "voya_booking_reference": "VOYA-HOTEL-2025-00001",
            "external_booking_reference": "SUPP-12345",
            "reference_num": "REF-67890",
            "booking_details": {
                "hotel_id": "H123",
                "hotel_name": "Grand Hotel",
                "check_in": "2025-06-01",
                "check_out": "2025-06-05",
                "total_price": 500.0,
                "currency": "EUR",
            },
        }
        with (
            patch.object(
                EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
            ),
            patch.object(
                EmailBuilder,
                "_generate_booking_auth_token",
                return_value="hotel_jwt",
            ),
        ):
            spec = EmailBuilder._build_booking_confirmation(context)
        assert "/hotels/bookings/VOYA-HOTEL-2025-00001" in spec.button_url
        assert "auth_token=hotel_jwt" in spec.button_url
        assert "/dev/hotel-booker/" not in spec.button_url

    def test_hotel_confirmation_without_user_id_has_no_auth_token(self):
        """Hotel booking confirmation without user_id has no auth_token but correct path."""
        context = {
            "user_name": "Guest",
            "voya_booking_reference": "VOYA-HOTEL-2025-00002",
            "external_booking_reference": "SUPP-99999",
            "reference_num": "REF-11111",
            "booking_details": {
                "hotel_id": "H456",
                "hotel_name": "Budget Inn",
                "check_in": "2025-07-01",
                "check_out": "2025-07-03",
                "total_price": 100.0,
                "currency": "USD",
            },
        }
        with patch.object(
            EmailBuilder, "_get_base_url", return_value="https://app.voya.com"
        ):
            spec = EmailBuilder._build_booking_confirmation(context)
        assert "/hotels/bookings/VOYA-HOTEL-2025-00002" in spec.button_url
        assert "auth_token=" not in spec.button_url
        assert "/dev/hotel-booker/" not in spec.button_url
