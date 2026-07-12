"""Discount / G2A manual voucher domain."""

from app.domains.discount.constants import VoucherStatus
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
from app.domains.discount.models import DiscountDoc
from app.domains.discount.schemas import (
    AdminBatchDetailResponse,
    AdminBatchListResponse,
    AdminBatchSummary,
    AdminDiscountListResponse,
    VoucherApplyRequest,
    VoucherApplyResponse,
    VoucherBatchCreateRequest,
    VoucherBatchCreateResponse,
    VoucherBatchSource,
    VoucherDocResponse,
    VoucherReleaseRequest,
    VoucherReleaseResponse,
)
from app.domains.discount.service import DiscountService, discount_service

__all__ = [
    "AdminBatchDetailResponse",
    "AdminBatchListResponse",
    "AdminBatchSummary",
    "AdminDiscountListResponse",
    "DiscountDoc",
    "DiscountDomainError",
    "DiscountService",
    "VoucherAlreadyUsedError",
    "VoucherAmountTooLowError",
    "VoucherApplyRequest",
    "VoucherApplyResponse",
    "VoucherBatchCreateRequest",
    "VoucherBatchCreateResponse",
    "VoucherBatchSource",
    "VoucherCurrencyInvalidError",
    "VoucherDocResponse",
    "VoucherExpiredError",
    "VoucherInvalidStateError",
    "VoucherNotFoundError",
    "VoucherReleaseConflictError",
    "VoucherReleaseRequest",
    "VoucherReleaseResponse",
    "VoucherReservedByOtherError",
    "VoucherStatus",
    "discount_service",
]
