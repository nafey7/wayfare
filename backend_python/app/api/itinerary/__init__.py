"""Itinerary API module.

Provides endpoints for n8n Itinerary Agent integration.
"""

from fastapi import APIRouter

from app.api.itinerary.capabilities import router as capabilities_router
from app.api.itinerary.generate import router as generate_router

itinerary_router = APIRouter()

# Direct itinerary generation (Day Plan form — no chat overhead)
itinerary_router.include_router(generate_router, tags=["Itinerary"])

# Include capabilities endpoints under /capabilities prefix
itinerary_router.include_router(
    capabilities_router, prefix="/capabilities", tags=["Itinerary Capabilities"]
)

__all__ = ["itinerary_router"]
