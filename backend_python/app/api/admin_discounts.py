"""Admin endpoints for discount / G2A voucher batches (require_admin)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.domains.auth.dependencies import require_admin
from app.domains.discount.exceptions import (
    DiscountDomainError,
    VoucherNotFoundError,
)
from app.domains.discount.schemas import (
    AdminBatchDetailResponse,
    AdminBatchListResponse,
    AdminDiscountListResponse,
    VoucherBatchCreateRequest,
    VoucherBatchCreateResponse,
    VoucherDocResponse,
)
from app.domains.discount.service import discount_service
from app.domains.user.schemas import UserPublic

router = APIRouter(prefix="/discounts", tags=["Admin/Discounts"])


@router.get("", response_model=AdminDiscountListResponse)
async def list_discounts(
    admin: UserPublic = Depends(require_admin),
    status_filter: str | None = Query(None, alias="status"),
    batch_id: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AdminDiscountListResponse:
    _ = admin
    return await discount_service.list_admin_discounts(
        status=status_filter,
        batch_id=batch_id,
        source=source,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/batches", response_model=AdminBatchListResponse)
async def list_batches(
    admin: UserPublic = Depends(require_admin),
) -> AdminBatchListResponse:
    _ = admin
    return await discount_service.list_batches()


@router.post("/batches", response_model=VoucherBatchCreateResponse)
async def create_batch(
    body: VoucherBatchCreateRequest,
    admin: UserPublic = Depends(require_admin),
) -> VoucherBatchCreateResponse:
    try:
        return await discount_service.generate_batch(
            admin_user_id=admin.id,
            count=body.count,
            amount_cents=body.amount_cents,
            source=body.source,
            prefix=body.prefix,
            expires_at=body.expires_at,
        )
    except DiscountDomainError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/batches/{batch_id}/export.csv")
async def export_batch_csv(
    batch_id: str,
    admin: UserPublic = Depends(require_admin),
) -> StreamingResponse:
    _ = admin
    if await discount_service.count_codes_in_batch(batch_id) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    async def _gen():
        async for line in discount_service.export_batch_csv_lines(batch_id):
            yield line.encode("utf-8")

    filename = f"voya-batch-{batch_id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        _gen(),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/batches/{batch_id}", response_model=AdminBatchDetailResponse)
async def get_batch_detail(
    batch_id: str,
    admin: UserPublic = Depends(require_admin),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AdminBatchDetailResponse:
    _ = admin
    try:
        return await discount_service.get_batch_detail(
            batch_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except VoucherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{discount_id}", response_model=VoucherDocResponse)
async def get_discount(
    discount_id: str,
    admin: UserPublic = Depends(require_admin),
) -> VoucherDocResponse:
    _ = admin
    try:
        return await discount_service.get_admin_discount(discount_id)
    except VoucherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{discount_id}/disable", response_model=VoucherDocResponse)
async def disable_discount(
    discount_id: str,
    admin: UserPublic = Depends(require_admin),
) -> VoucherDocResponse:
    _ = admin
    try:
        return await discount_service.disable_discount(discount_id)
    except VoucherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
