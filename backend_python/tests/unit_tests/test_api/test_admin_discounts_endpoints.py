"""HTTP tests for /api/admin/discounts (admin-only)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.admin_discounts import router as admin_discounts_router
from app.domains.auth.dependencies import require_admin
from app.domains.common.enums import AuthProvider
from app.domains.discount.schemas import (
    AdminDiscountListResponse,
    VoucherBatchCreateResponse,
)
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


@pytest.fixture
def admin_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="admin@example.com",
        first_name="A",
        last_name="Dmin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


_API_ADMIN = "/api/admin"


@pytest.fixture
def admin_discounts_app(admin_user: UserPublic) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_discounts_router, prefix=_API_ADMIN)

    async def override_admin() -> UserPublic:
        return admin_user

    app.dependency_overrides[require_admin] = override_admin
    return app


@pytest.fixture
def admin_client(admin_discounts_app: FastAPI) -> TestClient:
    return TestClient(admin_discounts_app)


def test_list_discounts_forbidden_for_non_admin() -> None:
    app = FastAPI()
    app.include_router(admin_discounts_router, prefix=_API_ADMIN)

    async def deny() -> UserPublic:
        raise HTTPException(status_code=403, detail="Admin access required")

    app.dependency_overrides[require_admin] = deny
    client = TestClient(app)
    resp = client.get(f"{_API_ADMIN}/discounts")
    assert resp.status_code == 403


@patch("app.api.admin_discounts.discount_service")
def test_list_discounts_ok(
    mock_svc: AsyncMock,
    admin_client: TestClient,
) -> None:
    mock_svc.list_admin_discounts = AsyncMock(
        return_value=AdminDiscountListResponse(
            items=[],
            total=0,
            limit=50,
            offset=0,
        )
    )
    resp = admin_client.get(f"{_API_ADMIN}/discounts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@patch("app.api.admin_discounts.discount_service")
def test_create_batch_ok(mock_svc: AsyncMock, admin_client: TestClient) -> None:
    now = datetime.now(UTC)
    mock_svc.generate_batch = AsyncMock(
        return_value=VoucherBatchCreateResponse(
            batch_id="b1",
            count=2,
            total_amount_cents=200,
            currency="USD",
            created_at=now,
            sample_codes=["VOYA-AA-AA", "VOYA-BB-BB"],
        )
    )
    resp = admin_client.post(
        f"{_API_ADMIN}/discounts/batches",
        json={
            "count": 2,
            "amount_cents": 100,
            "source": "G2A_TEST",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_id"] == "b1"
    assert body["currency"] == "USD"


@patch("app.api.admin_discounts.discount_service")
def test_csv_export_headers_and_stream(
    mock_svc: AsyncMock,
    admin_client: TestClient,
) -> None:
    mock_svc.count_codes_in_batch = AsyncMock(return_value=2)

    async def lines(_batch_id: str):
        yield "VOYA-1-1\n"
        yield "VOYA-2-2\n"

    mock_svc.export_batch_csv_lines = lines  # type: ignore[method-assign]

    resp = admin_client.get(f"{_API_ADMIN}/discounts/batches/b1/export.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    disp = resp.headers.get("content-disposition", "")
    assert "attachment" in disp.lower()
    assert "voya-batch-b1.csv" in disp
    assert resp.content == b"VOYA-1-1\nVOYA-2-2\n"


@patch("app.api.admin_discounts.discount_service")
def test_csv_export_404_empty_batch(
    mock_svc: AsyncMock,
    admin_client: TestClient,
) -> None:
    mock_svc.count_codes_in_batch = AsyncMock(return_value=0)
    resp = admin_client.get(f"{_API_ADMIN}/discounts/batches/missing/export.csv")
    assert resp.status_code == 404
