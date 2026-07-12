#!/usr/bin/env python3
"""
Standalone test for the session endpoint logic
Tests the endpoint without complex app dependencies
"""

import asyncio
import sys

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, status

# Test app
app = FastAPI(title="Session Endpoint Test")
router = APIRouter(prefix="/api/flights", tags=["Flights"])


@router.get("/test-endpoint")
async def test_endpoint() -> dict:
    return {"status": "ok", "message": "Test endpoint works"}


@router.get("/debug-sessions")
async def debug_sessions() -> dict:
    """Debug endpoint to check available sessions."""
    try:
        # Simulate what happens when we can't import the chat service
        try:
            # This would normally be:
            # from app.domains.chat.service import ChatService
            # chat_service = ChatService()
            raise ImportError("No module named 'app.domains.chat.service'")
        except ImportError as import_error:
            return {
                "status": "error",
                "error": f"Service dependencies not available: {import_error!s}",
                "simulation": True,
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/session/{session_id}")
async def get_booking_session_by_id(session_id: str) -> dict:
    """Get booking session data using session ID - TEST VERSION."""
    try:
        # Simulate the dynamic import process
        try:
            # This is what would happen in production
            # This would fail in production if dependencies missing
            raise ImportError("No module named 'app.domains.chat.service'")
        except ImportError as import_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service dependencies not available: {import_error!s}",
            ) from import_error

        # This code would never be reached in our test, but shows what would happen
        # if the imports succeeded but no sessions existed
        handler_count = 0
        total_sessions = 0

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking session {session_id} not found. Active handlers: {handler_count}, Total sessions: {total_sessions}",
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e!s} | Traceback: {traceback.format_exc()}",
        ) from e


app.include_router(router)


async def test_endpoints():
    """Test the endpoints programmatically"""
    print("=== TESTING SESSION ENDPOINT LOGIC ===")

    # Test the session endpoint
    session_id = "039ec25c-7f4f-449a-af26-36ea1415f3d4"

    try:
        result = await get_booking_session_by_id(session_id)
        print(f"✅ Session endpoint returned: {result}")
    except HTTPException as e:
        print(f"❌ Session endpoint raised HTTPException: {e.status_code} - {e.detail}")
    except Exception as e:
        print(f"❌ Session endpoint raised unexpected error: {e}")

    # Test debug endpoint
    try:
        result = await debug_sessions()
        print(f"✅ Debug endpoint returned: {result}")
    except Exception as e:
        print(f"❌ Debug endpoint error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        print("Starting test server on http://localhost:8003")
        print("Test URLs:")
        print("  http://localhost:8003/api/flights/test-endpoint")
        print("  http://localhost:8003/api/flights/debug-sessions")
        print(
            "  http://localhost:8003/api/flights/session/039ec25c-7f4f-449a-af26-36ea1415f3d4"
        )
        uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
    else:
        # Run programmatic test
        asyncio.run(test_endpoints())
