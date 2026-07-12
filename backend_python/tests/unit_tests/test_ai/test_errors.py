"""Unit tests for the AI-CHAT-010 error classifier.

Covers:
- One positive match per ``ErrorClass`` value
- ``FlightApiError`` special-case status-code routing (401/403/4xx/5xx)
- Unknown exceptions fall through to ``UNKNOWN`` (never raises)
- ``is_retryable`` matches the documented policy (only transient classes)
- ``user_message`` populated for every class
- ``log_detail`` truncates very long exception messages
"""

from __future__ import annotations

import pytest

from app.ai.errors import (
    ClassifiedError,
    ErrorClass,
    classify_exception,
)

# ---------------------------------------------------------------------------
# Test-only stand-ins for third-party exception types. We don't import the
# real OpenAI / httpx classes here because (a) they don't always carry the
# constructor signature we want for tests, and (b) the classifier matches
# on ``type(exc).__name__`` — so a local class with the right name suffices.
# ---------------------------------------------------------------------------


def _make_exc(name: str, message: str = "", **attrs: object) -> Exception:
    """Build a one-off exception class with the given name and attributes."""
    cls = type(name, (Exception,), attrs)
    return cls(message)


# ---------------------------------------------------------------------------
# Each known exception name should map to the expected class
# ---------------------------------------------------------------------------


class TestKnownExceptionMapping:
    @pytest.mark.parametrize(
        ("exc_name", "expected_class"),
        [
            # OpenAI transient
            ("RateLimitError", ErrorClass.TRANSIENT_LLM),
            ("APITimeoutError", ErrorClass.TRANSIENT_LLM),
            ("InternalServerError", ErrorClass.TRANSIENT_LLM),
            ("APIConnectionError", ErrorClass.TRANSIENT_LLM),
            # OpenAI deterministic
            ("BadRequestError", ErrorClass.VALIDATION),
            ("ContentPolicyViolationError", ErrorClass.CONTENT_POLICY),
            ("AuthenticationError", ErrorClass.QUOTA),
            ("PermissionDeniedError", ErrorClass.QUOTA),
            # Google GenAI
            ("ResourceExhausted", ErrorClass.QUOTA),
            ("DeadlineExceeded", ErrorClass.TRANSIENT_LLM),
            ("ServiceUnavailable", ErrorClass.TRANSIENT_LLM),
            # httpx
            ("TimeoutException", ErrorClass.TRANSIENT_API),
            ("ConnectError", ErrorClass.TRANSIENT_API),
            ("ReadTimeout", ErrorClass.TRANSIENT_API),
            ("WriteTimeout", ErrorClass.TRANSIENT_API),
            # Voya domain
            ("FlightSearchError", ErrorClass.VALIDATION),
            ("HotelSearchError", ErrorClass.VALIDATION),
            ("FlightValidationError", ErrorClass.VALIDATION),
            ("FlightBookingError", ErrorClass.VALIDATION),
            ("HotelBookingError", ErrorClass.VALIDATION),
            ("HotelRateError", ErrorClass.VALIDATION),
            ("FlightBookingSupplierSyncError", ErrorClass.TRANSIENT_API),
            # Builtins
            ("TimeoutError", ErrorClass.TRANSIENT_API),
            ("ConnectionError", ErrorClass.TRANSIENT_API),
            ("ValueError", ErrorClass.VALIDATION),
            ("TypeError", ErrorClass.VALIDATION),
            # Pydantic (the unqualified name)
            ("ValidationError", ErrorClass.VALIDATION),
        ],
    )
    def test_exception_name_maps_to_class(
        self, exc_name: str, expected_class: ErrorClass
    ) -> None:
        result = classify_exception(_make_exc(exc_name, "test failure"))
        assert result.cls is expected_class, (
            f"expected {exc_name} -> {expected_class}, got {result.cls}"
        )


# ---------------------------------------------------------------------------
# FlightApiError carries a status_code — must be classified by HTTP code
# ---------------------------------------------------------------------------


class TestFlightApiErrorStatusCode:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (401, ErrorClass.QUOTA),  # auth revoked
            (403, ErrorClass.QUOTA),  # permission denied
            (400, ErrorClass.VALIDATION),
            (404, ErrorClass.VALIDATION),
            (422, ErrorClass.VALIDATION),
            (500, ErrorClass.TRANSIENT_API),
            (502, ErrorClass.TRANSIENT_API),
            (503, ErrorClass.TRANSIENT_API),
            (504, ErrorClass.TRANSIENT_API),
        ],
    )
    def test_status_code_routing(self, status: int, expected: ErrorClass) -> None:
        exc = _make_exc(
            "FlightApiError", "FlightLogic returned error", status_code=status
        )
        result = classify_exception(exc)
        assert result.cls is expected, (
            f"FlightApiError status={status} should map to {expected}, got {result.cls}"
        )

    def test_flight_api_error_without_status_code_is_unknown(self) -> None:
        exc = _make_exc("FlightApiError", "no status_code attr")
        result = classify_exception(exc)
        assert result.cls is ErrorClass.UNKNOWN

    def test_flight_api_error_with_unrecognised_status_is_unknown(self) -> None:
        exc = _make_exc("FlightApiError", "weird", status_code=999)
        result = classify_exception(exc)
        assert result.cls is ErrorClass.UNKNOWN

    def test_flight_api_error_with_non_int_status_does_not_raise(self) -> None:
        """status_code that survives an odd round-trip (e.g. str) must not TypeError.

        Regression for PR #1088 review item #8 — chained ``400 <= status < 500``
        on a non-int would explode; the classifier contract is "never raises".
        """
        for bad_status in ("500", None, object(), 5.5):
            exc = _make_exc("FlightApiError", "weird", status_code=bad_status)
            result = classify_exception(exc)
            assert result.cls is ErrorClass.UNKNOWN


# ---------------------------------------------------------------------------
# Unknown exceptions never raise and fall through
# ---------------------------------------------------------------------------


class TestUnknownFallback:
    def test_unrecognised_exception_returns_unknown(self) -> None:
        result = classify_exception(_make_exc("SomeWeirdNeverSeen", "x"))
        assert result.cls is ErrorClass.UNKNOWN

    def test_classify_never_raises_on_any_exception(self) -> None:
        for name in ("FooBar", "BazError", "MysteryThing"):
            classify_exception(_make_exc(name, "x"))  # no assertion, just no raise

    def test_classify_handles_baseexception(self) -> None:
        # KeyboardInterrupt etc. inherit from BaseException, not Exception.
        # Classifier accepts BaseException — must not raise.
        result = classify_exception(KeyboardInterrupt("interrupted"))
        assert result.cls is ErrorClass.UNKNOWN

    def test_classify_handles_exception_with_no_message(self) -> None:
        result = classify_exception(_make_exc("Whatever"))
        assert result.cls is ErrorClass.UNKNOWN
        assert result.log_detail  # still produces something for the log


# ---------------------------------------------------------------------------
# is_retryable matches documented policy: only transient classes retry
# ---------------------------------------------------------------------------


class TestRetryability:
    @pytest.mark.parametrize(
        ("cls", "expected_retryable"),
        [
            (ErrorClass.TRANSIENT_LLM, True),
            (ErrorClass.TRANSIENT_API, True),
            (ErrorClass.VALIDATION, False),
            (ErrorClass.CONTENT_POLICY, False),
            (ErrorClass.QUOTA, False),
            (ErrorClass.UNKNOWN, False),
        ],
    )
    def test_is_retryable_per_class(
        self, cls: ErrorClass, expected_retryable: bool
    ) -> None:
        # Pick a representative exception name for each class.
        sample = {
            ErrorClass.TRANSIENT_LLM: "RateLimitError",
            ErrorClass.TRANSIENT_API: "TimeoutException",
            ErrorClass.VALIDATION: "ValueError",
            ErrorClass.CONTENT_POLICY: "ContentPolicyViolationError",
            ErrorClass.QUOTA: "AuthenticationError",
            ErrorClass.UNKNOWN: "FooBar",
        }[cls]
        result = classify_exception(_make_exc(sample))
        assert result.is_retryable is expected_retryable


# ---------------------------------------------------------------------------
# User messages are populated for every class + log_detail truncates
# ---------------------------------------------------------------------------


class TestUserMessageAndLogDetail:
    def test_every_class_has_a_user_message(self) -> None:
        # Ensure every class is covered by the user-message map by
        # iterating over the enum directly. A missing class would raise
        # KeyError on the lookup.
        for cls in ErrorClass:
            result = classify_exception(
                _make_exc("CustomExc", "x")
                if cls is ErrorClass.UNKNOWN
                else _make_exc(
                    {
                        ErrorClass.TRANSIENT_LLM: "RateLimitError",
                        ErrorClass.TRANSIENT_API: "TimeoutException",
                        ErrorClass.VALIDATION: "ValueError",
                        ErrorClass.CONTENT_POLICY: "ContentPolicyViolationError",
                        ErrorClass.QUOTA: "AuthenticationError",
                        ErrorClass.UNKNOWN: "WhateverError",
                    }[cls]
                )
            )
            assert result.user_message
            assert isinstance(result.user_message, str)

    def test_user_message_never_says_im_just_an_ai(self) -> None:
        """Tone rule shared with AI-CHAT-013 — never 'I'm just an AI'."""
        for cls in ErrorClass:
            sample_exc = _make_exc(
                {
                    ErrorClass.TRANSIENT_LLM: "RateLimitError",
                    ErrorClass.TRANSIENT_API: "TimeoutException",
                    ErrorClass.VALIDATION: "ValueError",
                    ErrorClass.CONTENT_POLICY: "ContentPolicyViolationError",
                    ErrorClass.QUOTA: "AuthenticationError",
                    ErrorClass.UNKNOWN: "FooBar",
                }[cls]
            )
            result = classify_exception(sample_exc)
            assert "i'm just an ai" not in result.user_message.lower()

    def test_user_message_never_uses_bare_encountered_an_error_phrase(self) -> None:
        """Regression for the production-evidence pattern.

        The opaque 'Sorry, I encountered an error' phrasing is what we're
        REPLACING. None of the user messages should contain it.
        """
        for cls in ErrorClass:
            sample_exc = _make_exc(
                {
                    ErrorClass.TRANSIENT_LLM: "RateLimitError",
                    ErrorClass.TRANSIENT_API: "TimeoutException",
                    ErrorClass.VALIDATION: "ValueError",
                    ErrorClass.CONTENT_POLICY: "ContentPolicyViolationError",
                    ErrorClass.QUOTA: "AuthenticationError",
                    ErrorClass.UNKNOWN: "FooBar",
                }[cls]
            )
            result = classify_exception(sample_exc)
            lower = result.user_message.lower()
            assert "encountered an error" not in lower
            assert "i'm having trouble right now" not in lower

    def test_log_detail_truncates_very_long_messages(self) -> None:
        huge = "x" * 5000
        result = classify_exception(_make_exc("RateLimitError", huge))
        # 200-char body cap + class-name prefix + ": " separator
        assert len(result.log_detail) <= 250

    def test_log_detail_includes_exception_class_name(self) -> None:
        result = classify_exception(_make_exc("RateLimitError", "ratelimited"))
        assert "RateLimitError" in result.log_detail


# ---------------------------------------------------------------------------
# Returned dataclass is frozen + has expected fields
# ---------------------------------------------------------------------------


class TestReturnShape:
    def test_returns_classified_error_instance(self) -> None:
        result = classify_exception(_make_exc("RateLimitError", "x"))
        assert isinstance(result, ClassifiedError)

    def test_dataclass_is_frozen(self) -> None:
        result = classify_exception(_make_exc("RateLimitError", "x"))
        with pytest.raises((AttributeError, TypeError)):
            result.cls = ErrorClass.UNKNOWN  # type: ignore[misc]
