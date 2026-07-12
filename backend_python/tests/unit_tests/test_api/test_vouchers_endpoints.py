"""HTTP tests for /api/vouchers apply and release."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.vouchers import router as vouchers_router
from app.domains.auth.dependencies import require_authenticated
from app.domains.common.enums import AuthProvider
from app.domains.discount.exceptions import VoucherNotFoundError
from app.domains.discount.schemas import VoucherApplyResponse
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


@pytest.fixture
def auth_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="u@example.com",
        first_name="U",
        last_name="Ser",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def vouchers_app(auth_user: UserPublic) -> FastAPI:
    app = FastAPI()
    app.include_router(vouchers_router, prefix="/vouchers")

    async def override_auth() -> UserPublic:
        return auth_user

    app.dependency_overrides[require_authenticated] = override_auth
    return app


@pytest.fixture
def vouchers_client(vouchers_app: FastAPI) -> TestClient:
    return TestClient(vouchers_app)


def test_apply_requires_body_validation(vouchers_client: TestClient) -> None:
    resp = vouchers_client.post("/vouchers/apply", json={})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@patch("app.api.vouchers.discount_service")
def test_apply_success_snake_case_response(
    mock_svc: AsyncMock,
    vouchers_client: TestClient,
    auth_user: UserPublic,
) -> None:
    exp = datetime(2026, 6, 1, tzinfo=UTC)
    mock_svc.apply_voucher = AsyncMock(
        return_value=VoucherApplyResponse(
            redemption_id="abc123",
            code="VOYA-AA-BB",
            discount_cents=500,
            new_total_cents=9500,
            currency="usd",
            reservation_expires_at=exp,
        )
    )
    resp = vouchers_client.post(
        "/vouchers/apply",
        json={
            "code": "VOYA-AA-BB",
            "voya_booking_reference": "VOYA-REF-1",
            "amount_cents": 10000,
            "booking_type": "flight",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["redemption_id"] == "abc123"
    assert data["new_total_cents"] == 9500
    assert "reservation_expires_at" in data
    mock_svc.apply_voucher.assert_awaited_once()
    call_kw = mock_svc.apply_voucher.await_args.kwargs
    assert call_kw["user_id"] == auth_user.id


@patch("app.api.vouchers.discount_service")
def test_apply_maps_not_found(mock_svc: AsyncMock, vouchers_client: TestClient) -> None:
    mock_svc.apply_voucher = AsyncMock(side_effect=VoucherNotFoundError("missing"))
    resp = vouchers_client.post(
        "/vouchers/apply",
        json={
            "code": "VOYA-XX-YY",
            "voya_booking_reference": "VOYA-REF-1",
            "amount_cents": 10000,
        },
    )
    assert resp.status_code == 404


def test_apply_unauthenticated() -> None:
    app = FastAPI()
    app.include_router(vouchers_router, prefix="/vouchers")

    async def deny() -> UserPublic:
        raise HTTPException(status_code=401, detail="nope")

    app.dependency_overrides[require_authenticated] = deny
    client = TestClient(app)
    resp = client.post(
        "/vouchers/apply",
        json={
            "code": "VOYA-AA-BB",
            "voya_booking_reference": "VOYA-REF-1",
            "amount_cents": 10000,
        },
    )
    assert resp.status_code == 401


@patch("app.api.vouchers.discount_service")
def test_release_success(mock_svc: AsyncMock, vouchers_client: TestClient) -> None:
    mock_svc.release_voucher = AsyncMock(return_value=None)
    resp = vouchers_client.post(
        "/vouchers/release",
        json={"redemption_id": "507f1f77bcf86cd799439011"},
    )
    assert resp.status_code == 200
    assert resp.json()["released"] is True
