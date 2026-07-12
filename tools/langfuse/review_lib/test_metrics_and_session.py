"""Unit tests for metrics.py and session_analyzer.py pure-computation functions."""

import pytest

from .metrics import _percentile, is_error_trace
from .session_analyzer import _compute_frustration_score, _detect_retries, _mask_email


# ---------------------------------------------------------------------------
# _percentile
# ---------------------------------------------------------------------------

class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert _percentile([], 50) == 0.0

    def test_single_item(self):
        assert _percentile([5.0], 50) == 5.0
        assert _percentile([5.0], 95) == 5.0

    def test_p50_even_list(self):
        values = sorted([1.0, 2.0, 3.0, 4.0])
        result = _percentile(values, 50)
        assert 2.0 <= result <= 3.0

    def test_p95_typical(self):
        values = sorted(float(i) for i in range(1, 101))
        result = _percentile(values, 95)
        assert 94.0 <= result <= 96.0

    def test_p100_returns_max(self):
        values = sorted([1.0, 2.0, 10.0])
        assert _percentile(values, 100) == 10.0


# ---------------------------------------------------------------------------
# _mask_email
# ---------------------------------------------------------------------------

class TestMaskEmail:
    def test_standard_email(self):
        assert _mask_email("john@gmail.com") == "j***@gmail.com"

    def test_single_char_local(self):
        assert _mask_email("a@example.com") == "a***@example.com"

    def test_none_returns_unknown(self):
        assert _mask_email(None) == "unknown"

    def test_empty_string_returns_unknown(self):
        assert _mask_email("") == "unknown"

    def test_no_at_sign(self):
        assert _mask_email("notanemail") == "***"

    def test_multiple_at_signs(self):
        # split("@") gives 3 parts, len != 2
        assert _mask_email("a@b@c") == "***"


# ---------------------------------------------------------------------------
# _detect_retries
# ---------------------------------------------------------------------------

class TestDetectRetries:
    def test_empty_list(self):
        assert _detect_retries([]) == 0

    def test_single_message(self):
        assert _detect_retries(["hello"]) == 0

    def test_no_retries_different_messages(self):
        msgs = ["book a flight to Paris", "I want a hotel in London", "what is the weather"]
        assert _detect_retries(msgs) == 0

    def test_exact_duplicate_counts_as_retry(self):
        msgs = ["round trip ticket please", "round trip ticket please"]
        assert _detect_retries(msgs) == 1

    def test_high_overlap_counts_as_retry(self):
        msgs = ["I need a flight to New York", "I need a flight to New York please"]
        assert _detect_retries(msgs) == 1

    def test_low_overlap_not_retry(self):
        msgs = ["book flight", "cancel hotel reservation for next week"]
        assert _detect_retries(msgs) == 0


# ---------------------------------------------------------------------------
# _compute_frustration_score
# ---------------------------------------------------------------------------

class TestComputeFrustrationScore:
    def _make_trace(self, latency=5.0, has_error=False):
        return {
            "id": "trace-1",
            "latency": latency,
            "level": "ERROR" if has_error else "DEFAULT",
            "statusMessage": "",
            "output": {},
        }

    def test_frustration_keyword_adds_score(self):
        traces = [self._make_trace()]
        score, flags = _compute_frustration_score(
            traces, ["help me find a flight"], {},
            retry_count=0, completed=False,
        )
        # "help me" is a frustration keyword
        assert score > 0.0

    def test_no_signals_scores_zero(self):
        traces = [self._make_trace()]
        score, flags = _compute_frustration_score(
            traces, ["book Paris flight"], {},
            retry_count=0, completed=True,
        )
        assert score == 0.0
        assert flags == []

    def test_negative_feedback_adds_score(self):
        traces = [self._make_trace()]
        score_lookup = {"trace-1": [{"value": 0}]}
        score, flags = _compute_frustration_score(
            traces, ["ok"], score_lookup,
            retry_count=0, completed=False,
        )
        assert score >= 0.4
        assert any("negative_feedback" in f for f in flags)

    def test_high_latency_adds_score(self):
        traces = [self._make_trace(latency=75.0)]
        score, flags = _compute_frustration_score(
            traces, ["ok"], {},
            retry_count=0, completed=False,
        )
        assert score >= 0.1
        assert any("high_latency" in f for f in flags)

    def test_score_capped_at_one(self):
        # Trigger every signal at once: error + high latency + negative feedback + retries + keywords
        traces = [self._make_trace(latency=75.0, has_error=True)] * 10
        score_lookup = {"trace-1": [{"value": 0}]}  # matches _make_trace id="trace-1"
        msgs = ["try again"] * 5
        score, _ = _compute_frustration_score(
            traces, msgs, score_lookup,
            retry_count=3, completed=False,
        )
        assert score <= 1.0


# ---------------------------------------------------------------------------
# is_error_trace
# ---------------------------------------------------------------------------

class TestIsErrorTrace:
    def test_level_error(self):
        assert is_error_trace({"level": "ERROR", "statusMessage": "", "output": {}})

    def test_status_message_keyword(self):
        assert is_error_trace({"level": "DEFAULT", "statusMessage": "Request timeout", "output": {}})

    def test_clean_trace(self):
        assert not is_error_trace({"level": "DEFAULT", "statusMessage": "", "output": {}})

    def test_500_in_status(self):
        assert is_error_trace({"level": "DEFAULT", "statusMessage": "HTTP 500 error", "output": {}})

    def test_exception_in_status(self):
        assert is_error_trace({"level": "DEFAULT", "statusMessage": "Unhandled exception", "output": {}})
