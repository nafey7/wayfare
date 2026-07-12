"""Saved itineraries API - persist and retrieve AI-generated itineraries."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.auth.dependencies import require_authenticated
from app.domains.saved_itinerary import (
    SAVED_ITINERARIES_LIST_LIMIT,
    SavedItineraryCreate,
    SavedItineraryResponse,
    create_saved_itinerary,
    delete_saved_itinerary,
    get_saved_itineraries_for_user,
    get_saved_itinerary_by_id,
)
from app.domains.user.schemas import UserPublic

router = APIRouter()


@router.post(
    "", response_model=SavedItineraryResponse, status_code=status.HTTP_201_CREATED
)
async def save_itinerary(
    request: SavedItineraryCreate,
    current_user: UserPublic = Depends(require_authenticated),
) -> SavedItineraryResponse:
    """Save an AI-generated itinerary for the current user."""
    return await create_saved_itinerary(str(current_user.id), request)


@router.get(
    "",
    response_model=list[SavedItineraryResponse],
    summary="List saved itineraries",
    description=(
        f"Returns up to {SAVED_ITINERARIES_LIST_LIMIT} itineraries for the current user, "
        "newest first. There is no pagination; older items beyond this cap are omitted."
    ),
)
async def list_itineraries(
    current_user: UserPublic = Depends(require_authenticated),
) -> list[SavedItineraryResponse]:
    """List saved itineraries (capped; see route description)."""
    return await get_saved_itineraries_for_user(str(current_user.id))


@router.get("/{itinerary_id}", response_model=SavedItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    current_user: UserPublic = Depends(require_authenticated),
) -> SavedItineraryResponse:
    """Get a single saved itinerary by ID. Owner only."""
    result = await get_saved_itinerary_by_id(itinerary_id, str(current_user.id))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found",
        )
    return result


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: str,
    current_user: UserPublic = Depends(require_authenticated),
) -> None:
    """Delete a saved itinerary. Owner only."""
    success = await delete_saved_itinerary(itinerary_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found",
        )
