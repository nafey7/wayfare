"""Tests for GET /api/config (frontend feature flags and public checkout config)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.config import router as config_router
from app.domains.discount.constants import RESERVATION_TTL_MINUTES


def test_frontend_config_includes_voucher_reservation_ttl_from_discount_constants() -> (
    None
):
    app = FastAPI()
    app.include_router(config_router, prefix="/api/config", tags=["Configuration"])
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["voucher_reservation_ttl_minutes"] == RESERVATION_TTL_MINUTES
