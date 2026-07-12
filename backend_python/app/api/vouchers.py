"""Traveler-facing voucher apply / release (authenticated)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.auth.dependencies import require_authenticated
from app.domains.discount.exceptions import (
    VoucherAlreadyUsedError,
    VoucherAmountTooLowError,
    VoucherCurrencyInvalidError,
    VoucherExpiredError,
    VoucherInvalidStateError,
    VoucherNotFoundError,
    VoucherReleaseConflictError,
    VoucherReservedByOtherError,
)
from app.domains.discount.schemas import (
    VoucherApplyRequest,
    VoucherApplyResponse,
    VoucherReleaseRequest,
    VoucherReleaseResponse,
)
from app.domains.discount.service import discount_service
from app.domains.user.schemas import UserPublic

router = APIRouter(tags=["Vouchers"])


def _map_discount_error(exc: Exception) -> HTTPException:
    if isinstance(exc, VoucherNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, VoucherAlreadyUsedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, VoucherExpiredError):
        return HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc))
    if isinstance(exc, VoucherReservedByOtherError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, VoucherAmountTooLowError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    if isinstance(exc, VoucherCurrencyInvalidError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    if isinstance(exc, VoucherInvalidStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, VoucherReleaseConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected error",
    )


@router.post("/apply", response_model=VoucherApplyResponse)
async def apply_voucher(
    body: VoucherApplyRequest,
    user: UserPublic = Depends(require_authenticated),
) -> VoucherApplyResponse:
    try:
        return await discount_service.apply_voucher(
            user_id=user.id,
            code=body.code,
            voya_booking_reference=body.voya_booking_reference,
            amount_cents=body.amount_cents,
            booking_type=body.booking_type,
            currency=body.currency,
        )
    except (
        VoucherNotFoundError,
        VoucherAlreadyUsedError,
        VoucherExpiredError,
        VoucherReservedByOtherError,
        VoucherAmountTooLowError,
        VoucherCurrencyInvalidError,
        VoucherInvalidStateError,
    ) as e:
        raise _map_discount_error(e) from e


@router.post("/release", response_model=VoucherReleaseResponse)
async def release_voucher(
    body: VoucherReleaseRequest,
    user: UserPublic = Depends(require_authenticated),
) -> VoucherReleaseResponse:
    try:
        await discount_service.release_voucher(
            user_id=user.id,
            redemption_id=body.redemption_id,
        )
        return VoucherReleaseResponse()
    except (VoucherNotFoundError, VoucherReleaseConflictError) as e:
        raise _map_discount_error(e) from e
