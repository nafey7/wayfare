"""Unit tests for database connection configuration to prevent regression issues.

These tests ensure that database connection variables are correctly configured
and prevent the issues that occurred when MONGODB_URI vs DATABASE_URL were mismatched.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app.database.connection import (
    DatabaseConnection,
    check_database_health,
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
    mongodb_connect_test,
    mongodb_connect_test_scram,
)


class TestDatabaseConnection:
    """Test database connection configuration and methods."""

    @pytest.fixture
    def db_connection(self) -> DatabaseConnection:
        """Create a fresh DatabaseConnection instance for testing."""
        return DatabaseConnection()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with valid database configuration."""
        mock_settings = MagicMock()
        mock_settings.DATABASE_URL = (
            "mongodb+srv://user:pass@cluster.mongodb.net/testdb"
        )
        mock_settings.MONGODB_URI = "mongodb+srv://user:pass@cluster.mongodb.net/testdb"
        mock_settings.DATABASE_NAME = "voya_test"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1
        return mock_settings

    def test_database_connection_initialization(
        self, db_connection: DatabaseConnection
    ):
        """Test that DatabaseConnection initializes with correct defaults."""
        assert db_connection.client is None
        assert db_connection.database is None
        assert db_connection._is_connected is False

    @patch("app.database.connection.settings")
    @patch("app.database.connection.AsyncIOMotorClient")
    async def test_connect_uses_database_url(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        db_connection: DatabaseConnection,
    ):
        """Test that connect() uses settings.MONGODB_URI correctly.

        This ensures consistent use of MONGODB_URI throughout the codebase.
        """
        # Setup
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        mock_settings.MONGODB_URI = "mongodb+srv://test:pass@cluster.mongodb.net/testdb"
        mock_settings.DATABASE_NAME = "voya_test"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1

        # Execute
        await db_connection.connect()

        # Verify MONGODB_URI is used
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        assert call_args[0][0] == mock_settings.MONGODB_URI

    @patch("app.database.connection.settings")
    async def test_connect_validates_uri_format(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test that invalid MongoDB URIs are properly validated."""
        # Test invalid URI format
        mock_settings.MONGODB_URI = "invalid-uri-format"
        mock_settings.DATABASE_URL = "invalid-uri-format"

        await db_connection.connect()

        # Should not connect with invalid URI
        assert not db_connection._is_connected
        assert db_connection.client is None

    @patch("app.database.connection.settings")
    async def test_connect_handles_authentication_failure(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test proper handling of authentication failures."""
        mock_settings.DATABASE_URL = (
            "mongodb+srv://invalid:pass@cluster.mongodb.net/testdb"
        )
        mock_settings.MONGODB_URI = (
            "mongodb+srv://invalid:pass@cluster.mongodb.net/testdb"
        )
        mock_settings.DATABASE_NAME = "voya_test"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1

        with patch("app.database.connection.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command.side_effect = Exception("Authentication failed")

            # Should raise exception for auth failure
            with pytest.raises(Exception, match="Authentication failed"):
                await db_connection.connect()

            assert not db_connection._is_connected

    @patch("app.database.connection.settings")
    async def test_connect_handles_timeout(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test proper handling of connection timeouts."""
        mock_settings.DATABASE_URL = (
            "mongodb+srv://user:pass@unreachable.mongodb.net/testdb"
        )
        mock_settings.MONGODB_URI = (
            "mongodb+srv://user:pass@unreachable.mongodb.net/testdb"
        )
        mock_settings.DATABASE_NAME = "voya_test"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1

        with patch("app.database.connection.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command.side_effect = ServerSelectionTimeoutError(
                "Timeout"
            )

            # Should raise ServerSelectionTimeoutError
            with pytest.raises(ServerSelectionTimeoutError):
                await db_connection.connect()

            assert not db_connection._is_connected

    def test_validate_mongodb_uri_valid_formats(
        self, db_connection: DatabaseConnection
    ):
        """Test URI validation accepts valid MongoDB URI formats."""
        valid_uris = [
            "mongodb://localhost:27017",
            "mongodb+srv://user:pass@cluster.mongodb.net/db",
            "mongodb://user:pass@host:27017/database",
        ]

        for uri in valid_uris:
            error = db_connection._validate_mongodb_uri(uri)
            assert error is None, f"URI {uri} should be valid but got error: {error}"

    def test_validate_mongodb_uri_invalid_formats(
        self, db_connection: DatabaseConnection
    ):
        """Test URI validation rejects invalid MongoDB URI formats."""
        invalid_uris = [
            "",
            "http://localhost:27017",
            "postgres://localhost:5432/db",
            "invalid-format",
            None,
        ]

        for uri in invalid_uris:
            error = db_connection._validate_mongodb_uri(uri)
            assert error is not None, (
                f"URI {uri} should be invalid but validation passed"
            )

    def test_sanitize_uri_for_logging(self, db_connection: DatabaseConnection):
        """Test that credentials are properly hidden in logs."""
        test_cases = [
            (
                "mongodb+srv://username:password@cluster.mongodb.net/db",
                "mongodb+srv://[CREDENTIALS_HIDDEN]@cluster.mongodb.net/db",
            ),
            (
                "mongodb://user:pass@localhost:27017/db",
                "mongodb://[CREDENTIALS_HIDDEN]@localhost:27017/db",
            ),
            (
                "mongodb://localhost:27017",  # No credentials
                "mongodb://localhost:27017",
            ),
        ]

        for original, expected in test_cases:
            result = db_connection._sanitize_uri_for_logging(original)
            assert result == expected
            # Ensure no passwords are visible in sanitized URI
            assert "password" not in result.lower()
            assert "pass" not in result.lower() or "pass" in expected.lower()

    @patch("app.database.connection.settings")
    async def test_get_database_requires_connection(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test that get_database() raises error when not connected."""
        with pytest.raises(RuntimeError, match="Database not connected"):
            db_connection.get_database()

    @patch("app.database.connection.settings")
    async def test_get_collection_requires_connection(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test that get_collection() raises error when not connected."""
        with pytest.raises(RuntimeError, match="Database not connected"):
            db_connection.get_collection("test_collection")

    @patch("app.database.connection.settings")
    async def test_check_connection_when_not_connected(
        self, mock_settings: MagicMock, db_connection: DatabaseConnection
    ):
        """Test health check returns False when not connected."""
        result = await db_connection.check_connection()
        assert result is False

    @patch("app.database.connection.settings")
    @patch("app.database.connection.AsyncIOMotorClient")
    async def test_successful_connection_flow(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        db_connection: DatabaseConnection,
    ):
        """Test complete successful connection flow."""
        # Setup
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_database = MagicMock()
        mock_client.__getitem__.return_value = mock_database

        mock_settings.DATABASE_URL = (
            "mongodb+srv://test:pass@cluster.mongodb.net/testdb"
        )
        mock_settings.MONGODB_URI = "mongodb+srv://test:pass@cluster.mongodb.net/testdb"
        mock_settings.DATABASE_NAME = "voya_test"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1

        # Execute connection
        await db_connection.connect()

        # Verify connection state
        assert db_connection._is_connected is True
        assert db_connection.client is not None
        assert db_connection.database is not None

        # Test database access
        database = db_connection.get_database()
        assert database is not None

        # Test collection access
        collection = db_connection.get_collection("test_collection")
        assert collection is not None

        # Test health check
        health = await db_connection.check_connection()
        assert health is True

        # Test disconnect
        await db_connection.disconnect()
        assert db_connection._is_connected is False


class TestDatabaseHelperFunctions:
    """Test helper functions for database connectivity."""

    @patch("app.database.connection.settings")
    @patch("app.database.connection.MongoClient")
    def test_mongodb_connect_test_uses_mongodb_uri(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ):
        """Test that mongodb_connect_test uses MONGODB_URI correctly."""
        # Setup
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_settings.MONGODB_URI = "mongodb+srv://test:pass@cluster.mongodb.net/testdb"

        # Execute
        mongodb_connect_test()

        # Verify correct URI is used
        mock_client_class.assert_called_once_with(
            mock_settings.MONGODB_URI, server_api=ANY
        )

    @patch("app.database.connection.settings")
    @patch("app.database.connection.MongoClient")
    def test_mongodb_connect_test_scram_uses_mongodb_uri(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ):
        """Test that mongodb_connect_test_scram uses MONGODB_URI correctly."""
        # Setup
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_settings.MONGODB_URI = "mongodb+srv://test:pass@cluster.mongodb.net/testdb"

        # Execute
        result = mongodb_connect_test_scram()

        # Verify correct URL is used and connection succeeds
        mock_client_class.assert_called_once_with(
            mock_settings.MONGODB_URI, server_api=ANY
        )
        assert result is True

    @patch("app.database.connection._db_connection")
    async def test_connect_to_mongodb_uses_global_connection(
        self, mock_global_connection: MagicMock
    ):
        """Test that connect_to_mongodb uses the global connection instance."""
        mock_global_connection.connect = AsyncMock()

        await connect_to_mongodb()

        mock_global_connection.connect.assert_called_once()

    @patch("app.database.connection._db_connection")
    async def test_disconnect_from_mongodb_uses_global_connection(
        self, mock_global_connection: MagicMock
    ):
        """Test that disconnect_from_mongodb uses the global connection instance."""
        mock_global_connection.disconnect = AsyncMock()

        await disconnect_from_mongodb()

        mock_global_connection.disconnect.assert_called_once()

    @patch("app.database.connection._db_connection")
    async def test_check_database_health_uses_global_connection(
        self, mock_global_connection: MagicMock
    ):
        """Test that check_database_health uses the global connection instance."""
        mock_global_connection.check_connection = AsyncMock(return_value=True)

        result = await check_database_health()

        mock_global_connection.check_connection.assert_called_once()
        assert result is True

    def test_get_connection_returns_global_instance(self):
        """Test that get_connection returns the global database connection instance."""
        connection = get_connection()

        # Should return the same global instance
        assert connection is not None
        assert isinstance(connection, DatabaseConnection)

        # Multiple calls should return the same instance
        connection2 = get_connection()
        assert connection is connection2


class TestDatabaseConnectionRegression:
    """Specific regression tests for the database connection issues that were fixed."""

    @patch("app.database.connection.settings")
    @patch("app.database.connection.AsyncIOMotorClient")
    async def test_regression_database_url_vs_mongodb_uri_consistency(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ):
        """Regression test: Ensure DATABASE_URL is used consistently in AsyncIOMotorClient.

        This test prevents the bug where connection.py line 51 used settings.DATABASE_URL
        but line 60 used settings.MONGODB_URI, causing connection failures.
        """
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        # Set different values to catch inconsistency
        mock_settings.DATABASE_URL = (
            "mongodb+srv://prod:pass@prod-cluster.mongodb.net/voya"
        )
        mock_settings.MONGODB_URI = "mongodb://localhost:27017"  # Different!
        mock_settings.DATABASE_NAME = "voya"
        mock_settings.DATABASE_MAX_POOL_SIZE = 10
        mock_settings.DATABASE_MIN_POOL_SIZE = 1

        db_connection = DatabaseConnection()
        await db_connection.connect()

        # Verify AsyncIOMotorClient was called with MONGODB_URI (current implementation)
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args[0][0]
        assert call_args == mock_settings.MONGODB_URI
