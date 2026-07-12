import asyncio
import logging
import os
import tracemalloc
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any, cast

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.bookings import router as bookings_router
from app.api.chat import router as chat_router
from app.api.imgproxy import router as imgproxy_router
from app.api.payments import router as payments_router
from app.api.places import close_places_client
from app.api.public_places import close_public_places_client
from app.api.revolut_payments import router as revolut_payments_router
from app.api.router import api_router
from app.api.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.logging import (
    get_agents_logger,
    get_backend_logger,
    scrub_sentry_event,
    setup_logging,
)
from app.database.connection import (
    FlightLogicHealthChecker,
    GeminiHealthChecker,
    GoogleAPIHealthChecker,
    SendGridHealthChecker,
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
    mongodb_connect_test_scram,
)
from app.domains.auth.exceptions import InvalidTokenError
from app.middleware import CacheControlMiddleware, LoggingMiddleware

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Sentry for error tracking and APM
if settings.SENTRY_DSN:
    from sentry_sdk.integrations.langchain import LangchainIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    # Capture ERROR logs as Sentry events (in addition to exceptions)
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture INFO+ as breadcrumbs
        event_level=logging.ERROR,  # Send ERROR+ as Sentry events
    )

    # LangChain integration for AI observability
    sentry_langchain = LangchainIntegration(
        include_prompts=True,  # Capture AI prompts and responses
    )

    def _sentry_before_send(
        event: dict[str, Any], _hint: dict[str, Any]
    ) -> dict[str, Any]:
        scrub_sentry_event(event)
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=True,  # Required for LangChain AI data capture
        integrations=[sentry_logging, sentry_langchain],
        before_send=_sentry_before_send,
    )
    logger.info(
        f"Sentry initialized for environment: {settings.ENVIRONMENT} "
        f"(traces: {settings.SENTRY_TRACES_SAMPLE_RATE}, "
        f"profiles: {settings.SENTRY_PROFILES_SAMPLE_RATE})"
    )
else:
    logger.debug("Sentry DSN not configured - error tracking disabled")

# Enable tracemalloc at startup
tracemalloc.start()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}")
    logger.debug(f"Debug mode: {settings.DEBUG}")
    logger.debug(f"CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"Flightlogic api url: {settings.FLIGHTLOGIC_API_URL}")

    # Connect to MongoDB (optional - don't fail if not available)
    # Clear old PDFs on startup (development/test only) - do this BEFORE MongoDB connection
    if settings.PDF_CLEAR_ON_STARTUP:
        try:
            from pathlib import Path

            pdf_dir = Path(settings.PDF_OUTPUT_DIR)
            if pdf_dir.exists():
                pdf_files = list(pdf_dir.glob("*.pdf"))
                cleared_count = 0
                skipped_count = 0

                for pdf_file in pdf_files:
                    try:
                        pdf_file.unlink()
                        cleared_count += 1
                    except PermissionError:
                        # File is open in another process (PDF viewer) - skip it
                        skipped_count += 1
                    except Exception as e:
                        logger.debug(f"Could not delete {pdf_file.name}: {e}")
                        skipped_count += 1

                if cleared_count > 0:
                    logger.info(f"Cleared {cleared_count} PDF file(s) from {pdf_dir}")
                if skipped_count > 0:
                    logger.debug(
                        f"Skipped {skipped_count} PDF file(s) (in use by another process)"
                    )
            else:
                pdf_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"PDF directory created: {pdf_dir}")
        except Exception as e:
            logger.warning(f"Failed to access PDF directory: {e}")

    # Load feature flags from SSM at startup (before first request)
    try:
        from app.core.feature_flags import _load_flags

        _load_flags()
        logger.info("Feature flags loaded from SSM")
    except Exception as e:
        logger.warning(f"Feature flags SSM preload failed: {e}")

    try:
        mongodb_connect_test_scram()
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")

    try:
        await connect_to_mongodb()

        # Initialize default agent prompts
        try:
            from app.domains.agent_prompt import agent_prompt_service

            await agent_prompt_service.initialize_default_prompts()
            logger.info("Agent prompts initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize agent prompts: {e}")

        # Seed test users for development and testing
        try:
            from app.database.seed import seed_test_users

            await seed_test_users()
            logger.info("Test users seeded successfully")
        except Exception as e:
            logger.warning(f"Failed to seed test users: {e}")

        try:
            from app.domains.saved_itinerary.repository import (
                ensure_saved_itinerary_indexes,
            )

            await ensure_saved_itinerary_indexes()
            logger.info("Saved itinerary indexes ensured")
        except Exception as e:
            logger.warning(f"Failed to ensure saved itinerary indexes: {e}")

    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")

    mongodb_ready = get_connection().is_connected

    # Connect to Gemini (optional - don't fail if not available)
    try:
        checker = GeminiHealthChecker()
        ping_msg = await checker.ping()
        logger.info(f"Gemini connection verified - reply: {ping_msg!r}")
    except Exception as exc:
        logger.error(f"Gemini connection test failed: {exc}")

    # Connect to Google API (optional - don't fail if not available)
    try:
        google_checker = GoogleAPIHealthChecker()
        ping_msg = await google_checker.ping()
        logger.info(f"Google API connection verified - reply: {ping_msg!r}")
    except Exception as exc:
        logger.error(f"Google API connection test failed: {exc}")

    # Connect to FlightLogic API (optional - don't fail if not available)
    try:
        flightlogic_checker = FlightLogicHealthChecker()
        ping_msg = await flightlogic_checker.ping()
        logger.info(f"FlightLogic API connection verified - {ping_msg}")
    except Exception as exc:
        logger.error(f"FlightLogic API connection test failed: {exc}")

    # Connect to SendGrid (optional - don't fail if not available)
    try:
        sendgrid_checker = SendGridHealthChecker()
        ping_msg = await sendgrid_checker.ping()
        logger.info(f"SendGrid connection verified - reply: {ping_msg!r}")
    except Exception as exc:
        logger.error(f"SendGrid connection test failed: {exc}")

    # Print clickable URLs for easy access
    # Use the configured HOST from settings
    logger.info("For development use:")
    base_url = f"http://{settings.HOST}:{settings.PORT}"
    logger.info("=" * 60)
    logger.info(">>> Server is running! Click the links below:")
    logger.info("=" * 60)

    logger.info("For development use:")
    logger.info(f"  API:          {base_url}")
    logger.info(f"  Health:       {base_url}/health")
    logger.info(f"  Swagger Docs: {base_url}/api/docs")
    logger.info(f"  ReDoc:        {base_url}/api/redoc")
    if settings.DEBUG:
        logger.info(f"  API Tester:    {base_url}/dev/api-tester.html")
        logger.info(f"  Flight Booker: {base_url}/dev/flight-booker/index.html")
        logger.info(f"  Hotel Booker:  {base_url}/dev/hotel-booker/index.html")
        logger.info(f"  Transit Booker: {base_url}/dev/transit-booker/index.html")
    logger.info("For production use:")
    logger.info(f"  API:          {settings.FRONTEND_URL}")
    logger.info(f"  Health:       {settings.FRONTEND_URL}/health")
    logger.info(f"  Swagger Docs: {settings.FRONTEND_URL}/api/docs")
    logger.info(f"  ReDoc:        {settings.FRONTEND_URL}/api/redoc")
    if settings.DEBUG:
        logger.info(f"  API Tester:    {settings.FRONTEND_URL}/dev/api-tester.html")
        logger.info(
            f"  Flight Booker: {settings.FRONTEND_URL}/dev/flight-booker/index.html"
        )
        logger.info(
            f"  Hotel Booker:  {settings.FRONTEND_URL}/dev/hotel-booker/index.html"
        )
        logger.info(
            f"  Transit Booker: {settings.FRONTEND_URL}/dev/transit-booker/index.html"
        )

    logger.info("=" * 60)

    sweeper_stop: asyncio.Event | None = None
    sweeper_task: asyncio.Task[None] | None = None
    if mongodb_ready:
        stop_event = asyncio.Event()
        sweeper_stop = stop_event

        async def voucher_reservation_sweeper() -> None:
            from app.domains.discount.service import discount_service

            while True:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=300.0)
                    return
                except TimeoutError:
                    try:
                        modified = await discount_service.expire_stale_reservations()
                        if modified:
                            logger.info(
                                "Voucher sweeper released %s stale reservations",
                                modified,
                            )
                    except Exception as exc:
                        logger.warning("Voucher reservation sweeper error: %s", exc)

        sweeper_task = asyncio.create_task(voucher_reservation_sweeper())

    yield
    # Shutdown
    if sweeper_stop is not None and sweeper_task is not None:
        sweeper_stop.set()
        sweeper_task.cancel()
        with suppress(asyncio.CancelledError):
            await sweeper_task

    logger.info(f"Shutting down {settings.APP_NAME}")
    try:
        await close_places_client()
    except Exception as e:
        logger.debug(f"Places client shutdown error (ignoring): {e}")
    try:
        await close_public_places_client()
    except Exception as e:
        logger.debug(f"Public Places client shutdown error (ignoring): {e}")
    try:
        await disconnect_from_mongodb()
    except Exception as e:
        logger.debug(f"MongoDB disconnect error (ignoring): {e}")

    # Clean up LangGraph graph resources (MongoDB clients, singletons)
    try:
        from app.ai.graph.supervisor_v2 import cleanup_supervisor_v2

        cleanup_supervisor_v2()
    except Exception as e:
        logger.debug(f"Supervisor V2 cleanup error (ignoring): {e}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS configuration - Allow all origins in development for testing
# Note: file:// protocol sends "null" as origin
cors_origins = ["*", "null"] if settings.DEBUG else settings.CORS_ORIGINS
app.add_middleware(
    cast("Any", CORSMiddleware),  # Type cast to bypass middleware factory typing
    allow_origins=cors_origins,  # Allow file:// protocol in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers to the client
)

# Add logging middleware for automatic request/response logging
app.add_middleware(LoggingMiddleware)

# Add cache control middleware for proper CDN caching
app.add_middleware(CacheControlMiddleware)


# Mount static files for development tools
# Allow in development OR when explicitly enabled for production admin tools

dev_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dev_ui")
should_mount_dev_ui = (
    settings.DEBUG  # Always in debug mode
    or settings.ENVIRONMENT in ["development", "staging"]  # Always in dev/staging
    or os.getenv("ENABLE_DEV_TOOLS", "false").lower()
    in ["true", "1", "yes"]  # Explicit override
)

if should_mount_dev_ui and os.path.exists(dev_ui_path):
    logger.info(f"Mounting development UI tools from {dev_ui_path}")
    app.mount("/dev", StaticFiles(directory=dev_ui_path, html=True), name="dev-ui")
    logger.info(
        "Development tools: /dev/api-tester.html, /dev/flight-booker/, /dev/hotel-booker/"
    )
elif os.path.exists(dev_ui_path):
    logger.info(
        f"Dev UI files exist at {dev_ui_path} but not mounting (DEBUG={settings.DEBUG}, ENV={settings.ENVIRONMENT})"
    )
    logger.info("To enable dev tools in production, set ENABLE_DEV_TOOLS=true")
else:
    logger.warning(f"Dev UI directory not found at {dev_ui_path}")

# Mount React frontend static files
react_static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
react_build_path = os.path.join(
    react_static_path, "static"
)  # React builds to static/static/

# Mount React's static assets (CSS, JS, images)
if os.path.exists(react_build_path):
    logger.info(f"Mounting React static assets from {react_build_path}")
    app.mount("/static", StaticFiles(directory=react_build_path), name="react-static")
    logger.info("React static assets mounted at /static/")
elif settings.DEBUG:
    logger.debug(
        f"React static assets not found at {react_build_path} (normal in development)"
    )
else:
    logger.warning(f"React static assets not found at {react_build_path}")

# Mount Vite frontend assets (frontend-v2 builds to static/assets/)
vite_assets_path = os.path.join(react_static_path, "assets")
if os.path.exists(vite_assets_path):
    logger.info(f"Mounting Vite assets from {vite_assets_path}")
    app.mount("/assets", StaticFiles(directory=vite_assets_path), name="vite-assets")
    logger.info("Vite assets mounted at /assets/")

# Add global exception handlers


@app.exception_handler(InvalidTokenError)
async def invalid_token_exception_handler(request: Request, exc: InvalidTokenError):
    """Handle InvalidTokenError globally"""
    logger.warning(f"InvalidTokenError caught globally for {request.url.path}: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid or expired token"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors (422 responses) with detailed logging."""
    from app.core.logging import (
        get_backend_logger,
        get_flights_logger,
        get_hotels_logger,
    )

    # Select appropriate logger based on request path (same logic as middleware)
    path = str(request.url.path)
    if path.startswith("/api/flights/"):
        logger = get_flights_logger()
    elif path.startswith("/api/hotels/"):
        logger = get_hotels_logger()
    else:
        logger = get_backend_logger()

    # Extract validation error details
    error_details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{field_path}: {error['msg']}")

    error_summary = "; ".join(error_details)

    # Log the validation error with details
    logger.warning(
        f"Validation error for {request.method} {request.url.path}: {error_summary}",
        extra={
            "validation_errors": exc.errors(),
            "request_method": request.method,
            "request_path": str(request.url.path),
            "status_code": 422,
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": error["loc"],
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ]
        },
    )


# Include API router AFTER static mount
app.include_router(api_router, prefix="/api")

# Add payments router (under /api prefix)
app.include_router(payments_router, prefix="/api")

# Add Revolut payments router (under /api prefix)
app.include_router(revolut_payments_router, prefix="/api")

# Add bookings router (under /api prefix)
app.include_router(bookings_router, prefix="/api")

# Add webhooks router (direct path, no /api prefix for Stripe compatibility)
app.include_router(webhooks_router)

# Add legacy routes for frontend compatibility (without /api prefix)
# This allows frontend to call /auth/register instead of /api/auth/register

app.include_router(auth_router, prefix="/auth", tags=["Authentication (Legacy)"])
# Chat router already has prefix="/chat", so include as-is
app.include_router(chat_router)

# imgproxy reverse proxy for local development
# In production, ALB routes /imgproxy/* directly to the imgproxy service
app.include_router(imgproxy_router, prefix="/imgproxy", tags=["Image Proxy"])


# Note: LoggingMiddleware handles all request/response logging now (added above)


@app.middleware("http")
async def serve_react_fallback(request: Request, call_next):
    response = await call_next(request)

    # If we get a 404 and it's not an API route, serve React
    if response.status_code == 404 and not request.url.path.startswith(
        ("/api/", "/docs", "/redoc", "/openapi.json", "/health", "/dev/")
    ):
        react_index = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "static", "index.html"
        )
        if os.path.exists(react_index):
            return FileResponse(react_index)

    return response


@app.get("/")
async def root():
    """Serve React app for the root route"""
    react_index = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "index.html"
    )
    if os.path.exists(react_index):
        return FileResponse(react_index)
    # Fallback - only show this if React files are missing
    return {
        "name": "Voya API",
        "version": "1.0.0",
        "status": "online",
        "error": "React app not found",
    }


# For agent-related operations
agents_logger = get_agents_logger()


@app.post("/agents/create")
async def create_agent(agent_data: dict):
    agents_logger.info(f"Creating new agent: {agent_data.get('name')}")
    try:
        # Agent creation logic here
        agents_logger.info(f"Agent created successfully: {agent_data.get('name')}")
        return {"status": "success"}
    except Exception as e:
        agents_logger.error(f"Failed to create agent: {e!s}")
        raise


# For general backend operations
backend_logger = get_backend_logger()


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for monitoring.

    Returns:
        dict: Service health status and metadata
    """

    # Check database connection
    db_status = "disconnected"
    try:
        db = get_connection().get_database()
        await db.command("ping")
        db_status = "connected"
    except (RuntimeError, ConnectionError, TimeoutError):
        # Expected exceptions when database is not connected
        pass

    return {
        "status": "OK",
        "service": settings.APP_NAME,
        "version": settings.GIT_VERSION,
        "commit": settings.GIT_COMMIT_HASH,
        "database": db_status,
    }


@app.exception_handler(404)
async def not_found_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Handle 404 Not Found errors.

    Args:
        _request: The incoming request (unused)
        _exc: The exception that was raised (unused)

    Returns:
        JSONResponse: 404 error response
    """
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Handle 500 Internal Server errors.

    Args:
        _request: The incoming request (unused)
        _exc: The exception that was raised (unused)

    Returns:
        JSONResponse: 500 error response
    """
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
