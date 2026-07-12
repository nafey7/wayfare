"""Booking + G2A voucher integration (Phase 4: persist, redeem, release)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.bookings import BookingService, CreateBookingEventRequest
from app.domains.bookings.constants import TEMP_EXTERNAL_REF
from app.domains.discount.constants import VoucherStatus
from app.domains.discount.models import DiscountDoc
from app.domains.discount.service import DiscountService
from app.domains.payment.webhook_service import PaymentWebhookService


@pytest.fixture
def mock_booking_db():
    mock_collection = Mock()
    mock_collection.insert_one = AsyncMock(
        return_value=Mock(
            inserted_id=ObjectId("507f1f77bcf86cd799439011")
        )  # pragma: allowlist secret
    )
    return {"booking_events": mock_collection}


@pytest.mark.asyncio
async def test_create_booking_persists_voucher_fields(mock_booking_db):
    """create_booking stores voucher_redemption_id and voucher_discount_amount when valid."""
    oid = ObjectId()
    req = CreateBookingEventRequest.model_validate(
        {
            "external_booking_reference": TEMP_EXTERNAL_REF,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-VCHR-TEST01",
            "voucher_redemption_id": str(oid),
        }
    )
    with (
        patch(
            "app.domains.bookings.service.get_database",
            AsyncMock(return_value=mock_booking_db),
        ),
        patch(
            "app.domains.discount.service.discount_service.validate_voucher_reservation_for_booking_event",
            AsyncMock(return_value=2500),
        ),
    ):
        svc = BookingService(user_id="507f1f77bcf86cd799439012")
        resp = await svc.create_booking(req)

    assert resp.voucher_redemption_id == str(oid)
    assert resp.voucher_discount_amount == 2500
    doc = mock_booking_db["booking_events"].insert_one.call_args[0][0]
    assert doc["voucher_redemption_id"] == str(oid)
    assert doc["voucher_discount_amount"] == 2500


@pytest.mark.asyncio
async def test_create_booking_voucher_without_voya_generates_ref(mock_booking_db):
    """voucher_redemption_id without voya: generate VOYA; never fail create_booking."""
    rid = str(ObjectId())
    req = CreateBookingEventRequest.model_validate(
        {
            "external_booking_reference": TEMP_EXTERNAL_REF,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voucher_redemption_id": rid,
        }
    )
    with (
        patch(
            "app.domains.bookings.service.get_database",
            AsyncMock(return_value=mock_booking_db),
        ),
        patch(
            "app.domains.discount.service.discount_service.validate_voucher_reservation_for_booking_event",
            AsyncMock(return_value=1000),
        ),
        patch(
            "app.domains.bookings.service.VoyaReferenceGenerator.generate_unique",
            AsyncMock(return_value="VOYA-GEN-00001"),
        ),
    ):
        svc = BookingService(user_id="507f1f77bcf86cd799439012")
        resp = await svc.create_booking(req)

    assert resp.voya_booking_reference == "VOYA-GEN-00001"
    assert resp.voucher_redemption_id == rid
    assert resp.voucher_discount_amount == 1000
    inserted = mock_booking_db["booking_events"].insert_one.call_args[0][0]
    assert inserted.get("voya_booking_reference") == "VOYA-GEN-00001"


@pytest.mark.asyncio
async def test_create_booking_voucher_validation_failure_still_inserts_event(
    mock_booking_db,
):
    """Invalid/stale voucher must not block booking_events row (link by redemption id)."""
    rid = str(ObjectId())
    req = CreateBookingEventRequest.model_validate(
        {
            "external_booking_reference": TEMP_EXTERNAL_REF,
            "action": "BOOKED",
            "event_type": "HOTEL",
            "voucher_redemption_id": rid,
        }
    )
    with (
        patch(
            "app.domains.bookings.service.get_database",
            AsyncMock(return_value=mock_booking_db),
        ),
        patch(
            "app.domains.discount.service.discount_service.validate_voucher_reservation_for_booking_event",
            AsyncMock(side_effect=RuntimeError("simulated discount failure")),
        ),
        patch(
            "app.domains.bookings.service.VoyaReferenceGenerator.generate_unique",
            AsyncMock(return_value="VOYA-H-GEN-02"),
        ),
    ):
        svc = BookingService(user_id="507f1f77bcf86cd799439012")
        resp = await svc.create_booking(req)

    assert resp.voucher_redemption_id == rid
    assert resp.voucher_discount_amount is None
    assert resp.voya_booking_reference == "VOYA-H-GEN-02"
    inserted = mock_booking_db["booking_events"].insert_one.call_args[0][0]
    assert inserted.get("voucher_redemption_id") == rid
    assert inserted.get("voucher_discount_amount") is None


@pytest.mark.asyncio
@patch(
    "app.domains.bookings.service.BookingService.get_latest_booking_event_with_voucher_for_voya",
    new_callable=AsyncMock,
)
async def test_redeem_on_payment_calls_repository_twice_idempotent(
    mock_get_event: AsyncMock,
):
    """Webhook may call redeem twice; repository handles idempotency."""
    mock_get_event.return_value = MagicMock(voucher_redemption_id="a" * 24)
    repo = MagicMock()
    repo.redeem_reserved_by_redemption_id = AsyncMock(return_value=None)
    svc = DiscountService(repository=repo)
    await svc.redeem_voucher_on_payment(booking_reference="VOYA-BR-1")
    await svc.redeem_voucher_on_payment(booking_reference="VOYA-BR-1")
    assert repo.redeem_reserved_by_redemption_id.await_count == 2


@pytest.mark.asyncio
@patch(
    "app.domains.bookings.service.BookingService.get_latest_booking_event_with_voucher_for_voya",
    new_callable=AsyncMock,
)
async def test_redeem_idempotent_after_manual_release_before_webhook(
    mock_get_event: AsyncMock,
) -> None:
    """Race: user releases voucher after pay confirm but before stripe webhook; redeem is a no-op."""
    mock_get_event.return_value = MagicMock(voucher_redemption_id="b" * 24)
    repo = MagicMock()
    repo.redeem_reserved_by_redemption_id = AsyncMock(return_value=None)
    svc = DiscountService(repository=repo)
    await svc.redeem_voucher_on_payment(booking_reference="VOYA-BR-REL")
    repo.redeem_reserved_by_redemption_id.assert_awaited_once()
    call_kw = repo.redeem_reserved_by_redemption_id.call_args.kwargs
    assert "redemption_id" in call_kw
    assert "now" in call_kw


@pytest.mark.asyncio
@patch(
    "app.domains.bookings.service.BookingService.get_latest_booking_event_with_voucher_for_voya",
    new_callable=AsyncMock,
)
async def test_release_voucher_for_booking_reference_calls_release(
    mock_get_event: AsyncMock,
):
    doc_id = str(ObjectId())
    reserved = Mock(
        id=doc_id,
        code="VOYA-ZZZZ-ZZZZ",
        status=VoucherStatus.RESERVED,
        reserved_by_user_id="user-1",
    )
    mock_get_event.return_value = Mock(voucher_redemption_id=doc_id)
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=reserved)
    repo.release_reservation = AsyncMock(return_value=Mock())
    svc = DiscountService(repository=repo)
    await svc.release_voucher_for_booking_reference(
        user_id="user-1",
        voya_booking_reference="VOYA-REL-00001",
    )
    mock_get_event.assert_awaited_once_with("VOYA-REL-00001")
    repo.release_reservation.assert_called_once()


@pytest.mark.asyncio
async def test_stripe_payment_succeeded_triggers_redeem():
    pi = {
        "id": "pi_test_123",
        "amount": 10000,
        "currency": "usd",
        "metadata": {
            "voya_booking_reference": "VOYA-WH-TEST01",
            "user_id": "507f1f77bcf86cd799439099",  # pragma: allowlist secret
        },
        "created": 1700000000,
    }
    mock_repo = Mock()
    mock_repo.update_transaction_status = AsyncMock(return_value=Mock())
    with (
        patch(
            "app.domains.payment.webhook_service.BookingService.get_latest_booking_by_voya_reference",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.domains.payment.webhook_service.BookingService.update_booking_dates_and_flags",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.payment.webhook_service.PaymentEventHandler.handle_payment_succeeded",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.discount.service.discount_service.redeem_voucher_on_payment",
            new_callable=AsyncMock,
        ) as mock_redeem,
    ):
        svc = PaymentWebhookService(repository=mock_repo)
        await svc.process_payment_succeeded(pi)
    mock_redeem.assert_awaited_once_with(booking_reference="VOYA-WH-TEST01")


@pytest.mark.asyncio
@patch(
    "app.domains.payment.webhook_service.BookingService.release_voucher_for_booking_if_any",
    new_callable=AsyncMock,
)
async def test_stripe_payment_failed_triggers_release(mock_release):
    pi = {
        "id": "pi_fail_1",
        "metadata": {
            "voya_booking_reference": "VOYA-WH-FAIL01",
            "user_id": "507f1f77bcf86cd799439088",  # pragma: allowlist secret
        },
    }
    mock_repo = Mock()
    mock_repo.update_transaction_status = AsyncMock(return_value=Mock())
    svc = PaymentWebhookService(repository=mock_repo)
    await svc.process_payment_failed(pi)
    mock_release.assert_awaited_once_with(
        "507f1f77bcf86cd799439088",  # pragma: allowlist secret
        "VOYA-WH-FAIL01",
    )


@pytest.mark.asyncio
async def test_validate_voucher_reservation_matches_user():
    """Reservation is validated by user + RESERVED state (no VOYA on discount row)."""
    doc_id = str(ObjectId())
    now = datetime.now(UTC)
    doc = DiscountDoc(
        id=doc_id,
        code="VOYA-X-Y",
        amount_cents=100,
        currency="USD",
        status=VoucherStatus.RESERVED,
        source="t",
        batch_id="b",
        created_at=now,
        created_by_admin_id=None,
        expires_at=None,
        reserved_by_user_id="u1",
        reservation_expires_at=None,
        redeemed_at=None,
        user_id=None,
    )
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=doc)
    svc = DiscountService(repository=repo)
    out = await svc.validate_voucher_reservation_for_booking_event(
        user_id="u1",
        redemption_id=doc_id,
    )
    assert out == 100
