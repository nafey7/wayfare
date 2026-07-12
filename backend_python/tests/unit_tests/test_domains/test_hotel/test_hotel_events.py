"""Unit tests for hotel event handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.hotel.events import HotelEventHandler


class TestHandleBookingConfirmed:
    """Test handle_booking_confirmed enrichment logic."""

    @pytest.mark.asyncio
    async def test_enrichment_with_existing_hotel_name(self):
        """Test that enrichment preserves existing hotel_name."""
        user_id = "user_123"
        external_booking_reference = "FL-HOTEL-456"
        booking_details = {
            "hotel_name": "Existing Hotel Name",
            "check_in": "2025-01-15",
        }
        voya_booking_reference = "VOYA-2025-00001"

        mock_user_service = MagicMock()
        mock_user_service.get_user_public = AsyncMock(
            return_value=MagicMock(
                email="test@example.com", first_name="Test", id=user_id
            )
        )

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.domains.hotel.events._get_user_service",
                return_value=mock_user_service,
            ),
            patch("app.domains.hotel.events.EmailService", mock_email_service),
        ):
            await HotelEventHandler.handle_booking_confirmed(
                user_id=user_id,
                external_booking_reference=external_booking_reference,
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
            )

        # Verify email was sent
        assert mock_email_service.send_email.called

        # Verify hotel_name was preserved
        call_args = mock_email_service.send_email.call_args
        context = call_args.kwargs.get("context", {})
        enriched_details = context.get("booking_details", {})
        assert enriched_details.get("hotel_name") == "Existing Hotel Name"

    @pytest.mark.asyncio
    async def test_enrichment_fetches_hotel_name_when_missing(self):
        """Test that enrichment fetches hotel_name from API when missing."""
        user_id = "user_123"
        external_booking_reference = "FL-HOTEL-789"
        reference_num = "REF-123"
        booking_details = {
            "check_in": "2025-02-20",
            # hotel_name is missing
        }
        voya_booking_reference = "VOYA-2025-00002"

        # Mock hotel service response with hotel name
        mock_hotel_service = MagicMock()
        mock_booking_details_response = MagicMock()
        mock_booking_details_response.booking_details = {
            "hotel_name": "Fetched Hotel Name",
        }
        mock_hotel_service.get_booking_details = AsyncMock(
            return_value=mock_booking_details_response
        )

        mock_user_service = MagicMock()
        mock_user_service.get_user_public = AsyncMock(
            return_value=MagicMock(
                email="test@example.com", first_name="Test", id=user_id
            )
        )

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.domains.hotel.events._get_user_service",
                return_value=mock_user_service,
            ),
            patch(
                "app.domains.hotel.events._get_hotel_service",
                return_value=lambda **kwargs: mock_hotel_service,
            ),
            patch("app.domains.hotel.events.EmailService", mock_email_service),
        ):
            await HotelEventHandler.handle_booking_confirmed(
                user_id=user_id,
                external_booking_reference=external_booking_reference,
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
                reference_num=reference_num,
            )

        # Verify hotel service was called
        assert mock_hotel_service.get_booking_details.called

        # Verify email was sent with enriched hotel_name
        assert mock_email_service.send_email.called
        call_args = mock_email_service.send_email.call_args
        context = call_args.kwargs.get("context", {})
        enriched_details = context.get("booking_details", {})
        assert enriched_details.get("hotel_name") == "Fetched Hotel Name"

    @pytest.mark.asyncio
    async def test_enrichment_handles_api_error_gracefully(self):
        """Test that enrichment handles API errors gracefully."""
        user_id = "user_123"
        external_booking_reference = "FL-HOTEL-999"
        reference_num = "REF-456"
        booking_details = {
            "check_in": "2025-03-10",
            # hotel_name is missing
        }
        voya_booking_reference = "VOYA-2025-00003"

        # Mock hotel service to raise an error
        mock_hotel_service = MagicMock()
        mock_hotel_service.get_booking_details = AsyncMock(
            side_effect=Exception("API Error")
        )

        mock_user_service = MagicMock()
        mock_user_service.get_user_public = AsyncMock(
            return_value=MagicMock(
                email="test@example.com", first_name="Test", id=user_id
            )
        )

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.domains.hotel.events._get_user_service",
                return_value=mock_user_service,
            ),
            patch(
                "app.domains.hotel.events._get_hotel_service",
                return_value=lambda **kwargs: mock_hotel_service,
            ),
            patch("app.domains.hotel.events.EmailService", mock_email_service),
        ):
            # Should not raise exception
            await HotelEventHandler.handle_booking_confirmed(
                user_id=user_id,
                external_booking_reference=external_booking_reference,
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
                reference_num=reference_num,
            )

        # Verify email was still sent (enrichment failure shouldn't block email)
        assert mock_email_service.send_email.called

        # Verify booking_details were copied (enrichment failed but fallback applied)
        call_args = mock_email_service.send_email.call_args
        context = call_args.kwargs.get("context", {})
        enriched_details = context.get("booking_details", {})
        assert "check_in" in enriched_details
        assert (
            enriched_details.get("hotel_name") == "Your Hotel"
        )  # Fallback when API errors

    @pytest.mark.asyncio
    async def test_enrichment_skips_when_no_reference_num(self):
        """Test that enrichment is skipped when reference_num is missing."""
        user_id = "user_123"
        external_booking_reference = "FL-HOTEL-111"
        booking_details = {
            "check_in": "2025-04-01",
            # hotel_name is missing
        }
        voya_booking_reference = "VOYA-2025-00004"
        # reference_num is None

        mock_user_service = MagicMock()
        mock_user_service.get_user_public = AsyncMock(
            return_value=MagicMock(
                email="test@example.com", first_name="Test", id=user_id
            )
        )

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.domains.hotel.events._get_user_service",
                return_value=mock_user_service,
            ),
            patch("app.domains.hotel.events.EmailService", mock_email_service),
        ):
            await HotelEventHandler.handle_booking_confirmed(
                user_id=user_id,
                external_booking_reference=external_booking_reference,
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
                reference_num=None,  # Missing reference_num
            )

        # Verify email was sent
        assert mock_email_service.send_email.called

        # Verify booking_details were copied with fallback (no enrichment when no reference_num)
        call_args = mock_email_service.send_email.call_args
        context = call_args.kwargs.get("context", {})
        enriched_details = context.get("booking_details", {})
        assert "check_in" in enriched_details
        assert (
            enriched_details.get("hotel_name") == "Your Hotel"
        )  # Fallback for email template

    @pytest.mark.asyncio
    async def test_enrichment_handles_empty_api_response(self):
        """Test that enrichment handles empty API response gracefully."""
        user_id = "user_123"
        external_booking_reference = "FL-HOTEL-222"
        reference_num = "REF-789"
        booking_details = {
            "check_in": "2025-05-15",
            # hotel_name is missing
        }
        voya_booking_reference = "VOYA-2025-00005"

        # Mock hotel service response with no booking_details
        mock_hotel_service = MagicMock()
        mock_booking_details_response = MagicMock()
        mock_booking_details_response.booking_details = None
        mock_hotel_service.get_booking_details = AsyncMock(
            return_value=mock_booking_details_response
        )

        mock_user_service = MagicMock()
        mock_user_service.get_user_public = AsyncMock(
            return_value=MagicMock(
                email="test@example.com", first_name="Test", id=user_id
            )
        )

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.domains.hotel.events._get_user_service",
                return_value=mock_user_service,
            ),
            patch(
                "app.domains.hotel.events._get_hotel_service",
                return_value=lambda **kwargs: mock_hotel_service,
            ),
            patch("app.domains.hotel.events.EmailService", mock_email_service),
        ):
            await HotelEventHandler.handle_booking_confirmed(
                user_id=user_id,
                external_booking_reference=external_booking_reference,
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
                reference_num=reference_num,
            )

        # Verify email was still sent
        assert mock_email_service.send_email.called

        # Verify booking_details were copied with fallback (empty API response)
        call_args = mock_email_service.send_email.call_args
        context = call_args.kwargs.get("context", {})
        enriched_details = context.get("booking_details", {})
        assert "check_in" in enriched_details
        assert (
            enriched_details.get("hotel_name") == "Your Hotel"
        )  # Fallback when API returns empty
