"""Tests for hotel my-bookings list mapping."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.common.enums import AuthProvider
from app.domains.hotel.service import HotelService, _mongo_doc_to_hotel_my_booking
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

_TS = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439022",  # pragma: allowlist secret
        email="h@example.com",
        first_name="H",
        last_name="Otel",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=_TS,
        updated_at=_TS,
    )


def test_mongo_doc_to_hotel_my_booking_includes_image_and_name() -> None:
    doc = {
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "voya_booking_reference": "VOYA-H1",
        "external_booking_reference": "CONF1",
        "action": "BOOKED",
        "timestamp": _TS,
        "event_type": "HOTEL",
        "hotel_image_url": "https://img.example/h.jpg",
        "hotel_name": "Grand Test",
        "hotel_city": "Barcelona",
        "amount": 420.0,
        "hotel_check_in_date": "2026-06-01",
        "hotel_check_out_date": "2026-06-05",
        "hotel_nights": 4,
    }
    item = _mongo_doc_to_hotel_my_booking(doc)
    assert item.hotel_image_url == "https://img.example/h.jpg"
    assert item.hotel_name == "Grand Test"
    assert item.hotel_city == "Barcelona"
    assert item.hotel_check_in_date == "2026-06-01"
    assert item.hotel_check_out_date == "2026-06-05"
    assert item.hotel_nights == 4


@pytest.mark.asyncio
@patch("app.domains.hotel.service.get_database")
async def test_get_user_bookings_hotel_filters_event_type(
    mock_get_database, sample_user: UserPublic
) -> None:
    mock_coll = Mock()
    mock_cursor = Mock()
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_cursor.sort = Mock(return_value=mock_cursor)
    mock_cursor.limit = Mock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_db = {"booking_events": mock_coll}
    mock_get_database.return_value = mock_db

    service = HotelService(current_user=sample_user)
    await service.get_user_bookings(limit=3)

    call_query = mock_coll.find.call_args[0][0]
    assert call_query["event_type"] == "HOTEL"
    assert call_query["user_id"] == {"$in": [ObjectId(sample_user.id), sample_user.id]}


@pytest.mark.asyncio
async def test_get_user_bookings_hotel_requires_user() -> None:
    service = HotelService(current_user=None)
    with pytest.raises(ValueError, match="Authentication required"):
        await service.get_user_bookings(limit=1)
