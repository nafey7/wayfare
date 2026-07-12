"""Unit tests for discount / voucher domain service."""

import itertools
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.discount.constants import VoucherStatus
from app.domains.discount.exceptions import (
    DiscountDomainError,
    VoucherAlreadyUsedError,
    VoucherAmountTooLowError,
    VoucherCurrencyInvalidError,
    VoucherExpiredError,
    VoucherNotFoundError,
    VoucherReleaseConflictError,
    VoucherReservedByOtherError,
)
from app.domains.discount.models import DiscountDoc
from app.domains.discount.schemas import VoucherBatchCreateRequest, VoucherBatchSource
from app.domains.discount.service import (
    DiscountService,
    _voya_client_ref_matches_booking_event,
)


def test_voya_client_ref_matches_leg_and_parent() -> None:
    ev = MagicMock(
        voya_booking_reference="VOYA-LEG-1",
        parent_voya_booking_reference="VOYA-GROUP-1",
    )
    assert _voya_client_ref_matches_booking_event("VOYA-GROUP-1", ev)
    assert _voya_client_ref_matches_booking_event("VOYA-LEG-1", ev)
    assert not _voya_client_ref_matches_booking_event("VOYA-OTHER", ev)


def test_voucher_batch_create_source_accepts_enum_and_custom_labels() -> None:
    custom = VoucherBatchCreateRequest.model_validate(
        {"count": 1, "amount_cents": 100, "source": "G2A_batch"},
    )
    assert custom.source == "G2A_batch"

    known = VoucherBatchCreateRequest.model_validate(
        {"count": 1, "amount_cents": 100, "source": "g2a"},
    )
    assert str(known.source) == VoucherBatchSource.G2A


def _doc(
    *,
    id: str | None = None,
    code: str = "VOYA-AAAA-BBBB",
    status: str = VoucherStatus.ACTIVE,
    amount_cents: int = 5000,
    batch_id: str = "batch-1",
    reserved_by: str | None = None,
    reservation_until: datetime | None = None,
    expires_at: datetime | None = None,
    user_id: str | None = None,
    redeemed_at: datetime | None = None,
) -> DiscountDoc:
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    return DiscountDoc(
        id=id or str(ObjectId()),
        code=code,
        amount_cents=amount_cents,
        currency="USD",
        status=status,
        source="test",
        batch_id=batch_id,
        created_at=now,
        created_by_admin_id="admin1",
        expires_at=expires_at,
        reserved_by_user_id=reserved_by,
        reservation_expires_at=reservation_until,
        redeemed_at=redeemed_at,
        user_id=user_id,
    )


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_apply_active_code_reserves_and_returns_total(
    fixed_now: datetime,
) -> None:
    repo = MagicMock()
    active = _doc(status=VoucherStatus.ACTIVE)
    reserved = _doc(
        status=VoucherStatus.RESERVED,
        reserved_by="u1",
        reservation_until=fixed_now + timedelta(minutes=15),
    )
    repo.find_by_code = AsyncMock(return_value=active)
    repo.mark_expired_if_needed = AsyncMock()
    repo.try_reserve_code = AsyncMock(return_value=reserved)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    out = await svc.apply_voucher(
        user_id="u1",
        code="voya-aaaa-bbbb",
        voya_booking_reference="VOYA-BOOK-1",
        amount_cents=10_000,
        booking_type="flight",
        currency=None,
    )
    assert out.discount_cents == 5000
    assert out.new_total_cents == 5000
    assert out.redemption_id == reserved.id
    repo.try_reserve_code.assert_awaited_once()
    kwn = repo.try_reserve_code.call_args.kwargs
    assert set(kwn) == {"code", "user_id", "reservation_expires_at", "now"}


@pytest.mark.asyncio
async def test_apply_reserved_other_user_naive_mongo_datetimes_no_typeerror(
    fixed_now: datetime,
) -> None:
    """BSON often returns naive UTC times; comparing to aware `now` must not raise."""
    oid = ObjectId()
    naive_future = datetime(2026, 1, 1, 13, 0, 0)  # naive, same wall time as UTC
    raw = {
        "_id": oid,
        "code": "VOYA-AAAA-BBBB",
        "amount_cents": 5000,
        "currency": "USD",
        "status": VoucherStatus.RESERVED,
        "source": "test",
        "batch_id": "batch-1",
        "created_at": naive_future,
        "created_by_admin_id": None,
        "expires_at": None,
        "reserved_by_user_id": "other",
        "reservation_expires_at": naive_future,
        "redeemed_at": None,
        "user_id": None,
    }
    existing = DiscountDoc.from_dict(raw)
    repo = MagicMock()
    repo.find_by_code = AsyncMock(return_value=existing)
    repo.mark_expired_if_needed = AsyncMock()
    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherReservedByOtherError):
        await svc.apply_voucher(
            user_id="u1",
            code="voya-aaaa-bbbb",
            voya_booking_reference="VOYA-ME",
            amount_cents=10_000,
            booking_type="flight",
            currency=None,
        )


@pytest.mark.asyncio
async def test_apply_used_code_returns_error(fixed_now: datetime) -> None:
    repo = MagicMock()
    used = _doc(status=VoucherStatus.USED)
    repo.find_by_code = AsyncMock(return_value=used)
    repo.mark_expired_if_needed = AsyncMock()

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherAlreadyUsedError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type=None,
            currency=None,
        )


@pytest.mark.asyncio
async def test_apply_nonexistent_returns_404(fixed_now: datetime) -> None:
    repo = MagicMock()
    repo.find_by_code = AsyncMock(return_value=None)
    repo.mark_expired_if_needed = AsyncMock()

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherNotFoundError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-XXXX-YYYY",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type=None,
            currency=None,
        )


@pytest.mark.asyncio
async def test_apply_amount_below_voucher_returns_error(fixed_now: datetime) -> None:
    repo = MagicMock()
    d = _doc(amount_cents=5000, status=VoucherStatus.ACTIVE)
    repo.find_by_code = AsyncMock(return_value=d)
    repo.mark_expired_if_needed = AsyncMock()

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherAmountTooLowError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=1000,
            booking_type=None,
            currency=None,
        )


@pytest.mark.asyncio
async def test_apply_non_usd_currency_returns_error(fixed_now: datetime) -> None:
    repo = MagicMock()
    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherCurrencyInvalidError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type=None,
            currency="eur",
        )


@pytest.mark.asyncio
async def test_apply_reserved_same_user_rejects_other_checkout_ref(
    fixed_now: datetime,
) -> None:
    import app.domains.bookings.service as booking_service_module

    rid = str(ObjectId())
    existing = _doc(
        id=rid,
        status=VoucherStatus.RESERVED,
        reserved_by="u1",
        reservation_until=fixed_now + timedelta(minutes=15),
    )
    with patch.object(
        booking_service_module.BookingService,
        "get_latest_booking_event_by_voucher_redemption_id",
        new_callable=AsyncMock,
    ) as mock_get_event:
        mock_get_event.return_value = MagicMock(
            voya_booking_reference="VOYA-BOOK-A",
            parent_voya_booking_reference=None,
        )
        repo = MagicMock()
        repo.find_by_code = AsyncMock(return_value=existing)
        repo.mark_expired_if_needed = AsyncMock()
        svc = DiscountService(repository=repo, clock=lambda: fixed_now)
        with pytest.raises(VoucherReservedByOtherError):
            await svc.apply_voucher(
                user_id="u1",
                code="VOYA-AAAA-BBBB",
                voya_booking_reference="VOYA-BOOK-B",
                amount_cents=10_000,
                booking_type="flight",
                currency=None,
            )


@pytest.mark.asyncio
async def test_apply_reserved_same_user_idempotent_when_booking_matches(
    fixed_now: datetime,
) -> None:
    import app.domains.bookings.service as booking_service_module

    rid = str(ObjectId())
    until = fixed_now + timedelta(minutes=15)
    existing = _doc(
        id=rid,
        status=VoucherStatus.RESERVED,
        reserved_by="u1",
        reservation_until=until,
    )
    with patch.object(
        booking_service_module.BookingService,
        "get_latest_booking_event_by_voucher_redemption_id",
        new_callable=AsyncMock,
    ) as mock_get_event:
        mock_get_event.return_value = MagicMock(
            voya_booking_reference="VOYA-BOOK-A",
            parent_voya_booking_reference=None,
        )
        repo = MagicMock()
        repo.find_by_code = AsyncMock(return_value=existing)
        repo.mark_expired_if_needed = AsyncMock()
        svc = DiscountService(repository=repo, clock=lambda: fixed_now)
        out = await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-A",
            amount_cents=10_000,
            booking_type="flight",
            currency=None,
        )
    assert out.redemption_id == rid
    assert out.reservation_expires_at == until


@pytest.mark.asyncio
async def test_apply_reserved_same_user_idempotent_skips_mismatch_check_without_booking_row(
    fixed_now: datetime,
) -> None:
    import app.domains.bookings.service as booking_service_module

    rid = str(ObjectId())
    until = fixed_now + timedelta(minutes=15)
    existing = _doc(
        id=rid,
        status=VoucherStatus.RESERVED,
        reserved_by="u1",
        reservation_until=until,
    )
    with patch.object(
        booking_service_module.BookingService,
        "get_latest_booking_event_by_voucher_redemption_id",
        new_callable=AsyncMock,
    ) as mock_get_event:
        mock_get_event.return_value = None
        repo = MagicMock()
        repo.find_by_code = AsyncMock(return_value=existing)
        repo.mark_expired_if_needed = AsyncMock()
        svc = DiscountService(repository=repo, clock=lambda: fixed_now)
        out = await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-NEW-CHECKOUT",
            amount_cents=10_000,
            booking_type="flight",
            currency=None,
        )
        assert out.redemption_id == rid
        mock_get_event.assert_awaited_once_with(rid)


@pytest.mark.asyncio
async def test_apply_race_two_users_only_one_reserves(fixed_now: datetime) -> None:
    """Simulate lost atomic reserve: re-read shows another user's reservation."""
    other_reserved = _doc(
        status=VoucherStatus.RESERVED,
        reserved_by="u-winner",
        reservation_until=fixed_now + timedelta(minutes=15),
    )
    repo = MagicMock()
    repo.mark_expired_if_needed = AsyncMock()
    repo.find_by_code = AsyncMock(
        side_effect=[_doc(status=VoucherStatus.ACTIVE), other_reserved]
    )
    repo.try_reserve_code = AsyncMock(return_value=None)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherReservedByOtherError):
        await svc.apply_voucher(
            user_id="u-loser",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type=None,
            currency=None,
        )


@pytest.mark.asyncio
async def test_release_reserved_returns(fixed_now: datetime) -> None:
    oid = ObjectId()
    doc = _doc(
        id=str(oid),
        status=VoucherStatus.RESERVED,
        reserved_by="u1",
    )
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=doc)
    repo.release_reservation = AsyncMock(return_value=_doc(status=VoucherStatus.ACTIVE))

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    await svc.release_voucher(user_id="u1", redemption_id=str(oid))
    repo.release_reservation.assert_awaited_once()


@pytest.mark.asyncio
async def test_release_used_returns_conflict(fixed_now: datetime) -> None:
    oid = ObjectId()
    doc = _doc(id=str(oid), status=VoucherStatus.USED)
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=doc)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherReleaseConflictError):
        await svc.release_voucher(user_id="u1", redemption_id=str(oid))


@pytest.mark.asyncio
async def test_release_already_active_idempotent(fixed_now: datetime) -> None:
    oid = ObjectId()
    doc = _doc(id=str(oid), status=VoucherStatus.ACTIVE)
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=doc)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    await svc.release_voucher(user_id="u1", redemption_id=str(oid))
    repo.release_reservation.assert_not_called()


@pytest.mark.asyncio
async def test_redeem_on_payment_idempotent(
    fixed_now: datetime,
) -> None:
    import app.domains.bookings.service as booking_service_module

    used = _doc(status=VoucherStatus.USED)
    with patch.object(
        booking_service_module.BookingService,
        "get_latest_booking_event_with_voucher_for_voya",
        new_callable=AsyncMock,
    ) as mock_get_event:
        mock_get_event.return_value = MagicMock(voucher_redemption_id="a" * 24)
        repo = MagicMock()
        repo.redeem_reserved_by_redemption_id = AsyncMock(return_value=used)

        svc = DiscountService(repository=repo, clock=lambda: fixed_now)
        await svc.redeem_voucher_on_payment(booking_reference="VOYA-BR-1")
        await svc.redeem_voucher_on_payment(booking_reference="VOYA-BR-1")
        assert repo.redeem_reserved_by_redemption_id.await_count == 2


@pytest.mark.asyncio
async def test_generate_batch_creates_n_codes(fixed_now: datetime) -> None:
    inserted: list[list] = []

    async def insert_many_raw(docs: list) -> None:
        inserted.append(docs)

    repo = MagicMock()
    repo.delete_many_by_batch = AsyncMock()
    repo.insert_many_raw = AsyncMock(side_effect=insert_many_raw)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    out = await svc.generate_batch(
        admin_user_id="admin1",
        count=5,
        amount_cents=100,
        source="SRC",
        prefix="VOYA",
        expires_at=None,
    )
    assert out.count == 5
    assert len(inserted[-1]) == 5
    assert len({d["code"] for d in inserted[-1]}) == 5
    assert all(d["batch_id"] == out.batch_id for d in inserted[-1])
    assert "reserved_for_booking_reference" not in inserted[-1][0]
    assert "booking_reference" not in inserted[-1][0]


@pytest.mark.asyncio
async def test_generate_batch_retries_on_collision(fixed_now: datetime) -> None:
    calls = {"n": 0}
    inserted_codes: list[list[str]] = []

    async def insert_many_raw(docs: list) -> None:
        calls["n"] += 1
        inserted_codes.append([d["code"] for d in docs])
        if calls["n"] == 1:
            from pymongo.errors import BulkWriteError

            raise BulkWriteError({"writeErrors": [{"code": 11000, "index": 0}]})

    repo = MagicMock()
    repo.delete_many_by_batch = AsyncMock()
    repo.insert_many_raw = AsyncMock(side_effect=insert_many_raw)

    char_cycle = itertools.cycle("ABCD23456789")

    svc = DiscountService(
        repository=repo,
        clock=lambda: fixed_now,
        pick_char=lambda: next(char_cycle),
    )
    out = await svc.generate_batch(
        admin_user_id="admin1",
        count=2,
        amount_cents=50,
        source="S",
        prefix="VOYA",
        expires_at=None,
    )
    assert out.count == 2
    assert repo.insert_many_raw.await_count == 2
    assert repo.delete_many_by_batch.await_count == 2
    assert len(inserted_codes) == 2
    assert set(inserted_codes[0]) != set(inserted_codes[1])


@pytest.mark.asyncio
async def test_generate_batch_bulk_write_retries_exhausted_raises(
    fixed_now: datetime,
) -> None:
    from pymongo.errors import BulkWriteError

    repo = MagicMock()
    repo.delete_many_by_batch = AsyncMock()
    repo.insert_many_raw = AsyncMock(
        side_effect=BulkWriteError({"writeErrors": [{"code": 11000, "index": 0}]}),
    )

    with patch("app.domains.discount.service.BATCH_INSERT_MAX_ATTEMPTS", 3):
        svc = DiscountService(repository=repo, clock=lambda: fixed_now)
        with pytest.raises(
            DiscountDomainError, match="Batch insert failed after retries"
        ):
            await svc.generate_batch(
                admin_user_id="admin1",
                count=2,
                amount_cents=50,
                source="S",
                prefix="VOYA",
                expires_at=None,
            )

    assert repo.insert_many_raw.await_count == 3
    assert repo.delete_many_by_batch.await_count == 4


@pytest.mark.asyncio
async def test_apply_expired_reloads_doc_after_mark(
    fixed_now: datetime,
) -> None:
    """Active+past natural expiry: mark + re-read picks up current DB state."""
    first = _doc(
        status=VoucherStatus.ACTIVE,
        expires_at=fixed_now - timedelta(days=1),
    )
    expired = _doc(
        status=VoucherStatus.EXPIRED,
        expires_at=fixed_now - timedelta(days=1),
    )
    repo = MagicMock()
    repo.find_by_code = AsyncMock(side_effect=[first, expired])
    repo.mark_expired_if_needed = AsyncMock(return_value=True)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherExpiredError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type="hotel",
            currency=None,
        )
    assert repo.find_by_code.await_count == 2


@pytest.mark.asyncio
async def test_apply_expired_mark_race_refetches_once(fixed_now: datetime) -> None:
    """If mark matched nothing (race), service re-reads once for current DB state."""
    first = _doc(
        status=VoucherStatus.ACTIVE,
        expires_at=fixed_now - timedelta(days=1),
    )
    other_reserved = _doc(
        status=VoucherStatus.RESERVED,
        reserved_by="winner",
        reservation_until=fixed_now + timedelta(minutes=15),
    )
    repo = MagicMock()
    repo.find_by_code = AsyncMock(side_effect=[first, other_reserved])
    repo.mark_expired_if_needed = AsyncMock(return_value=False)

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    with pytest.raises(VoucherReservedByOtherError):
        await svc.apply_voucher(
            user_id="u1",
            code="VOYA-AAAA-BBBB",
            voya_booking_reference="VOYA-BOOK-1",
            amount_cents=10_000,
            booking_type=None,
            currency=None,
        )
    assert repo.find_by_code.await_count == 2


@pytest.mark.asyncio
async def test_export_batch_streams_csv_rows(fixed_now: datetime) -> None:
    async def iter_csv(batch_id: str):
        assert batch_id == "b1"
        for c in ("VOYA-A-B", "VOYA-C-D"):
            yield c

    repo = MagicMock()
    repo.iter_codes_in_batch_csv = iter_csv  # type: ignore[method-assign]

    svc = DiscountService(repository=repo, clock=lambda: fixed_now)
    lines: list[str] = []
    async for line in svc.export_batch_csv_lines("b1"):
        lines.append(line)
    assert lines == ["VOYA-A-B\n", "VOYA-C-D\n"]
