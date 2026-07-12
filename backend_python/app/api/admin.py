"""Administrative endpoints for user management and system operations."""

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from pydantic import Field

from app.api.admin_discounts import router as admin_discounts_router
from app.domains.agent_prompt import (
    AgentPromptCreate,
    AgentPromptListResponse,
    AgentPromptResponse,
    AgentPromptUpdate,
    agent_prompt_service,
)
from app.domains.auth.dependencies import require_admin
from app.domains.common import MessageResponse
from app.domains.flight.enums import TicketStatus
from app.domains.flight.schemas import TripDetailsRequest
from app.domains.user import UserService
from app.domains.user.enums import UserStatus
from app.domains.user.schemas import (
    UserPublic,
    UserResponse,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.shared.schemas import StrictModel

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def _first_error_message(errors: Any, default: str = "Unknown error.") -> str:
    """Build a single user-facing message from the first error in a list.

    Uses .message (and optionally .code) so the API returns the provider message
    (e.g. FlightLogic "Booking already done with Current Session ID.") instead
    of a serialized object.
    """
    if not errors or not isinstance(errors, (list, tuple)) or len(errors) == 0:
        return default
    first = errors[0]
    msg = getattr(first, "message", None) or (
        first.get("message") if isinstance(first, dict) else None
    )
    if not msg:
        return default
    return msg


async def _get_updated_user_or_404(user_id: str) -> UserPublic:
    """Fetch updated user or raise 404 if not found.

    Args:
        user_id: ID of the user to fetch

    Returns:
        UserPublic model

    Raises:
        HTTPException: 404 if user not found
    """
    updated_user = await UserService.get_user_public(user_id)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return updated_user


# ==============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ==============================================================================


# ==============================================================================
# ADMIN BOOKINGS (all booking_events)
# ==============================================================================


@router.get("/bookings")
async def get_all_bookings(
    limit: int = Query(50, ge=1, le=200, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Skip first N events"),
    _admin: UserPublic = Depends(require_admin),
) -> dict[str, Any]:
    """Get all booking events from booking_events collection (admin only).
    Each event includes user_display_name set to the user's email (from users collection).
    """
    from app.domains.bookings.service import BookingService
    from app.domains.user.repository import get_users_by_ids

    events, total = await BookingService.list_all_events(limit=limit, offset=offset)
    unique_user_ids = list({e.user_id for e in events})
    users = await get_users_by_ids(unique_user_ids)
    user_display: dict[str, str] = {}
    for u in users:
        uid = str(u.id) if u.id else ""
        if uid:
            user_display[uid] = getattr(u, "email", None) or "Unknown"
    event_dicts = [
        {**e.model_dump(), "user_display_name": user_display.get(e.user_id, "Unknown")}
        for e in events
    ]
    return {
        "events": event_dicts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/bookings/by-reference/{voya_booking_reference}")
async def get_booking_event_by_reference(
    voya_booking_reference: str,
    _admin: UserPublic = Depends(require_admin),
) -> dict[str, Any]:
    """Get a single booking event by VOYA reference (admin only). Returns full event including id, payload, hotel_reference_number for retry."""
    from app.domains.bookings.service import BookingService

    event = await BookingService.get_event_by_voya_reference(voya_booking_reference)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking not found: {voya_booking_reference}",
        )
    return event.model_dump(by_alias=True, exclude_none=False)


class AdminBookingRetryRequest(StrictModel):
    """Request body for admin booking retry."""

    booking_event_id: str = Field(..., description="MongoDB _id of the booking event")


@router.post("/bookings/retry")
async def admin_retry_booking(
    body: AdminBookingRetryRequest,
    _admin: UserPublic = Depends(require_admin),
) -> dict[str, Any]:
    """Retry booking: FLIGHT LCC = re-call booking API with stored payload; GDS = issue tickets.
    HOTEL = re-call hotel book API with stored payload (admin only)."""
    from app.domains.bookings.service import BookingService
    from app.domains.flight.schemas import TicketOrderRequest
    from integrations.flightlogic import get_flights_client

    event = await BookingService.get_event_by_id(body.booking_event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking event not found",
        )
    if event.action != "BOOKED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retry is only supported for BOOKED events",
        )

    event_type = getattr(event, "event_type", "FLIGHT")
    client = get_flights_client(_admin)
    voya_ref = event.voya_booking_reference or ""

    # Hotel retry: re-call hotel book API with stored payload
    if event_type == "HOTEL":
        if not event.payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hotel retry requires stored payload; none found",
            )
        try:
            hotel_response = await client.book_hotel_with_payload(event.payload)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Hotel booking failed: {e!s}",
            ) from e
        if hotel_response.status != "Success":
            detail = (
                hotel_response.errors.get("message", "Booking failed.")
                if hotel_response.errors
                else "Booking failed."
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            )
        if hotel_response.supplier_confirmation_num:
            await BookingService.update_external_reference(
                voya_ref, hotel_response.supplier_confirmation_num
            )
        if hotel_response.reference_num:
            await BookingService.update_hotel_reference_number(
                voya_ref, hotel_response.reference_num
            )
        # Send hotel booking confirmation email on successful retry (same as normal flow)
        try:
            from app.domains.hotel.events import HotelEventHandler

            user_id = str(event.user_id)
            booking_details = getattr(hotel_response, "booking_details", None) or {}
            ext_ref = (
                hotel_response.supplier_confirmation_num
                or event.external_booking_reference
            )
            await HotelEventHandler.handle_booking_confirmed(
                user_id,
                ext_ref,
                booking_details,
                voya_booking_reference=voya_ref,
                booking_request=None,
                reference_num=hotel_response.reference_num,
            )
        except Exception as e:
            logger.warning(
                "Admin hotel retry: failed to send confirmation email: %s", e
            )
        return {
            "success": True,
            "voya_booking_reference": voya_ref,
            "external_booking_reference": hotel_response.supplier_confirmation_num
            or event.external_booking_reference,
        }

    # Flight retry
    if event_type != "FLIGHT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retry is only supported for FLIGHT or HOTEL BOOKED events",
        )

    if event.carrier_type == "LCC":
        if not event.payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LCC retry requires stored payload; none found",
            )
        try:
            lcc_booking_response = await client.create_booking_with_payload(
                event.payload
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"FlightLogic booking failed: {e!s}",
            ) from e
        if not lcc_booking_response.is_successful:
            detail = _first_error_message(
                getattr(lcc_booking_response, "errors", None),
                default="Booking failed.",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            )
        pnr_code = None
        pnr_airline_code = None
        pnr_airline_name = None
        pnr_status = None
        if lcc_booking_response.airline_pnr:
            pnr_code = lcc_booking_response.airline_pnr.pnr_code
            if lcc_booking_response.airline_pnr.airline:
                pnr_airline_code = lcc_booking_response.airline_pnr.airline.iata_code
                pnr_airline_name = lcc_booking_response.airline_pnr.airline.airline_name
            if lcc_booking_response.airline_pnr.status:
                pnr_status = lcc_booking_response.airline_pnr.status.value
        ticket_time_limit_utc = None
        if (
            lcc_booking_response.ticket_time_limit
            and lcc_booking_response.ticket_time_limit.value
        ):
            ticket_time_limit_utc = lcc_booking_response.ticket_time_limit.value
        voya_ref = event.voya_booking_reference or ""
        await BookingService.update_booking_after_flight_confirmation(
            voya_ref,
            lcc_booking_response.external_booking_reference,
            airline_pnr_code=pnr_code,
            airline_pnr_airline_code=pnr_airline_code,
            airline_pnr_airline_name=pnr_airline_name,
            airline_pnr_status=pnr_status,
            ticket_time_limit=ticket_time_limit_utc,
        )
        # Send Flight Booking Confirmation email and update PNR on successful LCC retry (same as normal flow)
        try:
            from app.domains.flight.events import FlightEventHandler
            from app.domains.flight.service import _extract_pnrs_from_trip_details

            user_id = str(event.user_id)
            trip_details = await client.get_trip_details(
                TripDetailsRequest(
                    voya_booking_reference=voya_ref,
                    external_booking_reference=lcc_booking_response.external_booking_reference,
                )
            )
            # Update booking event PNR list from trip details
            if trip_details and getattr(trip_details, "segments", None):
                pnrs = _extract_pnrs_from_trip_details(trip_details)
                if pnrs:
                    try:
                        await BookingService.update_booking_pnr(voya_ref, pnrs)
                    except Exception as pnr_err:
                        logger.warning(
                            "Admin LCC retry: failed to update booking PNR: %s",
                            pnr_err,
                        )
            booking_details = (
                lcc_booking_response.model_dump()
                if hasattr(lcc_booking_response, "model_dump")
                else {}
            )
            await FlightEventHandler.handle_booking_confirmed(
                user_id,
                lcc_booking_response.external_booking_reference,
                booking_details,
                voya_booking_reference=voya_ref,
                revalidate_response=None,
                booking_request=None,
                trip_details=trip_details,
                booking_response_pnr=pnr_code,
                cancellation_policy_text=getattr(
                    event, "cancellation_policy_text", None
                ),
            )
        except Exception as e:
            logger.warning("Admin LCC retry: failed to send confirmation email: %s", e)
        return {
            "success": True,
            "voya_booking_reference": voya_ref,
            "external_booking_reference": lcc_booking_response.external_booking_reference,
        }

    if event.carrier_type == "GDS":
        ext_ref = event.external_booking_reference
        if not ext_ref:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GDS retry requires external_booking_reference; none found",
            )
        voya_ref = event.voya_booking_reference or ""
        # GDS: call trip details before ticket order; skip if already ticketed or cancelled
        try:
            trip_details = await client.get_trip_details(
                TripDetailsRequest(
                    voya_booking_reference=voya_ref,
                    external_booking_reference=ext_ref,
                )
            )
            if trip_details and trip_details.ticket_status in (
                TicketStatus.TICKETED,
                TicketStatus.CANCELLED,
            ):
                logger.info(
                    "Admin GDS retry: skipping ticket order - booking already %s",
                    trip_details.ticket_status.value,
                    extra={
                        "voya_booking_reference": voya_ref,
                        "ticket_status": trip_details.ticket_status.value,
                    },
                )
                return {
                    "success": True,
                    "voya_booking_reference": voya_ref,
                    "external_booking_reference": ext_ref,
                    "message": (
                        "Tickets already issued"
                        if trip_details.ticket_status == TicketStatus.TICKETED
                        else "Booking was cancelled"
                    ),
                }
        except Exception as e:
            logger.warning(
                "Admin GDS retry: trip details failed: %s",
                e,
                extra={"voya_booking_reference": voya_ref},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Trip details failed; cannot proceed with ticket order: {e!s}",
            ) from e

        try:
            ticket_request = TicketOrderRequest(
                voya_booking_reference=voya_ref,
                external_booking_reference=ext_ref,
                payment_id=None,
                cancellation_policy_text=getattr(
                    event, "cancellation_policy_text", None
                ),
            )
            ticket_response = await client.issue_tickets(ticket_request)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"FlightLogic ticket order failed: {e!s}",
            ) from e
        if not ticket_response.success:
            detail = _first_error_message(
                getattr(ticket_response, "errors", None),
                default="Ticket order failed.",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            )
        # Send Flight Tickets Issued email and update PNR on successful GDS retry (same as normal flow)
        try:
            from app.domains.flight.events import FlightEventHandler
            from app.domains.flight.service import _extract_pnrs_from_trip_details

            user_id = str(event.user_id)
            trip_details = await client.get_trip_details(
                TripDetailsRequest(
                    voya_booking_reference=voya_ref,
                    external_booking_reference=ext_ref,
                )
            )
            # Update booking event PNR list from trip details
            if trip_details and getattr(trip_details, "segments", None):
                pnrs = _extract_pnrs_from_trip_details(trip_details)
                if pnrs:
                    try:
                        await BookingService.update_booking_pnr(voya_ref, pnrs)
                    except Exception as pnr_err:
                        logger.warning(
                            "Admin GDS retry: failed to update booking PNR: %s",
                            pnr_err,
                        )
            booking_event_for_policy = (
                await BookingService.get_latest_booking_by_voya_reference(voya_ref)
            )
            cancellation_policy_text = (
                booking_event_for_policy.cancellation_policy_text
                if booking_event_for_policy
                else None
            ) or getattr(event, "cancellation_policy_text", None)
            ticket_numbers = getattr(ticket_response, "ticket_numbers", None) or []
            await FlightEventHandler.handle_tickets_issued(
                user_id,
                ext_ref,
                ticket_numbers,
                voya_ref,
                trip_details,
                cancellation_policy_text=cancellation_policy_text,
            )
            await BookingService.update_booking_dates_and_flags(
                voya_ref,
                date_tickets_issued=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning(
                "Admin GDS retry: failed to send tickets issued email: %s", e
            )
        return {
            "success": True,
            "voya_booking_reference": voya_ref,
            "external_booking_reference": ticket_response.external_booking_reference,
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Retry requires carrier_type LCC or GDS",
    )


# ==============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ==============================================================================


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    user_status: UserStatus | None = Query(
        None, description="Filter by user status", alias="status"
    ),
    _admin: UserPublic = Depends(require_admin),
) -> list[UserResponse]:
    """Get all users (admin only).

    Supports pagination and filtering by status.
    """
    from app.database.dependencies import get_database

    db = await get_database()

    # Build query
    query: dict[str, Any] = {}
    if user_status is not None:
        query["status"] = user_status.value

    # Get users with pagination
    cursor = db.users.find(query).skip(skip).limit(limit)

    users: list[UserResponse] = []
    async for user_data in cursor:
        # Create a temporary UserPublic from the data first
        from app.database.models.user import UserModel

        user_model = UserModel(**user_data)
        users.append(UserResponse.from_user(UserPublic.from_model(user_model)))

    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse:
    """Get a specific user by ID (admin only)."""
    user = await UserService.get_user_public(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return UserResponse.from_user(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse:
    """Update any user (admin only).

    Admins can update any field including sensitive ones.
    """
    # Get the user first to ensure they exist
    existing_user = await UserService.get_user_public(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    updated_user = await UserService(_admin).update_user(user_id, request)

    return UserResponse.from_user(updated_user)


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse:
    """Update user status (admin only).

    Can be used to activate, suspend, or soft-delete users.
    """
    # Update user status using dedicated function

    success = await UserService(_admin).update_user_status(user_id, request.status)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found or update failed",
        )

    updated_user = await _get_updated_user_or_404(user_id)
    return UserResponse.from_user(updated_user)


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role: str = Query(..., description="New role: user or admin"),
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse:
    """Update user role (admin only).

    Roles:
    - user: Standard user with access to regular features
    - admin: Full system access, can manage all users and settings
    """
    from app.domains.admin.service import update_user_role

    # Update role using admin service
    success = await update_user_role(user_id, role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update role for user {user_id}. Check if user exists and role is valid.",
        )

    # Get updated user
    updated_user = await _get_updated_user_or_404(user_id)
    return UserResponse.from_user(updated_user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    permanent: bool = Query(
        False, description="Permanently delete (not just soft delete)"
    ),
    _admin: UserPublic = Depends(require_admin),
) -> MessageResponse:
    """Delete a user (admin only).

    By default, performs a soft delete (sets status to DELETED).
    Use permanent=true for hard delete.
    """
    if permanent:
        # Hard delete - actually remove from database
        success = await UserService(_admin).delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return MessageResponse(message=f"User {user_id} permanently deleted")

    # Soft delete - just update status
    success = await UserService(_admin).update_user_status(user_id, UserStatus.DELETED)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    await _get_updated_user_or_404(user_id)  # Verify user exists before deletion
    return MessageResponse(message=f"User {user_id} marked as deleted")


@router.post("/users/{user_id}/verify", response_model=UserResponse)
async def verify_user_email(
    user_id: str,
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse:
    """Manually verify a user's email (admin only)."""
    # Use verify_email function
    success = await UserService.verify_email(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    updated_user = await _get_updated_user_or_404(user_id)
    return UserResponse.from_user(updated_user)


@router.get("/users/search/email", response_model=Optional[UserResponse])
async def search_user_by_email(
    email: str = Query(..., description="Email to search for"),
    _admin: UserPublic = Depends(require_admin),
) -> UserResponse | None:
    """Search for a user by email (admin only)."""
    user = await UserService.get_user_public_by_email(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found",
        )

    return UserResponse.from_user(user)


# ==============================================================================
# AGENT PROMPT ENDPOINTS
# ==============================================================================


@router.get("/agent-prompts", response_model=AgentPromptListResponse)
async def get_all_agent_prompts(
    _admin: UserPublic = Depends(require_admin),
) -> AgentPromptListResponse:
    """Get all agent prompts (admin only)."""
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"🤖 [Agent Prompts] Admin {_admin.email} requesting all agent prompts")

    prompts = await agent_prompt_service.get_all_prompts()
    logger.info(f"🤖 [Agent Prompts] Found {len(prompts)} prompts, returning response")

    return AgentPromptListResponse(prompts=prompts, total=len(prompts))


@router.get("/agent-prompts/{agent_name}", response_model=AgentPromptResponse)
async def get_agent_prompt(
    agent_name: str,
    _admin: UserPublic = Depends(require_admin),
) -> AgentPromptResponse:
    """Get prompt for specific agent (admin only)."""
    prompt = await agent_prompt_service.get_prompt_by_agent(agent_name)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prompt found for agent: {agent_name}",
        )
    return prompt


@router.post("/agent-prompts", response_model=AgentPromptResponse)
async def create_agent_prompt(
    prompt_data: AgentPromptCreate,
    admin: UserPublic = Depends(require_admin),
) -> AgentPromptResponse:
    """Create a new agent prompt (admin only)."""
    return await agent_prompt_service.create_prompt(prompt_data, admin.id)


@router.put("/agent-prompts/{agent_name}", response_model=AgentPromptResponse)
async def update_agent_prompt(
    agent_name: str,
    prompt_data: AgentPromptUpdate,
    admin: UserPublic = Depends(require_admin),
) -> AgentPromptResponse:
    """Update an agent prompt (admin only)."""
    import logging

    logger = logging.getLogger(__name__)

    # Log the prompt update attempt
    logger.info(
        f"🔄 [Prompt Update] Admin {admin.email} updating prompt for agent: {agent_name}"
    )
    # Get the current prompt for comparison
    try:
        current_prompt = await agent_prompt_service.get_prompt_by_agent(agent_name)
        if current_prompt:
            logger.info(f"📋 [Prompt Update] Current prompt for {agent_name}:")
            logger.info(f"   Goal: {current_prompt.goal}")
            logger.info(f"   Active: {current_prompt.is_active}")
            logger.info(
                f"   Template (first 200 chars): {current_prompt.prompt_template[:200]}..."
            )
        else:
            logger.info(
                f"📋 [Prompt Update] No existing prompt found for {agent_name} - creating new one"
            )
    except Exception as e:
        logger.warning(f"📋 [Prompt Update] Could not fetch current prompt: {e}")

    # Log the new data being applied
    logger.info(f"📝 [Prompt Update] New data for {agent_name}:")
    logger.info(f"   Goal: {prompt_data.goal}")
    logger.info(f"   Active: {prompt_data.is_active}")
    logger.info(
        f"   Template (first 200 chars): {prompt_data.prompt_template[:200] if prompt_data.prompt_template else 'None'}..."
    )
    # Apply the update
    updated_prompt = await agent_prompt_service.update_prompt(
        agent_name, prompt_data, admin.id
    )

    if not updated_prompt:
        logger.error(
            f"❌ [Prompt Update] Failed to update prompt for agent: {agent_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prompt found for agent: {agent_name}",
        )

    # Log successful update with final state
    logger.info(f"✅ [Prompt Update] Successfully updated prompt for {agent_name}")
    logger.info(f"📊 [Prompt Update] Final state for {agent_name}:")
    logger.info(f"   ID: {updated_prompt.id}")
    logger.info(f"   Goal: {updated_prompt.goal}")
    logger.info(f"   Active: {updated_prompt.is_active}")
    logger.info(f"   Updated by: {admin.email} (ID: {admin.id})")
    logger.info(f"   Updated at: {updated_prompt.updated_at}")
    logger.info(
        f"   Template length: {len(updated_prompt.prompt_template) if updated_prompt.prompt_template else 0} characters"
    )
    # Log to agents logger as well for visibility
    from app.core.logging import get_agents_logger

    agents_logger = get_agents_logger()
    agents_logger.info(
        f"🔄 PROMPT_UPDATE | Agent: {agent_name} | Admin: {admin.email} | Goal: {updated_prompt.goal} | Active: {updated_prompt.is_active}"
    )
    return updated_prompt


@router.post("/agent-prompts/initialize", response_model=MessageResponse)
async def initialize_default_prompts(
    _admin: UserPublic = Depends(require_admin),
) -> MessageResponse:
    """Initialize default prompts for all agents (admin only)."""
    await agent_prompt_service.initialize_default_prompts()
    return MessageResponse(message="Default prompts initialized successfully")


# ==============================================================================
# DIAGNOSTIC ENDPOINTS
# ==============================================================================


@router.post("/debug/generate-token", response_model=dict)
async def generate_admin_token_for_testing(
    email: str = Query(..., description="Email of existing admin user"),
) -> dict:
    """Generate JWT token for existing admin user (DEBUG ONLY).

    This endpoint is only available when ENABLE_DEV_TOOLS=true.
    Use this to generate JWT tokens for testing admin endpoints.
    """
    import os
    import uuid

    from app.domains.auth.service import AuthService

    # Only allow this endpoint when dev tools are enabled
    if os.getenv("ENABLE_DEV_TOOLS", "false").lower() not in ["true", "1", "yes"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production",
        )

    # Find the user by email
    from app.domains.user import UserService

    user = await UserService.get_user_public_by_email(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found",
        )

    # Check if user is admin
    from app.domains.user.constants import UserRole

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {email} is not an admin (role: {user.role})",
        )

    # Generate a session ID and create token
    session_id = str(uuid.uuid4())
    access_token = AuthService.create_access_token(str(user.id), session_id)

    return {
        "message": f"Generated JWT token for admin user: {email}",
        "user_id": str(user.id),
        "user_email": email,
        "user_role": user.role,
        "session_id": session_id,
        "access_token": access_token,
        "token_preview": f"{access_token[:50]}...",
        "usage_instructions": [
            "Copy the 'access_token' value above",
            "Paste it into the JWT token field on the admin pages",
            "Token expires in 30 minutes",
            "Use this token to authenticate admin API calls",
        ],
    }


@router.get("/email/diagnostics")
async def email_diagnostics(
    admin: UserPublic = Depends(require_admin),
) -> dict[str, Any]:
    """Comprehensive email system diagnostics (admin only)."""
    import logging

    from app.core.config import settings
    from app.database.connection import SendGridHealthChecker
    from app.domains.email.service import EmailService

    logger = logging.getLogger(__name__)
    logger.info(
        f"🔍 [Email Diagnostics] Admin {admin.email} requesting email diagnostics"
    )
    diagnostics: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "admin_user": admin.email,
        "configuration": {},
        "health_checks": {},
        "service_status": {},
        "recommendations": [],
    }

    # === CONFIGURATION ANALYSIS ===
    diagnostics["configuration"] = {
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "use_mailhog": settings.USE_MAILHOG,
        "sendgrid_api_key_configured": bool(settings.SENDGRID_API_KEY),
        "sendgrid_api_key_length": (
            len(settings.SENDGRID_API_KEY) if settings.SENDGRID_API_KEY else 0
        ),
        "sendgrid_from_email": settings.SENDGRID_FROM_EMAIL,
        "mailhog_host": settings.MAILHOG_HOST,
        "mailhog_port": settings.MAILHOG_PORT,
    }

    # === SENDGRID HEALTH CHECK ===
    try:
        if settings.SENDGRID_API_KEY:
            checker = SendGridHealthChecker()
            health_result = await checker.ping()
            diagnostics["health_checks"]["sendgrid"] = {
                "status": "healthy",
                "message": health_result,
                "api_key_prefix": (
                    settings.SENDGRID_API_KEY[:10] + "..."
                    if settings.SENDGRID_API_KEY
                    else "None"
                ),
            }
        else:
            diagnostics["health_checks"]["sendgrid"] = {
                "status": "misconfigured",
                "message": "SendGrid API key not configured",
                "api_key_prefix": "None",
            }
    except Exception as e:
        diagnostics["health_checks"]["sendgrid"] = {
            "status": "unhealthy",
            "message": str(e),
            "api_key_prefix": (
                settings.SENDGRID_API_KEY[:10] + "..."
                if settings.SENDGRID_API_KEY
                else "None"
            ),
        }

    # === EMAIL SERVICE INITIALIZATION TEST ===
    try:
        # Test email client initialization
        init_result = EmailService._initialize_email_client()
        diagnostics["service_status"]["initialization"] = {
            "success": init_result,
            "provider": "sendgrid" if not settings.USE_MAILHOG else "mailhog",
        }
    except Exception as e:
        diagnostics["service_status"]["initialization"] = {
            "success": False,
            "error": str(e),
            "provider": "unknown",
        }

    # === DOMAIN VERIFICATION ===
    from_domain = (
        settings.SENDGRID_FROM_EMAIL.split("@")[1]
        if "@" in settings.SENDGRID_FROM_EMAIL
        else "unknown"
    )
    diagnostics["service_status"]["domain_info"] = {
        "from_email": settings.SENDGRID_FROM_EMAIL,
        "domain": from_domain,
        "is_myvoya_domain": from_domain
        in ["myvoya.ai", "app.myvoya.ai", "www.myvoya.ai"],
    }

    # === GENERATE RECOMMENDATIONS ===
    if settings.ENVIRONMENT == "production":
        if not settings.SENDGRID_API_KEY:
            diagnostics["recommendations"].append(
                {
                    "priority": "CRITICAL",
                    "category": "Configuration",
                    "issue": "SendGrid API key not configured in production",
                    "solution": "Set SENDGRID_API_KEY environment variable with valid SendGrid API key",
                }
            )
        if settings.USE_MAILHOG:
            diagnostics["recommendations"].append(
                {
                    "priority": "HIGH",
                    "category": "Configuration",
                    "issue": "MailHog is enabled in production environment",
                    "solution": "Set USE_MAILHOG=false in production environment",
                }
            )
        if diagnostics["health_checks"]["sendgrid"]["status"] != "healthy":
            diagnostics["recommendations"].append(
                {
                    "priority": "HIGH",
                    "category": "Service",
                    "issue": f"SendGrid health check failed: {diagnostics['health_checks']['sendgrid']['message']}",
                    "solution": "Verify SendGrid API key is valid and has proper permissions",
                }
            )
        if not diagnostics["service_status"]["domain_info"]["is_myvoya_domain"]:
            diagnostics["recommendations"].append(
                {
                    "priority": "MEDIUM",
                    "category": "Domain",
                    "issue": f"From email domain '{from_domain}' may not be verified with SendGrid",
                    "solution": "Ensure domain is verified in SendGrid and matches production domain",
                }
            )
    if not diagnostics["recommendations"]:
        diagnostics["recommendations"].append(
            {
                "priority": "INFO",
                "category": "Status",
                "issue": "No issues detected",
                "solution": "Email configuration appears healthy",
            }
        )

    logger.info(
        f"📧 [Email Diagnostics] Completed for {admin.email}: {len(diagnostics['recommendations'])} recommendations"
    )
    return diagnostics


@router.post("/email/test-send")
async def test_email_send(
    test_email: str,
    admin: UserPublic = Depends(require_admin),
) -> dict[str, Any]:
    """Send a test email to verify email functionality (admin only)."""
    import logging

    from app.domains.email.enums import EmailType
    from app.domains.email.service import EmailService

    logger = logging.getLogger(__name__)
    logger.info(
        f"📧 [Test Email] Admin {admin.email} sending test email to {test_email}"
    )
    try:
        # Send a simple test email
        result = await EmailService.send_email(
            email_type=EmailType.WELCOME,  # Using welcome email as test
            recipient_email=test_email,
            context={"user_name": "Test User", "admin_sender": admin.email},
        )

        if result:
            logger.info(f"✅ [Test Email] Successfully sent to {test_email}")
            return {
                "success": True,
                "message": f"Test email sent successfully to {test_email}",
                "timestamp": datetime.utcnow().isoformat(),
                "sender_admin": admin.email,
            }
        logger.error(f"❌ [Test Email] Failed to send to {test_email}")
        return {
            "success": False,
            "message": f"Failed to send test email to {test_email}",
            "timestamp": datetime.utcnow().isoformat(),
            "sender_admin": admin.email,
        }
    except Exception as e:
        logger.error(f"❌ [Test Email] Exception sending to {test_email}: {e}")
        return {
            "success": False,
            "message": f"Exception sending test email: {e!s}",
            "timestamp": datetime.utcnow().isoformat(),
            "sender_admin": admin.email,
        }


# ==============================================================================
# ROUTER EXPORT
# ==============================================================================

admin_router = APIRouter()
admin_router.include_router(
    router, tags=["Admin/Users", "Admin/Agent-Prompts", "Admin/Debug"]
)
admin_router.include_router(admin_discounts_router)

__all__ = ["admin_router"]
