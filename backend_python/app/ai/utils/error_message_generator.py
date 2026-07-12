"""LLM-powered error message generator for FlightLogic API errors.

This module provides functionality to generate empathetic, human-readable error
messages from technical FlightLogic API errors using the LLM service.

Part of Issue #276: Improve FlightLogic Error Handling in Booker UI and AI Chat
"""

import logging
from typing import Any

from integrations.llm import get_llm_service

logger = logging.getLogger(__name__)


def detect_error_type(exception: Exception) -> tuple[str, str, str | None, int | None]:
    """Detect error type and extract details from exception.

    This function centralizes error type detection logic that was duplicated
    across multiple handlers. It handles both flight and hotel domain exceptions.

    Args:
        exception: The exception to analyze

    Returns:
        Tuple of (error_type, error_message, error_code, status_code)
        - error_type: String like "FLIGHT_API_ERROR", "HOTEL_SEARCH_ERROR", etc.
        - error_message: Human-readable error message
        - error_code: Optional error code from exception
        - status_code: Optional HTTP status code (only for FlightApiError)

    Example:
        >>> try:
        ...     raise FlightSearchError(reason="No flights found")
        ... except Exception as e:
        ...     error_type, msg, code, status = detect_error_type(e)
        ...     print(error_type)  # "FLIGHT_SEARCH_ERROR"
    """
    # Import here to avoid circular dependencies
    from app.domains.flight.exceptions import (
        FlightApiError,
        FlightBookingError,
        FlightBookingSupplierSyncError,
        FlightSearchError,
        FlightValidationError,
    )
    from app.domains.hotel.exceptions import (
        HotelBookingError,
        HotelRateError,
        HotelSearchError,
        HotelSessionError,
        HotelValidationError,
    )

    error_type = "UNKNOWN_ERROR"
    error_message = str(exception)
    error_code = None
    status_code = None

    # Flight domain exceptions
    if isinstance(exception, FlightApiError):
        error_type = "FLIGHT_API_ERROR"
        error_message = exception.reason or str(exception)
        status_code = exception.status_code
        error_code = exception.code
    elif isinstance(exception, FlightSearchError):
        error_type = "FLIGHT_SEARCH_ERROR"
        error_message = exception.reason or str(exception)
        error_code = exception.code
    elif isinstance(exception, FlightBookingSupplierSyncError):
        error_type = "FLIGHT_BOOKING_SUPPLIER_SYNC_ERROR"
        error_message = exception.reason or str(exception)
        error_code = exception.code
        status_code = 409
    elif isinstance(exception, FlightBookingError):
        error_type = "FLIGHT_BOOKING_ERROR"
        error_message = exception.reason or str(exception)
        error_code = exception.code
    elif isinstance(exception, FlightValidationError):
        error_type = "FLIGHT_VALIDATION_ERROR"
        error_message = exception.reason or str(exception)
        error_code = exception.code
    # Hotel domain exceptions
    elif isinstance(exception, HotelSearchError):
        error_type = "HOTEL_SEARCH_ERROR"
        error_message = exception.message
        error_code = exception.code
    elif isinstance(exception, HotelBookingError):
        error_type = "HOTEL_BOOKING_ERROR"
        error_message = exception.message
        error_code = exception.code
    elif isinstance(exception, HotelValidationError):
        error_type = "HOTEL_VALIDATION_ERROR"
        error_message = exception.message
        error_code = exception.code
    elif isinstance(exception, HotelSessionError):
        error_type = "HOTEL_SESSION_ERROR"
        error_message = exception.message
        error_code = exception.code
    elif isinstance(exception, HotelRateError):
        error_type = "HOTEL_RATE_ERROR"
        error_message = exception.message
        error_code = exception.code
    elif hasattr(exception, "__class__") and "Hotel" in exception.__class__.__name__:
        # Catch any other hotel domain errors
        error_type = "HOTEL_ERROR"
        error_message = str(exception)
        error_code = getattr(exception, "code", None)

    return error_type, error_message, error_code, status_code


def _categorize_error_for_llm(error_code: str | None, error_message: str) -> str:
    """Categorize error to help LLM provide appropriate response.

    Returns a category description that helps the LLM understand the error context.
    """
    if not error_code and not error_message:
        return "unknown error"

    error_upper = (error_code or "").upper() + " " + error_message.upper()

    # Authentication/configuration errors (system issues, user can't fix)
    if any(
        keyword in error_upper
        for keyword in [
            "INVALID USER",
            "USER_ID",
            "USER_PASSWORD",
            "AUTH",
            "CREDENTIAL",
            "LOGIN",
        ]
    ):
        return "authentication/configuration error (system issue that needs admin attention)"

    # Validation errors (user input issues)
    if any(
        keyword in error_upper
        for keyword in ["VALIDATION", "INVALID", "REQUIRED", "MISSING", "FORMAT"]
    ):
        return "validation error (check user input)"

    # No results (not really an error, just no matches)
    if any(
        keyword in error_upper
        for keyword in ["NO RESULT", "NO FLIGHTS", "NO HOTELS", "NOT FOUND"]
    ):
        return "no results found (search criteria may be too restrictive)"

    # Session/timeout errors
    if any(keyword in error_upper for keyword in ["SESSION", "TIMEOUT", "EXPIRED"]):
        return "session/timeout error (user should retry)"

    # Rate limiting
    if any(keyword in error_upper for keyword in ["RATE LIMIT", "QUOTA", "TOO MANY"]):
        return "rate limit error (too many requests, wait and retry)"

    return "general error"


async def generate_error_message(
    error_type: str,
    error_message: str,
    operation: str,
    error_code: str | None = None,
    status_code: int | None = None,
    additional_context: dict[str, Any] | None = None,
) -> str:
    """Generate an empathetic, human-readable error message using LLM.

    This function takes raw FlightLogic API error data and uses the LLM to
    generate a user-friendly, empathetic response that guides users on next steps.

    Args:
        error_type: Type of error (e.g., "FLIGHT_API_ERROR", "HOTEL_SEARCH_ERROR")
        error_message: Raw error message from FlightLogic API
        operation: Affected operation (e.g., "search", "booking", "validation")
        error_code: Optional error code from FlightLogic
        status_code: Optional HTTP status code
        additional_context: Optional additional context dict

    Returns:
        Human-readable error message generated by LLM

    Example:
        >>> message = await generate_error_message(
        ...     error_type="FLIGHT_SEARCH_ERROR",
        ...     error_message="No flights found for the specified route",
        ...     operation="search"
        ... )
        >>> print(message)
        "I couldn't find any flights for that route. Would you like to try
        different dates or consider connecting flights?"
    """
    # Build structured error context for LLM
    error_context = {
        "error_type": error_type,
        "error_message": error_message,
        "operation": operation,
    }

    if error_code:
        error_context["error_code"] = error_code
    if status_code:
        error_context["status_code"] = status_code
    if additional_context:
        error_context.update(additional_context)

    # Categorize error to provide better context
    error_category = _categorize_error_for_llm(error_code, error_message)

    # Create prompt for LLM
    prompt = f"""You are a helpful travel assistant. A FlightLogic API error occurred while {operation}ing.

Error Details:
- Error Type: {error_type}
- Error Message: {error_message}
- Error Category: {error_category}
{f"- Error Code: {error_code}" if error_code else ""}
{f"- HTTP Status: {status_code}" if status_code else ""}
{f"- Additional Context: {additional_context}" if additional_context else ""}

Generate a brief, empathetic, and helpful error message (2-3 sentences max) that:
1. Acknowledges the issue in a friendly way
2. Translates the error message into user-friendly language that explains what went wrong
   - Example: "Invalid user_id/user_password" → "We're experiencing a temporary issue with our flight search service. Our team has been notified."
   - Example: "No flights found" → "I couldn't find any flights matching your criteria. Would you like to try different dates or nearby airports?"
   - Example: "Session expired" → "Your search session has timed out. Let me start a fresh search for you."
3. Suggests actionable next steps based on the error category:
   - Authentication/configuration errors: Mention it's a system issue and support has been notified
   - Validation errors: Ask user to check their input
   - No results: Suggest modifying search criteria
   - Session/timeout: Suggest retrying
   - Rate limiting: Suggest waiting a moment before retrying

IMPORTANT:
- Translate the technical error message into plain, user-friendly language
- Explain what the error means in terms the user can understand
- Don't just say "an error occurred" - explain what the error means based on the error message
- Don't expose technical details like error codes, API names, or internal system names
- Be specific about what went wrong when possible
- Use the error category to guide your response tone and suggestions

Response (just the message, no quotes or formatting):"""

    try:
        llm_service = get_llm_service()
        response = await llm_service.generate_content(prompt)

        generated_message = response.text.strip()

        # Remove quotes if LLM wrapped the response
        if (generated_message.startswith('"') and generated_message.endswith('"')) or (
            generated_message.startswith("'") and generated_message.endswith("'")
        ):
            generated_message = generated_message[1:-1]

        logger.debug(
            f"Generated LLM error message for {operation} operation: "
            f"{generated_message[:100]}..."
        )

        return generated_message

    except Exception as e:
        logger.error(f"Failed to generate LLM error message: {e}", exc_info=True)

        # Fallback to a generic but still helpful message
        operation_verb = (
            "searching"
            if operation == "search"
            else "booking"
            if operation == "booking"
            else "processing"
        )
        return (
            f"I encountered an issue while {operation_verb}. "
            f"This might be temporary - would you like to try again? "
            f"If the problem persists, please try modifying your search criteria or contact support."
        )
