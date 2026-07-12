"""Frontend configuration API endpoint.

Provides feature flags and configuration values that the frontend
needs to conditionally render UI elements.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.feature_flags import public_chat_enabled
from app.domains.discount.constants import RESERVATION_TTL_MINUTES

router = APIRouter()
logger = logging.getLogger(__name__)


class FrontendConfig(BaseModel):
    """Frontend configuration response model.

    Contains feature flags and configuration values that control
    frontend behavior and UI rendering.
    """

    # Feature flags
    chat_feedback_enabled: bool
    public_chat_enabled: bool
    langgraph_flights_enabled: bool
    langgraph_hotels_enabled: bool
    use_flightlogic_airports: bool

    # Environment info (useful for debugging)
    environment: str

    # API Keys (for client-side services)
    google_maps_api_key: str | None = None
    revolut_environment: str | None = None

    # Checkout / discounts (single source: app.domains.discount.constants.RESERVATION_TTL_MINUTES)
    voucher_reservation_ttl_minutes: int


@router.get(
    "",
    response_model=FrontendConfig,
    summary="Get frontend configuration",
    description="Returns feature flags and configuration values for the frontend. "
    "This endpoint is public and does not require authentication.",
)
async def get_frontend_config() -> FrontendConfig:
    """Get frontend configuration including feature flags."""
    return FrontendConfig(
        chat_feedback_enabled=settings.VOYA_FEATURE_FLAG_CHAT_FEEDBACK,
        public_chat_enabled=public_chat_enabled(),
        langgraph_flights_enabled=True,  # LangGraph is now the only path (flag removed)
        langgraph_hotels_enabled=True,  # LangGraph is now the only path (flag removed)
        use_flightlogic_airports=settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS,
        environment=settings.ENVIRONMENT,
        google_maps_api_key=settings.GOOGLE_MAPS_API_KEY,
        revolut_environment=settings.REVOLUT_ENVIRONMENT,
        voucher_reservation_ttl_minutes=RESERVATION_TTL_MINUTES,
    )
