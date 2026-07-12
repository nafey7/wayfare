"""
Fixtures for AI handler characterization tests.

PURPOSE: Capture current AI handler behavior before refactoring.
These tests document how the system works NOW, not how it should work.

REQUIREMENTS:
- FlightLogic mock server: docker compose up -d
- Gemini API key: GOOGLE_GENERATIVE_AI_API_KEY in .env

NOT FOR CI: These tests make real Gemini API calls and require local setup.
Run manually during migration/refactoring work.

Run with: pytest tests/integration_tests/ai/ -v -m integration

TRANSCRIPT EXPORT:
Run with --export-transcripts to generate a markdown file with all conversations:
    pytest tests/integration_tests/ai/ -v --export-transcripts
Output: tests/integration_tests/ai/transcripts/YYYY-MM-DD_transcripts.md
"""

import inspect
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.config import settings
from app.database.connection import _db_connection as db_manager
from app.domains.chat.schemas import ChatResponse
from app.domains.chat.service import ChatService
from app.domains.common import AuthProvider
from app.domains.user.enums import UserStatus
from app.domains.user.schemas import UserPublic

# Configure test logger
logger = logging.getLogger("ai_integration_tests")
logger.setLevel(logging.INFO)

# Add handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("\n%(message)s"))
    logger.addHandler(handler)


# ============================================================================
# Transcript Collection Infrastructure
# ============================================================================


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""

    turn_number: int
    user_message: str
    llm_response: str
    intent_name: str | None
    confidence: float | None
    response_type: str
    response_data: dict | None


@dataclass
class TestTranscript:
    """Complete transcript for a single test."""

    test_name: str
    test_class: str
    test_module: str
    docstring: str | None
    turns: list[ConversationTurn] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    outcome: str = "unknown"  # passed, failed, skipped, xfailed
    failure_reason: str | None = None
    is_multi_turn: bool = False


def extract_assertions_from_source(func) -> list[str]:
    """Extract assertion statements from a test function's source code.

    Returns a list of assertion lines, cleaned up for readability.
    """
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return []

    assertions = []
    lines = source.split("\n")

    # Track multi-line assertions
    in_multiline = False
    current_assertion = ""

    for line in lines:
        stripped = line.strip()

        # Handle multi-line assertions (lines ending with continuation)
        if in_multiline:
            current_assertion += " " + stripped
            if not stripped.endswith(("(", ",", "\\")):
                # Clean up and add the complete assertion
                cleaned = _clean_assertion(current_assertion)
                if cleaned:
                    assertions.append(cleaned)
                in_multiline = False
                current_assertion = ""
            continue

        # Match assert statements
        if stripped.startswith("assert "):
            if stripped.endswith(("(", ",", "\\")):
                in_multiline = True
                current_assertion = stripped
            else:
                cleaned = _clean_assertion(stripped)
                if cleaned:
                    assertions.append(cleaned)

        # Match pytest.xfail calls (document expected failures)
        elif "pytest.xfail(" in stripped:
            # Extract the reason from xfail
            match = re.search(r'pytest\.xfail\(["\'](.+?)["\']', stripped)
            if match:
                assertions.append(f"XFAIL: {match.group(1)[:100]}")
            else:
                assertions.append("XFAIL: (expected failure)")

    return assertions


def _clean_assertion(assertion: str) -> str | None:
    """Clean up an assertion string for display.

    Removes 'assert ' prefix and simplifies for readability.
    """
    # Remove 'assert ' prefix
    if assertion.startswith("assert "):
        assertion = assertion[7:]

    # Skip very long assertions (likely data dumps)
    if len(assertion) > 200:
        # Try to extract just the condition
        if "," in assertion:
            assertion = assertion.split(",")[0]
        if len(assertion) > 200:
            return assertion[:100] + "..."

    # Clean up whitespace
    assertion = " ".join(assertion.split())

    return assertion if assertion else None


class TranscriptCollector:
    """Collects transcripts from all tests in a session."""

    def __init__(self):
        self.transcripts: list[TestTranscript] = []
        self._current_transcript: TestTranscript | None = None

    def start_test(
        self,
        test_name: str,
        test_class: str,
        test_module: str,
        docstring: str | None,
        assertions: list[str] | None = None,
    ):
        """Start collecting for a new test."""
        self._current_transcript = TestTranscript(
            test_name=test_name,
            test_class=test_class,
            test_module=test_module,
            docstring=docstring,
            assertions=assertions or [],
        )

    def add_turn(
        self,
        turn_number: int,
        user_message: str,
        response: ChatResponse,
    ):
        """Add a conversation turn to the current test."""
        if self._current_transcript is None:
            return

        turn = ConversationTurn(
            turn_number=turn_number,
            user_message=user_message,
            llm_response=response.message or "",
            intent_name=response.intent_name,
            confidence=response.confidence,
            response_type=response.type,
            response_data=response.data,
        )
        self._current_transcript.turns.append(turn)

        # Mark as multi-turn if we have more than one turn
        if turn_number > 1:
            self._current_transcript.is_multi_turn = True

    def finish_test(self, outcome: str, failure_reason: str | None = None):
        """Finish current test and store transcript."""
        if self._current_transcript is not None:
            self._current_transcript.outcome = outcome
            self._current_transcript.failure_reason = failure_reason
            self.transcripts.append(self._current_transcript)
            self._current_transcript = None

    def export_markdown(self, output_path: Path) -> None:
        """Export all transcripts to a markdown file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("# AI Handler Characterization Test Transcripts\n\n")
            f.write(f"**Generated**: {datetime.now(UTC).isoformat()}\n")
            f.write(f"**Total Tests**: {len(self.transcripts)}\n")

            # Summary statistics
            passed = sum(1 for t in self.transcripts if t.outcome == "passed")
            failed = sum(1 for t in self.transcripts if t.outcome == "failed")
            xfailed = sum(1 for t in self.transcripts if t.outcome == "xfailed")
            skipped = sum(1 for t in self.transcripts if t.outcome == "skipped")
            multi_turn = sum(1 for t in self.transcripts if t.is_multi_turn)

            f.write(
                f"**Passed**: {passed} | **Failed**: {failed} | "
                f"**XFailed**: {xfailed} | **Skipped**: {skipped}\n"
            )
            f.write(f"**Multi-turn conversations**: {multi_turn}\n\n")
            f.write("---\n\n")

            # Group by test class
            by_class: dict[str, list[TestTranscript]] = {}
            for t in self.transcripts:
                key = t.test_class or "Uncategorized"
                if key not in by_class:
                    by_class[key] = []
                by_class[key].append(t)

            for class_name, tests in sorted(by_class.items()):
                f.write(f"## {class_name}\n\n")

                for transcript in tests:
                    # Test header with outcome badge
                    badge = {
                        "passed": "✅",
                        "failed": "❌",
                        "skipped": "⏭️",
                        "xfailed": "⚠️",
                    }.get(transcript.outcome, "❓")
                    multi_badge = "🔄" if transcript.is_multi_turn else "1️⃣"

                    f.write(f"### {badge} {multi_badge} {transcript.test_name}\n\n")

                    if transcript.docstring:
                        f.write(f"*{transcript.docstring.strip()}*\n\n")

                    if transcript.failure_reason:
                        f.write(f"**Failure**: `{transcript.failure_reason}`\n\n")

                    if not transcript.turns:
                        f.write("*No conversation recorded*\n\n")
                    else:
                        # Conversation transcript
                        f.write("**Conversation:**\n")
                        f.write("```\n")
                        for turn in transcript.turns:
                            f.write(f"[Turn {turn.turn_number}]\n")
                            f.write(f"USER: {turn.user_message}\n")
                            f.write(f"LLM:  {turn.llm_response[:500]}")
                            if len(turn.llm_response) > 500:
                                f.write("...")
                            f.write("\n")
                            f.write(
                                f"      intent={turn.intent_name} | "
                                f"confidence={turn.confidence} | "
                                f"type={turn.response_type}\n"
                            )
                            if turn.response_data:
                                data_str = json.dumps(turn.response_data, default=str)
                                if len(data_str) > 200:
                                    data_str = data_str[:200] + "..."
                                f.write(f"      data={data_str}\n")
                            f.write("\n")
                        f.write("```\n\n")

                    # Assertions section
                    if transcript.assertions:
                        f.write("**Assertions:**\n")
                        for assertion in transcript.assertions:
                            if assertion.startswith("XFAIL:"):
                                f.write(f"- ⚠️ {assertion}\n")
                            else:
                                f.write(f"- `{assertion}`\n")
                        f.write("\n")

                f.write("---\n\n")

        logger.info(f"\n📝 Transcripts exported to: {output_path}")


# Global collector instance
_transcript_collector = TranscriptCollector()


def pytest_addoption(parser):
    """Add --export-transcripts option."""
    parser.addoption(
        "--export-transcripts",
        action="store_true",
        default=False,
        help="Export conversation transcripts to markdown file",
    )


def pytest_runtest_setup(item):
    """Called before each test runs."""
    if not item.config.getoption("--export-transcripts", default=False):
        return

    # Extract test metadata
    test_name = item.name
    test_class = item.cls.__name__ if item.cls else None
    test_module = item.module.__name__ if item.module else None
    docstring = item.function.__doc__ if hasattr(item, "function") else None

    # Extract assertions from test source code
    assertions = []
    if hasattr(item, "function"):
        assertions = extract_assertions_from_source(item.function)

    _transcript_collector.start_test(
        test_name, test_class, test_module, docstring, assertions
    )


def pytest_runtest_makereport(item, call):
    """Called after each test phase (setup, call, teardown)."""
    if call.when != "call":
        return

    if not item.config.getoption("--export-transcripts", default=False):
        return

    if call.excinfo is not None:
        # Check for xfail (expected failure)
        # pytest.xfail() raises _pytest.outcomes.XFail
        exc_type_name = call.excinfo.type.__name__
        exc_module = getattr(call.excinfo.type, "__module__", "")
        failure_str = str(call.excinfo.value)

        is_xfail = (
            exc_type_name == "XFail"
            or "outcomes" in exc_module
            or "KNOWN BEHAVIOR" in failure_str
            or failure_str.startswith("XFAIL")
        )

        if is_xfail:
            outcome = "xfailed"
            failure_reason = failure_str[:200]
        else:
            outcome = "failed"
            failure_reason = failure_str[:200]
    else:
        outcome = "passed"
        failure_reason = None

    _transcript_collector.finish_test(outcome, failure_reason)


def pytest_sessionfinish(session, exitstatus):
    """Called after all tests complete."""
    if not session.config.getoption("--export-transcripts", default=False):
        return

    # Export transcripts
    output_dir = Path(__file__).parent / "transcripts"
    output_file = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_transcripts.md"
    _transcript_collector.export_markdown(output_file)


# ============================================================================
# Mock Server Configuration
# ============================================================================


def is_mock_server_available() -> bool:
    """Check if FlightLogic mock server is configured.

    Mock server configuration is done by tests/conftest.py:pytest_configure
    which runs before any imports. If the mock server was detected, the
    FLIGHTLOGIC_API_URL environment variable will contain 'localhost'.
    """
    api_url = os.environ.get("FLIGHTLOGIC_API_URL", "")
    return "localhost" in api_url


@pytest.fixture(scope="session", autouse=True)
def configure_flightlogic_mock():
    """Configure FlightLogic to use mock server if available.

    Since Settings is instantiated at import time (before pytest_configure runs),
    we need to patch the settings object directly here.
    """
    if is_mock_server_available():
        api_url = os.environ.get("FLIGHTLOGIC_API_URL", "")
        logger.info(f"\n{'=' * 60}")
        logger.info("✅ FlightLogic mock server detected - using mock data")
        logger.info(f"   URL: {api_url}")
        logger.info("   Credentials: test_user / test_password")
        logger.info(f"{'=' * 60}\n")

        # Patch the settings object directly since it was created before env vars were set
        # Settings is a Pydantic model - use object.__setattr__ to bypass frozen check
        # IMPORTANT: FLIGHTS_API_BASE_URL takes precedence over API_URL in the client
        mock_url = os.environ.get("FLIGHTLOGIC_API_URL", api_url)
        hotel_url = mock_url.replace("/api/aeroVE5", "/api/hotel-api-v6")
        object.__setattr__(settings, "FLIGHTLOGIC_FLIGHTS_API_BASE_URL", mock_url)
        object.__setattr__(settings, "FLIGHTLOGIC_HOTELS_API_BASE_URL", hotel_url)
        object.__setattr__(settings, "FLIGHTLOGIC_API_URL", mock_url)
        object.__setattr__(settings, "FLIGHTLOGIC_API_KEY", "mock-api-key-test")
        object.__setattr__(settings, "FLIGHTLOGIC_USER_ID", "test_user")
        object.__setattr__(settings, "FLIGHTLOGIC_PASSWORD", "test_password")
        object.__setattr__(settings, "FLIGHTLOGIC_ACCESS_TYPE", "Test")
    else:
        logger.info(f"\n{'=' * 60}")
        logger.info("⚠️  FlightLogic mock server not running")
        logger.info("   Search/booking tests may fail or return errors")
        logger.info("   Start with: docker compose up -d flightlogic-mock")
        logger.info(f"{'=' * 60}\n")


@pytest.fixture
def mock_server_running() -> bool:
    """Fixture that requires FlightLogic mock server.

    These characterization tests require:
    1. FlightLogic mock server running (docker compose up -d)
    2. Gemini API access (GOOGLE_GENERATIVE_AI_API_KEY)

    They are NOT meant for CI - they capture current behavior before refactoring.
    """
    if not is_mock_server_available():
        pytest.fail("FlightLogic mock server required. Run: docker compose up -d")
    return True


class LoggingChatService:
    """Wrapper around ChatService that logs all messages and records transcripts."""

    def __init__(self, chat_service: ChatService):
        self._service = chat_service
        self._turn_count = 0

    async def process_message(
        self,
        message: str,
        user: UserPublic,
        chat_id: str,
    ) -> ChatResponse:
        """Process message and log both user input and LLM response."""
        self._turn_count += 1

        # Log user message
        logger.info(f"{'=' * 60}")
        logger.info(f"TURN {self._turn_count} | USER: {message}")

        # Process message
        response = await self._service.process_message(
            message=message,
            user=user,
            chat_id=chat_id,
        )

        # Log LLM response with details
        logger.info(f"TURN {self._turn_count} | LLM: {response.message}")
        logger.info(
            f"  → intent={response.intent_name} | "
            f"confidence={response.confidence} | "
            f"type={response.type}"
        )
        if response.data:
            logger.info(f"  → data={response.data}")
        logger.info(f"{'=' * 60}")

        # Record turn for transcript export
        _transcript_collector.add_turn(self._turn_count, message, response)

        return response


@pytest.fixture
async def setup_ai_database():
    """Ensure database is connected for AI tests."""
    if not db_manager._is_connected:
        await db_manager.connect()
    # Don't disconnect - other tests may need it


@pytest.fixture
def test_user() -> UserPublic:
    """Test user for ChatService calls.

    Uses a valid MongoDB ObjectId format for user_id.
    """
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret  # Valid ObjectId format
        email="integration-test@example.com",
        first_name="Integration",
        last_name="Tester",
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def chat_service(setup_ai_database) -> LoggingChatService:
    """Real ChatService instance wrapped with logging.

    Logs all user messages and LLM responses for test visibility.
    Depends on setup_ai_database to ensure MongoDB is connected.
    """
    return LoggingChatService(ChatService())


@pytest.fixture
def chat_id() -> str:
    """Unique chat ID for test isolation."""
    return f"test-chat-{datetime.now().timestamp()}"


# ============================================================================
# Response Extraction Helpers
# ============================================================================


def get_collected(response: ChatResponse) -> dict:
    """Extract collected_so_far from response data.

    Returns empty dict if response.data is None or missing collected_so_far.
    """
    if response.data is None:
        return {}
    return response.data.get("collected_so_far", {})


def get_waiting_for(response: ChatResponse) -> str | None:
    """Extract waiting_for field from response data.

    Returns None if response.data is None or missing waiting_for.
    """
    if response.data is None:
        return None
    return response.data.get("waiting_for")
