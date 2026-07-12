"""Business logic for G2A / manual discount vouchers."""

from __future__ import annotations

import contextlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, NoReturn

from bson import ObjectId
from pymongo.errors import BulkWriteError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from app.domains.discount.models import DiscountDoc

from app.domains.discount.constants import (
    BATCH_INSERT_MAX_ATTEMPTS,
    CODE_ALPHABET,
    CODE_BLOCK_LEN,
    DISCOUNT_CODE_PREFIX,
    MAX_BATCH_SIZE,
    RESERVATION_TTL_MINUTES,
    VoucherStatus,
)
from app.domains.discount.exceptions import (
    DiscountDomainError,
    VoucherAlreadyUsedError,
    VoucherAmountTooLowError,
    VoucherCurrencyInvalidError,
    VoucherExpiredError,
    VoucherInvalidStateError,
    VoucherNotFoundError,
    VoucherReleaseConflictError,
    VoucherReservedByOtherError,
)
from app.domains.discount.repository import DiscountRepository, discount_repository
from app.domains.discount.schemas import (
    AdminBatchDetailResponse,
    AdminBatchListResponse,
    AdminBatchSummary,
    AdminDiscountListResponse,
    VoucherApplyResponse,
    VoucherBatchCreateResponse,
    VoucherDocResponse,
)

logger = logging.getLogger(__name__)


def _voya_client_ref_matches_booking_event(request_ref: str, event: object) -> bool:
    """True if the client ref equals the event's VOYA leg or multicity parent reference."""
    n = request_ref.strip().casefold()
    for attr in ("voya_booking_reference", "parent_voya_booking_reference"):
        cand = getattr(event, attr, None)
        if cand is not None and str(cand).strip().casefold() == n:
            return True
    return False


def normalize_voucher_code(raw: str) -> str:
    return raw.strip().upper()


def generate_voucher_code(
    prefix: str = DISCOUNT_CODE_PREFIX,
    *,
    pick_char: Callable[[], str] | None = None,
) -> str:
    """Return a code like ``VOYA-ABCD-1234`` using the URL-safe alphabet."""

    def _pick() -> str:
        return pick_char() if pick_char else secrets.choice(CODE_ALPHABET)

    def _block() -> str:
        return "".join(_pick() for _ in range(CODE_BLOCK_LEN))

    p = prefix.strip().upper()
    return f"{p}-{_block()}-{_block()}"


class DiscountService:
    """Apply, release, batch-generate, and redeem discount vouchers."""

    def __init__(
        self,
        repository: DiscountRepository | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        pick_char: Callable[[], str] | None = None,
    ) -> None:
        self._repo = repository or discount_repository
        self._clock = clock
        self._pick_char = pick_char

    def _now(self) -> datetime:
        if self._clock:
            return self._clock()
        return datetime.now(UTC)

    def _make_code(self, prefix: str) -> str:
        return generate_voucher_code(prefix, pick_char=self._pick_char)

    def _doc_to_response(self, doc: DiscountDoc) -> VoucherDocResponse:
        if doc.id is None:
            raise VoucherInvalidStateError("Discount document missing id")
        return VoucherDocResponse(
            id=doc.id,
            code=doc.code,
            amount_cents=doc.amount_cents,
            currency=doc.currency,
            status=doc.status,
            source=doc.source,
            batch_id=doc.batch_id,
            created_at=doc.created_at,
            created_by_admin_id=doc.created_by_admin_id,
            expires_at=doc.expires_at,
            reserved_by_user_id=doc.reserved_by_user_id,
            reservation_expires_at=doc.reservation_expires_at,
            redeemed_at=doc.redeemed_at,
            user_id=doc.user_id,
        )

    def _ensure_usd_currency(self, currency: str | None) -> None:
        if currency is None:
            return
        if str(currency).lower() != "usd":
            raise VoucherCurrencyInvalidError("Only USD is supported for vouchers")

    async def apply_voucher(  # noqa: PLR0913
        self,
        *,
        user_id: str,
        code: str,
        voya_booking_reference: str | None = None,
        amount_cents: int,
        booking_type: str | None,  # noqa: ARG002
        currency: str | None,
    ) -> VoucherApplyResponse:
        """Reserve a voucher. ``booking_type`` is accepted for API stability but not
        used yet; flight and hotel share the same apply rules.

        The discount row no longer stores a VOYA booking ref; linkage is
        ``booking_events.voucher_redemption_id`` (this document's ``_id``).
        ``voya_booking_reference`` is optional metadata for clients.
        """
        self._ensure_usd_currency(currency)

        normalized = normalize_voucher_code(code)
        now = self._now()

        existing = await self._repo.find_by_code(normalized)
        if existing is None:
            raise VoucherNotFoundError("Voucher not found")

        await self._repo.mark_expired_if_needed(normalized, now=now)
        if (
            existing.status == VoucherStatus.ACTIVE
            and existing.expires_at is not None
            and existing.expires_at <= now
        ):
            existing = await self._repo.find_by_code(normalized)
            if existing is None:
                raise VoucherNotFoundError("Voucher not found")

        if existing.status == VoucherStatus.USED:
            raise VoucherAlreadyUsedError("Voucher already used")
        if existing.status == VoucherStatus.DISABLED:
            raise VoucherAlreadyUsedError("Voucher is disabled")
        if existing.status == VoucherStatus.EXPIRED:
            raise VoucherExpiredError("Voucher has expired")
        if existing.expires_at and existing.expires_at <= now:
            raise VoucherExpiredError("Voucher has expired")

        discount_cents = existing.amount_cents
        if amount_cents < discount_cents:
            raise VoucherAmountTooLowError(
                booking_cents=amount_cents, voucher_cents=discount_cents
            )

        if (
            existing.status == VoucherStatus.RESERVED
            and existing.reservation_expires_at
            and existing.reservation_expires_at > now
        ):
            if existing.reserved_by_user_id == user_id:
                ref = (voya_booking_reference or "").strip()
                if ref:
                    from app.domains.bookings.service import BookingService

                    event = await BookingService.get_latest_booking_event_by_voucher_redemption_id(
                        str(existing.id),
                    )
                    # No booking_events row yet is expected between apply and book. Until one
                    # exists we cannot correlate refs, so the same reserved redemption is
                    # returned even if the client sends a different voya_booking_reference
                    # (idempotent apply; see test_apply_reserved_same_user_idempotent_skips_mismatch_check_without_booking_row).
                    if event is not None and not _voya_client_ref_matches_booking_event(
                        ref, event
                    ):
                        raise VoucherReservedByOtherError(
                            "Voucher is reserved for another booking"
                        )
                if existing.id is None:
                    raise VoucherInvalidStateError("Discount document missing id")
                return VoucherApplyResponse(
                    redemption_id=existing.id,
                    code=existing.code,
                    discount_cents=discount_cents,
                    new_total_cents=amount_cents - discount_cents,
                    currency="usd",
                    reservation_expires_at=existing.reservation_expires_at,
                )
            raise VoucherReservedByOtherError(
                "Voucher is reserved by another user or booking"
            )

        reservation_until = now + timedelta(minutes=RESERVATION_TTL_MINUTES)
        updated = await self._repo.try_reserve_code(
            code=normalized,
            user_id=user_id,
            reservation_expires_at=reservation_until,
            now=now,
        )

        if updated is None:
            await self._raise_apply_failure(normalized, user_id, now)

        if updated.id is None:
            raise VoucherInvalidStateError("Discount document missing id after reserve")
        return VoucherApplyResponse(
            redemption_id=updated.id,
            code=updated.code,
            discount_cents=discount_cents,
            new_total_cents=amount_cents - discount_cents,
            currency="usd",
            reservation_expires_at=reservation_until,
        )

    async def _raise_apply_failure(
        self, code: str, user_id: str, now: datetime
    ) -> NoReturn:
        doc = await self._repo.find_by_code(code)
        if doc is None:
            raise VoucherNotFoundError("Voucher not found")
        if doc.status == VoucherStatus.USED:
            raise VoucherAlreadyUsedError("Voucher already used")
        if doc.status == VoucherStatus.DISABLED:
            raise VoucherAlreadyUsedError("Voucher is disabled")
        if doc.status == VoucherStatus.EXPIRED:
            raise VoucherExpiredError("Voucher has expired")
        if doc.expires_at and doc.expires_at <= now:
            raise VoucherExpiredError("Voucher has expired")
        if doc.status == VoucherStatus.RESERVED:
            if doc.reservation_expires_at and doc.reservation_expires_at <= now:
                raise VoucherExpiredError("Reservation expired; try again")
            if doc.reserved_by_user_id != user_id:
                raise VoucherReservedByOtherError(
                    "Voucher is reserved by another user or booking"
                )
            raise VoucherInvalidStateError("Could not apply voucher")
        raise VoucherInvalidStateError("Could not apply voucher")

    async def release_voucher(self, *, user_id: str, redemption_id: str) -> None:
        try:
            oid = ObjectId(redemption_id)
        except Exception as err:
            raise VoucherNotFoundError("Voucher reservation not found") from err

        doc = await self._repo.find_by_id(redemption_id)
        if doc is None:
            raise VoucherNotFoundError("Voucher reservation not found")
        if doc.status == VoucherStatus.USED:
            raise VoucherReleaseConflictError("Voucher already redeemed")
        if doc.status == VoucherStatus.ACTIVE:
            # Idempotent: already released (duplicate client callback, React strict mode, or back+error twice).
            return
        if doc.status != VoucherStatus.RESERVED:
            raise VoucherNotFoundError("Voucher reservation not found")
        if doc.reserved_by_user_id != user_id:
            raise VoucherNotFoundError("Voucher reservation not found")

        released = await self._repo.release_reservation(doc_id=oid, user_id=user_id)
        if released is None:
            raise VoucherNotFoundError("Voucher reservation not found")

    async def validate_voucher_reservation_for_booking_event(
        self,
        *,
        user_id: str,
        redemption_id: str,
    ) -> int:
        """Ensure the reservation matches this user; return discount cents (USD).

        Booking correlation is on ``booking_events`` via ``voucher_redemption_id``, not on the
        discount document.
        """
        doc = await self._repo.find_by_id(redemption_id)
        now = self._now()
        if doc is None:
            raise VoucherNotFoundError("Voucher reservation not found")
        if doc.status != VoucherStatus.RESERVED:
            if doc.status == VoucherStatus.USED:
                raise VoucherAlreadyUsedError("Voucher already used")
            raise VoucherInvalidStateError(
                "Voucher is not in a valid state for booking"
            )
        if doc.reserved_by_user_id != user_id:
            raise VoucherReservedByOtherError(
                "Voucher is reserved by another user or booking"
            )
        if doc.reservation_expires_at is not None and doc.reservation_expires_at <= now:
            raise VoucherExpiredError("Voucher reservation has expired; apply again")
        if doc.expires_at is not None and doc.expires_at <= now:
            raise VoucherExpiredError("Voucher has expired")
        return doc.amount_cents

    async def release_voucher_for_booking_reference(
        self,
        *,
        user_id: str,
        voya_booking_reference: str,
    ) -> None:
        """Release a RESERVED voucher held for this booking (payment failed, cancel, etc.)."""
        from app.domains.bookings.service import BookingService

        event = await BookingService.get_latest_booking_event_with_voucher_for_voya(
            voya_booking_reference
        )
        if event is None or not event.voucher_redemption_id:
            return
        with contextlib.suppress(VoucherReleaseConflictError):
            await self.release_voucher(
                user_id=user_id, redemption_id=event.voucher_redemption_id
            )

    async def redeem_voucher_on_payment(self, *, booking_reference: str) -> None:
        from app.domains.bookings.service import BookingService

        now = self._now()
        event = await BookingService.get_latest_booking_event_with_voucher_for_voya(
            booking_reference
        )
        if event is None or not event.voucher_redemption_id:
            return
        doc = await self._repo.redeem_reserved_by_redemption_id(
            redemption_id=event.voucher_redemption_id,
            now=now,
        )
        if doc is None:
            logger.warning(
                "[G2A voucher] redeem_voucher_on_payment: Mongo update returned no "
                "doc after redeem attempt voya=%r (see previous repository log for status)",
                booking_reference,
            )
            return
        from app.core.logging import mask_voucher_code_for_log

        logger.info(
            "Redeemed voucher %s for booking ref %s",
            mask_voucher_code_for_log(doc.code),
            booking_reference,
        )

    async def expire_stale_reservations(self) -> int:
        return await self._repo.expire_stale_reservations(now=self._now())

    async def generate_batch(
        self,
        *,
        admin_user_id: str,
        count: int,
        amount_cents: int,
        source: str,
        prefix: str | None,
        expires_at: datetime | None,
    ) -> VoucherBatchCreateResponse:
        if count > MAX_BATCH_SIZE:
            raise DiscountDomainError(f"Batch size must be at most {MAX_BATCH_SIZE}")

        batch_id = str(uuid.uuid4())
        now = self._now()
        pf = (prefix or DISCOUNT_CODE_PREFIX).strip().upper()
        if not pf.replace("-", "").isalnum():
            raise DiscountDomainError("Prefix must be alphanumeric")

        codes: set[str] = set()
        attempt = 0
        max_gen = max(count * 4, 16)
        while len(codes) < count and attempt < max_gen:
            attempt += 1
            codes.add(self._make_code(pf))

        if len(codes) < count:
            raise DiscountDomainError("Failed to generate enough unique codes")

        code_list = list(codes)[:count]

        for attempt in range(BATCH_INSERT_MAX_ATTEMPTS):
            await self._repo.delete_many_by_batch(batch_id)
            if attempt > 0:
                regen: set[str] = set()
                gen_attempts = 0
                while len(regen) < count and gen_attempts < max(count * 4, 16):
                    gen_attempts += 1
                    regen.add(self._make_code(pf))
                if len(regen) < count:
                    raise DiscountDomainError("Failed to generate enough unique codes")
                code_list = list(regen)[:count]

            pending = [
                {
                    "code": c,
                    "amount_cents": amount_cents,
                    "currency": "USD",
                    "status": VoucherStatus.ACTIVE,
                    "source": source,
                    "batch_id": batch_id,
                    "created_at": now,
                    "created_by_admin_id": admin_user_id,
                    "expires_at": expires_at,
                    "reserved_by_user_id": None,
                    "reservation_expires_at": None,
                    "redeemed_at": None,
                    "user_id": None,
                }
                for c in code_list
            ]
            try:
                await self._repo.insert_many_raw(pending)
                break
            except BulkWriteError as bwe:
                if attempt + 1 >= BATCH_INSERT_MAX_ATTEMPTS:
                    await self._repo.delete_many_by_batch(batch_id)
                    raise DiscountDomainError(
                        "Batch insert failed after retries"
                    ) from bwe

        return VoucherBatchCreateResponse(
            batch_id=batch_id,
            count=count,
            total_amount_cents=count * amount_cents,
            currency="USD",
            created_at=now,
            sample_codes=code_list[:3],
        )

    async def export_batch_csv_lines(self, batch_id: str) -> AsyncIterator[str]:
        async for code in self._repo.iter_codes_in_batch_csv(batch_id):
            yield f"{code}\n"

    async def count_codes_in_batch(self, batch_id: str) -> int:
        return await self._repo.count_codes_for_batch(batch_id)

    async def list_admin_discounts(
        self,
        *,
        status: str | None,
        batch_id: str | None,
        source: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> AdminDiscountListResponse:
        items, total = await self._repo.list_discounts(
            status=status,
            batch_id=batch_id,
            source=source,
            search=search,
            limit=limit,
            offset=offset,
        )
        return AdminDiscountListResponse(
            items=[self._doc_to_response(d) for d in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_admin_discount(self, doc_id: str) -> VoucherDocResponse:
        doc = await self._repo.find_by_id(doc_id)
        if doc is None:
            raise VoucherNotFoundError("Discount not found")
        return self._doc_to_response(doc)

    async def disable_discount(self, doc_id: str) -> VoucherDocResponse:
        try:
            oid = ObjectId(doc_id)
        except Exception as err:
            raise VoucherNotFoundError("Discount not found") from err
        doc = await self._repo.disable_code(oid)
        if doc is None:
            raise VoucherNotFoundError("Discount not found or cannot be disabled")
        return self._doc_to_response(doc)

    async def list_batches(self) -> AdminBatchListResponse:
        rows = await self._repo.aggregate_batch_summaries()
        batches: list[AdminBatchSummary] = []
        for r in rows:
            batches.append(
                AdminBatchSummary(
                    batch_id=str(r["_id"]),
                    total=int(r.get("total", 0)),
                    used=int(r.get("used", 0)),
                    reserved=int(r.get("reserved", 0)),
                    active=int(r.get("active", 0)),
                    expired=int(r.get("expired", 0)),
                    disabled=int(r.get("disabled", 0)),
                    source=str(r.get("source") or ""),
                    created_at=r.get("created_at"),
                    total_amount_cents=int(r.get("total_amount_cents", 0)),
                )
            )
        return AdminBatchListResponse(batches=batches)

    async def get_batch_detail(
        self,
        batch_id: str,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AdminBatchDetailResponse:
        summaries = await self._repo.aggregate_batch_summaries(batch_id=batch_id)
        summary_row = summaries[0] if summaries else None
        if summary_row is None:
            raise VoucherNotFoundError("Batch not found")

        summary = AdminBatchSummary(
            batch_id=batch_id,
            total=int(summary_row.get("total", 0)),
            used=int(summary_row.get("used", 0)),
            reserved=int(summary_row.get("reserved", 0)),
            active=int(summary_row.get("active", 0)),
            expired=int(summary_row.get("expired", 0)),
            disabled=int(summary_row.get("disabled", 0)),
            source=str(summary_row.get("source") or ""),
            created_at=summary_row.get("created_at"),
            total_amount_cents=int(summary_row.get("total_amount_cents", 0)),
        )

        codes, total_codes = await self._repo.list_codes_in_batch(
            batch_id, status=status, limit=limit, offset=offset
        )
        return AdminBatchDetailResponse(
            batch_id=batch_id,
            source=summary.source,
            created_at=summary.created_at,
            summary=summary,
            codes=[self._doc_to_response(d) for d in codes],
            total_codes=total_codes,
            limit=limit,
            offset=offset,
        )


discount_service = DiscountService()
