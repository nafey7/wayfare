"""User API endpoints for profile and user management."""

import logging
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.domains.auth import AuthService
from app.domains.auth.dependencies import (
    require_authenticated,
    require_authenticated_with_session,
)
from app.domains.auth.schemas import ChangePasswordRequest, SessionResponse
from app.domains.common import MessageResponse
from app.domains.passenger import (
    PassengerCreate,
    PassengerMasked,
    PassengerResponse,
    PassengerUpdate,
    create_passenger,
    delete_passenger,
    get_passenger_by_id,
    get_passengers_for_user,
    update_passenger,
)
from app.domains.pii_verification import (
    PiiVerificationRequestResponse,
    PiiVerificationVerifyRequest,
    PiiVerificationVerifyResponse,
    request_pii_verification,
    verify_pii_otp,
)
from app.domains.pii_verification.service import verify_pii_view_token
from app.domains.user import UserService
from app.domains.user.schemas import (
    DiscountEligibilityResponse,
    ProfileAggregateResponse,
    UseDiscountRequest,
    UserPhotoResponse,
    UserPublic,
    UserResponse,
    UserUpdateRequest,
)
from app.domains.user_preferences import (
    PreferencesUpdateRequest,
    UserPreferencesResponse,
    get_preferences,
    upsert_preferences,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# USER PROFILE MANAGEMENT
# ==============================================================================


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserPublic = Depends(require_authenticated),
) -> UserResponse:
    """Get current user profile information.

    Note: We fetch fresh data from DB because the JWT token might
    contain stale data if the user recently updated their profile.
    """
    service = UserService(current_user)
    return await service.get_user_profile(current_user.id)


@router.get("/me/profile", response_model=ProfileAggregateResponse)
async def get_me_profile(
    current_user: UserPublic = Depends(require_authenticated),
) -> ProfileAggregateResponse:
    """Get full profile for profile page: user + preferences + passengers.

    Single aggregate call. Passengers sorted with primary (self) first.
    """
    service = UserService(current_user)
    return await service.get_profile(current_user.id)


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_me_preferences(
    request: PreferencesUpdateRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> UserPreferencesResponse:
    """Upsert user preferences (partial update supported)."""
    update_dict = request.model_dump(exclude_unset=True)
    if not update_dict:
        return await get_preferences(current_user.id)
    return await upsert_preferences(current_user.id, update_dict)


@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> UserResponse:
    """Update current user profile."""
    from app.domains.user.exceptions import InvalidPhoneNumberError, ValidationError

    service = UserService(current_user)

    try:
        updated_user = await service.update_user(current_user.id, request)
        return await service.get_user_profile(updated_user.id)
    except InvalidPhoneNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


# ==============================================================================
# PROFILE PHOTO (S3 + imgproxy)
# ==============================================================================


@router.put("/me/photo", response_model=UserPhotoResponse)
async def upload_my_photo(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(require_authenticated),
) -> UserPhotoResponse:
    """Upload (or replace) the current user's profile photo.

    Validates size/MIME/dimensions, strips EXIF, writes to S3, and persists the
    resulting ``photo_key`` plus rendering URLs for sm/md/lg presets.
    """
    from app.domains.user.exceptions import (
        InvalidPhotoError,
        PhotoTooLargeError,
        UnsupportedPhotoTypeError,
    )
    from app.domains.user.photo_service import upload_profile_photo

    # Short-circuit oversize uploads before buffering the body into memory.
    if file.size is not None and file.size > settings.AVATAR_MAX_BYTES:
        logger.info(
            "avatar.upload.rejected.too_large user_id=%s size=%s",
            current_user.id,
            file.size,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo exceeds maximum allowed size of {settings.AVATAR_MAX_BYTES} bytes",
        )

    raw = await file.read()
    try:
        return await upload_profile_photo(
            current_user.id,
            raw,
            declared_mime=file.content_type,
        )
    except PhotoTooLargeError as e:
        logger.info("avatar.upload.rejected.too_large user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        ) from e
    except UnsupportedPhotoTypeError as e:
        logger.info(
            "avatar.upload.rejected.unsupported_type user_id=%s ct=%s",
            current_user.id,
            file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        ) from e
    except InvalidPhotoError as e:
        logger.info(
            "avatar.upload.rejected.invalid user_id=%s reason=%s",
            current_user.id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/me/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_photo(
    current_user: UserPublic = Depends(require_authenticated),
) -> Response:
    """Delete the current user's profile photo. Idempotent — 204 even if absent."""
    from app.domains.user.photo_service import delete_profile_photo

    await delete_profile_photo(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# PROMOTIONAL DISCOUNT
# ==============================================================================


# Promotion constants
DISCOUNT_AMOUNT = 50.0  # $50 discount
MIN_BOOKING_AMOUNT = 600.0  # Minimum booking amount to qualify
PROMOTION_END_DATE = datetime(2026, 4, 1, tzinfo=UTC)  # April 1, 2026


@router.get("/me/discount-eligibility", response_model=DiscountEligibilityResponse)
async def check_discount_eligibility(
    current_user: UserPublic = Depends(require_authenticated),
) -> DiscountEligibilityResponse:
    """Check if user is eligible for the $50 first-booking discount.

    Eligibility requirements:
    - User has not used the discount before (discount_eligible = True)
    - Current date is before April 1, 2026

    Returns:
        DiscountEligibilityResponse with eligibility status and details
    """
    now = datetime.now(UTC)

    # Check if promotion period has ended
    if now >= PROMOTION_END_DATE:
        return DiscountEligibilityResponse(
            eligible=False,
            reason="Promotion period has ended",
        )

    # Check if user has already used the discount
    if not current_user.discount_eligible:
        return DiscountEligibilityResponse(
            eligible=False,
            reason="Discount has already been used",
        )

    return DiscountEligibilityResponse(
        eligible=True,
        reason="Eligible for $50 discount on bookings $600+",
    )


@router.post("/me/use-discount", response_model=MessageResponse)
async def use_discount(
    request: UseDiscountRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Mark the discount as used after successful payment.

    This endpoint should be called after a successful payment to:
    - Validate the booking amount qualifies for discount
    - Set discount_eligible to False to prevent reuse

    Requirements:
    - User must be eligible (discount_eligible = True)
    - Booking amount must be >= $600
    - Current date must be before April 1, 2026

    Args:
        request: Contains booking_amount to validate

    Returns:
        MessageResponse confirming discount was applied

    Raises:
        HTTPException 400: If user is not eligible or booking doesn't qualify
    """
    from app.domains.user import repository as user_repo

    now = datetime.now(UTC)

    # Check if promotion period has ended
    if now >= PROMOTION_END_DATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promotion period has ended",
        )

    # Early check from token state (avoids DB call when clearly ineligible)
    if not current_user.discount_eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount has already been used",
        )

    # Check if booking amount qualifies (before atomic update)
    if request.booking_amount < MIN_BOOKING_AMOUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking amount must be at least ${MIN_BOOKING_AMOUNT} to qualify",
        )

    # Atomically mark discount as used (prevents race: two requests can't both succeed)
    updated_user = await user_repo.use_discount_atomic(current_user.id)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount has already been used or user not found",
        )

    # Audit: booking_amount is frontend-provided (not validated against Stripe)
    logger.info(
        "Discount used by user %s for claimed booking amount $%s (frontend-provided)",
        current_user.id,
        request.booking_amount,
    )

    return MessageResponse(message="$50 discount applied successfully")


# ==============================================================================
# ACCOUNT SECURITY
# ==============================================================================


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Change password for authenticated user."""
    auth_service = AuthService()

    # Verify current password
    user = await auth_service.authenticate_user(
        current_user.email, request.old_password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Change password using auth service
    success = await auth_service.change_user_password(
        user_id=current_user.id, new_password=request.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    return MessageResponse(message="Password changed successfully")


# ==============================================================================
# SESSION MANAGEMENT
# ==============================================================================


@router.get("/me/sessions", response_model=list[SessionResponse])
async def get_my_sessions(
    user_and_session: tuple[UserPublic, str | None] = Depends(
        require_authenticated_with_session
    ),
) -> list[SessionResponse]:
    """Get all active sessions for the current user."""
    current_user, current_session_id = user_and_session

    auth_service = AuthService()
    sessions = await auth_service.get_user_sessions(current_user.id)

    return [
        SessionResponse.from_model(
            session, is_current=(str(session.id) == current_session_id)
        )
        for session in sessions
    ]


@router.delete("/me/sessions/{session_id}", response_model=MessageResponse)
async def revoke_my_session(
    session_id: str,
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Revoke a specific session."""
    auth_service = AuthService()
    success = await auth_service.revoke_user_session(session_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already inactive",
        )

    return MessageResponse(message="Session revoked successfully")


@router.post("/me/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Logout from all devices by invalidating all sessions."""
    auth_service = AuthService()
    success = await auth_service.logout_all_sessions(current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active sessions to logout",
        )

    return MessageResponse(message="Successfully logged out from all devices")


# ==============================================================================
# PII VERIFICATION (Email OTP for viewing passport)
# ==============================================================================


@router.post(
    "/me/pii-verification/request",
    response_model=PiiVerificationRequestResponse,
)
async def pii_verification_request(
    current_user: UserPublic = Depends(require_authenticated),
) -> PiiVerificationRequestResponse:
    """Request PII verification: send 6-digit OTP to user's email, return challenge_id."""
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address on account for verification",
        )
    try:
        return await request_pii_verification(current_user)
    except ValueError as e:
        detail = str(e)
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Too many" in detail
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from e


@router.post(
    "/me/pii-verification/verify",
    response_model=PiiVerificationVerifyResponse,
)
async def pii_verification_verify(
    request: PiiVerificationVerifyRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> PiiVerificationVerifyResponse:
    """Verify OTP; on success return short-lived PII view token."""
    try:
        return await verify_pii_otp(
            current_user,
            request.challenge_id,
            request.code,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# ==============================================================================
# PASSENGER DETAILS STORAGE (issue #418)
# ==============================================================================


@router.post(
    "/me/passengers",
    response_model=PassengerMasked,
    status_code=status.HTTP_201_CREATED,
)
async def store_passenger(
    request: PassengerCreate,
    current_user: UserPublic = Depends(require_authenticated),
) -> PassengerMasked:
    """Store passenger details for the current user.

    Sensitive fields (passport number, expiry, frequent flyer number) are
    encrypted at rest. Response returns masked values for sensitive fields.
    """
    try:
        return await create_passenger(str(current_user.id), request)
    except DuplicateKeyError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another passenger is already set as primary. Please try again.",
        ) from err


@router.get("/me/passengers", response_model=list[PassengerMasked])
async def list_passengers(
    current_user: UserPublic = Depends(require_authenticated),
) -> list[PassengerMasked]:
    """List all saved passengers for the current user.

    Sensitive fields are masked (e.g. passport_number: ****4589).
    """
    return await get_passengers_for_user(str(current_user.id))


@router.get(
    "/me/passengers/{passenger_id}", response_model=PassengerMasked | PassengerResponse
)
async def get_passenger(
    passenger_id: str,
    current_user: UserPublic = Depends(require_authenticated),
    include_sensitive: bool = Query(
        False,
        description="Return full values. Requires X-PII-View-Token when viewing passport in profile.",
    ),
    x_pii_view_token: str | None = Header(
        default=None,
        alias="X-PII-View-Token",
        description="Short-lived token from pii-verification/verify (required when include_sensitive=true)",
    ),
) -> PassengerMasked | PassengerResponse:
    """Get a passenger by ID. Owner only. Use include_sensitive=true with X-PII-View-Token for profile passport view."""
    if include_sensitive:
        if not x_pii_view_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification required. Request an email code from the profile page.",
            )
        user_id_from_token = verify_pii_view_token(x_pii_view_token)
        if not user_id_from_token or user_id_from_token != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired verification. Please verify again.",
            )
    result = await get_passenger_by_id(
        passenger_id,
        str(current_user.id),
        include_sensitive=include_sensitive,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passenger not found",
        )
    return result


@router.put("/me/passengers/{passenger_id}", response_model=PassengerMasked)
async def update_passenger_endpoint(
    passenger_id: str,
    request: PassengerUpdate,
    current_user: UserPublic = Depends(require_authenticated),
) -> PassengerMasked:
    """Update a stored passenger. Owner only."""
    try:
        result = await update_passenger(
            passenger_id,
            str(current_user.id),
            request,
        )
    except DuplicateKeyError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another passenger is already set as primary. Please try again.",
        ) from err
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passenger not found",
        )
    return result


@router.delete("/me/passengers/{passenger_id}", response_model=MessageResponse)
async def remove_passenger(
    passenger_id: str,
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Delete a passenger. Permanently removes data (GDPR right to deletion)."""
    success = await delete_passenger(passenger_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passenger not found",
        )
    return MessageResponse(message="Passenger deleted")


# ==============================================================================
# ACCOUNT DELETION
# ==============================================================================


@router.delete("/me", response_model=MessageResponse)
async def delete_me(
    current_user: UserPublic = Depends(require_authenticated),
) -> MessageResponse:
    """Delete current user account.

    This is a soft delete that marks the account as deleted
    but preserves the data for compliance/recovery.
    """
    service = UserService(current_user)
    success = await service.delete_user(current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )

    return MessageResponse(message="Account successfully deleted")
