"""MongoDB connection management and lifecycle.

This module handles database connection and lifecycle management.
Collections and indexes should be created outside the application (migrations, scripts, etc).
"""

import asyncio
import json
import logging

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from app.core.config import settings
from integrations.llm import get_llm_service

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None
        self._is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        """True after a successful :meth:`connect` (pinged cluster)."""
        return self._is_connected

    async def connect(self) -> None:
        """Initialize MongoDB connection with connection pooling."""
        if self._is_connected:
            logger.debug("Already connected to MongoDB")
            return

        try:
            # Validate MONGODB_URI format before attempting connection
            uri_validation_error = self._validate_mongodb_uri(settings.MONGODB_URI)
            if uri_validation_error:
                logger.error(f"MONGODB_URI validation failed: {uri_validation_error}")
                self._is_connected = False
                return

            # Log sanitized URI (hide credentials)
            sanitized_uri = self._sanitize_uri_for_logging(settings.MONGODB_URI)
            logger.info(f"Connecting to MongoDB: {sanitized_uri}")

            # Accept both local MongoDB (mongodb://) and Atlas (mongodb+srv://) URIs
            if not (
                settings.MONGODB_URI.startswith("mongodb://")
                or settings.MONGODB_URI.startswith("mongodb+srv://")
            ):
                logger.error(
                    "Invalid MONGODB_URI. Expected a valid MongoDB URI (mongodb:// or mongodb+srv://)."
                )
                self._is_connected = False
                return

            # Create client with connection pooling
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                server_api=ServerApi("1"),
                maxPoolSize=settings.DATABASE_MAX_POOL_SIZE,
                minPoolSize=settings.DATABASE_MIN_POOL_SIZE,
                maxIdleTimeMS=60000,  # 60 seconds idle timeout
                serverSelectionTimeoutMS=10000,  # Increased timeout
                connectTimeoutMS=10000,  # Connection timeout
                socketTimeoutMS=20000,  # Socket timeout
            )

            logger.info("MongoDB client created, testing connection...")

            # Verify connection with timeout
            ping_result = await asyncio.wait_for(
                self.client.admin.command("ping"), timeout=15.0
            )
            logger.info(f"MongoDB ping successful: {ping_result}")

            # Set the database
            self.database = self.client[settings.DATABASE_NAME]
            self._is_connected = True

            logger.info(
                f"Connected to MongoDB database: {settings.DATABASE_NAME} "
                f"(pool: {settings.DATABASE_MIN_POOL_SIZE}-{settings.DATABASE_MAX_POOL_SIZE})"
            )

        except TimeoutError as e:
            logger.error("MongoDB connection timed out")
            self._is_connected = False
            raise ConnectionError("MongoDB connection timeout") from e

        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            self._is_connected = False
            raise

        except Exception as e:
            # Log more detailed error information for authentication failures
            error_type = type(e).__name__
            error_msg = str(e)

            if "Authentication failed" in error_msg:
                logger.error(
                    "MongoDB authentication failed - check credentials in MONGODB_URI"
                )
                logger.error(
                    f"URI format: {settings.MONGODB_URI.split('@')[0] if '@' in settings.MONGODB_URI else 'No credentials found'}@[HIDDEN]"
                )
            elif "ServerSelectionTimeoutError" in error_type:
                logger.error(
                    f"MongoDB server unreachable - check network and URI: {error_msg}"
                )
            else:
                logger.error(f"Failed to connect to MongoDB: {error_type}: {error_msg}")

            self._is_connected = False
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if not self._is_connected or self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get collection by name."""
        if not self._is_connected or self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database[name]

    async def check_connection(self) -> bool:
        """Check if database connection is healthy."""
        if not self._is_connected or self.client is None:
            return False

        try:
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def _validate_mongodb_uri(self, uri: str) -> str | None:
        """Validate MongoDB URI format and return error message if invalid."""
        if not uri:
            return "MongoDB URI is empty"

        if not uri.startswith(("mongodb://", "mongodb+srv://")):
            return "URI must start with mongodb:// or mongodb+srv://"

        return None

    def _sanitize_uri_for_logging(self, uri: str) -> str:
        """Remove credentials from URI for safe logging."""
        if "@" in uri:
            # Split at @ and hide credentials
            parts = uri.split("@")
            if len(parts) >= 2:
                scheme_and_creds = parts[0]
                if "://" in scheme_and_creds:
                    scheme = scheme_and_creds.split("://")[0]
                    return f"{scheme}://[CREDENTIALS_HIDDEN]@{parts[1]}"
        return uri


def mongodb_connect_test() -> None:
    """Test MongoDB connection using MongoClient.

    Returns:
    None
    """
    try:
        uri = settings.MONGODB_URI
        client: MongoClient = MongoClient(uri, server_api=ServerApi("1"))
        client.admin.command("ping")
        logger.info("MongoDB connection test successful")
    except Exception as e:
        logger.warning(
            f"MongoDB connection test failed for mongodb_uri {settings.MONGODB_URI}: {e}"
        )


def mongodb_connect_test_scram() -> bool:
    """Test MongoDB connection using synchronous MongoClient.

    Returns:
        bool: True if connection successful, False otherwise
    """
    MONGODB_URI = settings.MONGODB_URI
    if MONGODB_URI == "mongodb://localhost:27017":
        logger.info("ERROR: MONGODB_URI environment variable not set")
        return False

    # Create a new client and connect to the server
    client: MongoClient = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
    # Send a ping to confirm a successful connection
    try:
        client.admin.command("ping")
        logger.info("MongoDB SCRAM test: Connection successful")
        return True
    except Exception as e:
        logger.error(f"MongoDB SCRAM test failed: {type(e).__name__}: {e}")
        return False
    finally:
        if client:
            client.close()


# Global connection instance
_db_connection = DatabaseConnection()


# Lifecycle functions for FastAPI startup/shutdown
async def connect_to_mongodb() -> None:
    """Connect to MongoDB on application startup.

    Usage in main.py:
        @app.on_event("startup")
        async def startup():
            await connect_to_mongodb()
    """
    await _db_connection.connect()


async def disconnect_from_mongodb() -> None:
    """Disconnect from MongoDB on application shutdown.

    Usage in main.py:
        @app.on_event("shutdown")
        async def shutdown():
            await disconnect_from_mongodb()
    """
    await _db_connection.disconnect()


async def check_database_health() -> bool:
    """Check if database is healthy.

    Usage in health check endpoint:
        @router.get("/health")
        async def health_check():
            db_healthy = await check_database_health()
            return {"database": "healthy" if db_healthy else "unhealthy"}
    """
    return await _db_connection.check_connection()


def get_connection() -> DatabaseConnection:
    """Get the global database connection instance.

    For internal use when direct access to connection is needed.
    """
    return _db_connection


class GeminiHealthChecker:
    """
    Small utility that validates we can talk to the Gemini API.
    Uses the LLMService abstraction for vendor-agnostic health checks.
    """

    def __init__(self) -> None:
        """Initialize with the LLM service singleton."""
        self._llm = get_llm_service()

    async def ping(self) -> str:
        """
        Tests Gemini API connectivity using the LLM service health check.

        Returns:
            Success message if healthy.

        Raises:
            RuntimeError – if the call fails for any reason (network,
                           authentication, quota, etc.).
        """
        try:
            if await self._llm.health_check():
                return "Gemini API healthy"
            raise RuntimeError("Gemini health check returned unhealthy")
        except Exception as exc:
            # Wrap the original exception with a clearer message.
            raise RuntimeError(f"Gemini health-check failed: {exc}") from exc


class GoogleAPIHealthChecker:
    """
    Small utility that validates we can talk to Google APIs.
    Uses the Cloud Resource Manager API to list projects as a minimal test.
    """

    def __init__(self) -> None:
        # Check for API key or service account credentials
        self.api_key = settings.GOOGLE_API_KEY
        self.service_account_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON

        if not self.api_key and not self.service_account_json:
            raise RuntimeError(
                "No Google API credentials supplied - set GOOGLE_API_KEY "
                "or GOOGLE_SERVICE_ACCOUNT_JSON in your environment."
            )

    async def ping(self) -> str:
        """
        Makes a minimal API call to verify Google API connectivity.
        Uses Cloud Resource Manager API to test authentication.

        Raises:
            RuntimeError – if the call fails for any reason (network,
                           authentication, quota, etc.).
        """
        try:
            if self.api_key:
                # Using API key - test with a simple API call
                service = build("cloudresourcemanager", "v1", developerKey=self.api_key)
                # Just test the connection without actually listing projects
                request = service.projects().list(pageSize=1)
                _response = request.execute()  # Execute to verify API key works
                return "API key authenticated"

            # Using service account credentials
            sa_json = self.service_account_json
            if not sa_json:
                raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")
            credentials_info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"],
            )

            service = build("cloudresourcemanager", "v1", credentials=credentials)
            request = service.projects().list(pageSize=1)
            _response = request.execute()  # Execute to verify authentication works
            return "Service account authenticated"
        except Exception as exc:
            raise RuntimeError(f"Google API health-check failed: {exc}") from exc


class FlightLogicHealthChecker:
    """
    Health checker for FlightLogic API credentials and connectivity.
    Tests authentication by attempting a minimal API call.
    """

    def __init__(self) -> None:
        """Initialize with FlightLogic credentials from settings."""
        if not settings.FLIGHTLOGIC_USER_ID or not settings.FLIGHTLOGIC_PASSWORD:
            raise RuntimeError(
                "FlightLogic credentials not configured - check FLIGHTLOGIC_USER_ID and FLIGHTLOGIC_PASSWORD"
            )
        self.user_id = settings.FLIGHTLOGIC_USER_ID
        self.user_password = settings.FLIGHTLOGIC_PASSWORD
        self.environment = settings.FLIGHTLOGIC_ACCESS_TYPE
        self.ip_address = settings.FLIGHTLOGIC_IP_ADDRESS or "127.0.0.1"
        self.api_url = (
            settings.FLIGHTLOGIC_API_URL or "https://travelnext.works/api/aeroVE5"
        )

    async def ping(self) -> str:
        """
        Test FlightLogic API credentials with a minimal request.

        Returns:
            Success message with masked credentials

        Raises:
            RuntimeError: If credentials are invalid or API is unreachable
        """
        import httpx

        try:
            # Create minimal test request payload
            test_payload = {
                "user_id": self.user_id,
                "user_password": self.user_password,
                "environment": self.environment,
                "ip_address": self.ip_address,
                "originDestinationInfo": [
                    {
                        "originLocationCode": "LHR",
                        "destinationLocationCode": "JFK",
                        "departureDate": "2025-12-01",
                    }
                ],
                "passengers": {"adults": 1, "children": 0, "infants": 0},
                "cabinClass": "Economy",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/availability",
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    response_data = response.json()

                    # Check if we get authentication error in response
                    if (
                        response_data.get("Errors", {}).get("ErrorMessage")
                        == "Invalid user_id/user_password"
                    ):
                        raise RuntimeError(
                            f"FlightLogic authentication failed - invalid credentials for user_id: {self.user_id}"
                        )

                    # Success - credentials are valid
                    masked_password = (
                        f"{self.user_password[:4]}***"
                        if len(self.user_password) > 4
                        else "***"
                    )
                    return f"FlightLogic API accessible - user_id: {self.user_id}, password: {masked_password}"
                raise RuntimeError(
                    f"FlightLogic API returned HTTP {response.status_code}: {response.text}"
                )

        except httpx.TimeoutException:
            raise RuntimeError(
                "FlightLogic API timeout - service may be unavailable"
            ) from None
        except httpx.RequestError as e:
            raise RuntimeError(f"FlightLogic API connection failed: {e}") from e
        except Exception as exc:
            raise RuntimeError(f"FlightLogic health-check failed: {exc}") from exc


class SendGridHealthChecker:
    """
    Small utility that validates we can talk to the SendGrid API.
    Uses the API key validation endpoint to test connectivity.
    """

    _BASE_URL = "https://api.sendgrid.com/v3"

    def __init__(self) -> None:
        api_key = settings.SENDGRID_API_KEY
        if not api_key:
            raise RuntimeError(
                "No SendGrid API key supplied - set SENDGRID_API_KEY "
                "in your environment."
            )
        self.api_key = api_key

    async def ping(self) -> str:
        """
        Makes a minimal API call to verify SendGrid API connectivity.

        Raises:
            RuntimeError – if the call fails for any reason (network,
                           authentication, quota, etc.).
        """
        try:
            url = f"{self._BASE_URL}/scopes"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    scopes_count = len(data.get("scopes", []))
                    return f"{scopes_count} API scopes available"
                raise RuntimeError(f"API returned status {response.status_code}")
        except Exception as exc:
            raise RuntimeError(f"SendGrid health-check failed: {exc}") from exc
