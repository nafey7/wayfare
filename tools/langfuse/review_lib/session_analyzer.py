"""Session-level analysis with frustration detection.

Groups traces by session and scores each session for user frustration signals.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from langfuse_traces import extract_ai_response, extract_user_message  # noqa: E402

from .metrics import get_agent_tag, is_error_trace  # noqa: E402

# Keywords that suggest user frustration
FRUSTRATION_KEYWORDS = [
    "not working",
    "doesn't work",
    "doesn't work",
    "wrong",
    "broken",
    "try again",
    "still not",
    "why can't",
    "frustrated",
    "help me",
    "same thing",
    "already told you",
    "again",
    "stuck",
    "keeps",
    "impossible",
]

# Response types that indicate a completed action
ACTION_TYPES = [
    "flight_search_results",
    "hotel_search_results",
    "itinerary_results",
    "booking_confirmation",
]


@dataclass
class TraceDetail:
    """Details for a single trace within a session, for the report."""

    trace_id: str
    timestamp: str
    agent: str
    user_message: str
    ai_response: str
    latency: float | None
    cost: float | None
    is_error: bool
    has_negative_feedback: bool
    langfuse_url: str
    _observations: list | None = field(default=None, repr=False)


@dataclass
class SessionHealth:
    """Health assessment for a single session (conversation)."""

    session_id: str
    user_id: str | None
    user_email: str | None
    trace_count: int
    agents_used: list[str]
    total_latency: float
    had_errors: bool
    error_count: int
    had_negative_feedback: bool
    negative_feedback_count: int
    retry_count: int
    completed_action: bool
    frustration_score: float
    flags: list[str]
    traces: list[TraceDetail] = field(default_factory=list)
    severity: str = "low"  # low, medium, high


def _mask_email(email: str | None) -> str:
    """Mask email for privacy: john@gmail.com -> j***@gmail.com."""
    if not email:
        return "unknown"
    parts = email.split("@")
    if len(parts) != 2 or not parts[0]:
        return "***"
    return f"{parts[0][0]}***@{parts[1]}"


def _normalize_message(msg: str) -> str:
    """Normalize a message for comparison (lowercase, strip punctuation)."""
    return re.sub(r"[^\w\s]", "", msg.lower()).strip()


def _detect_retries(messages: list[str]) -> int:
    """Count queries that are semantically repeated.

    Uses word overlap: if two messages share >80% of words, it's a retry.
    """
    if len(messages) < 2:
        return 0

    normalized = [_normalize_message(m) for m in messages if m.strip()]
    retry_count = 0

    for i in range(1, len(normalized)):
        words_curr = set(normalized[i].split())
        if not words_curr:
            continue
        for j in range(i):
            words_prev = set(normalized[j].split())
            if not words_prev:
                continue
            overlap = len(words_curr & words_prev)
            max_len = max(len(words_curr), len(words_prev))
            if max_len > 0 and overlap / max_len > 0.8:
                retry_count += 1
                break  # Count each message as a retry at most once

    return retry_count


def _has_frustration_keywords(messages: list[str]) -> bool:
    """Check if any message contains frustration keywords."""
    combined = " ".join(messages).lower()
    return any(kw in combined for kw in FRUSTRATION_KEYWORDS)


def _check_completed_action(traces: list[dict]) -> bool:
    """Check if any trace output indicates a completed action."""
    for t in traces:
        output = t.get("output")
        if isinstance(output, dict):
            # Check for known action response types
            resp_type = output.get("type", "")
            if resp_type in ACTION_TYPES:
                return True
            # Check messages for structured results
            messages = output.get("messages", [])
            for msg in messages:
                if msg.get("type") == "ai":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        # Flight/hotel results usually contain these markers
                        if any(
                            marker in content.lower()
                            for marker in [
                                "found",
                                "results",
                                "here are",
                                "options",
                                "booked",
                                "confirmed",
                                "itinerary",
                            ]
                        ):
                            return True
    return False


def _compute_frustration_score(
    traces: list[dict],
    user_messages: list[str],
    score_lookup: dict[str, list[dict]],
    *,
    retry_count: int,
    completed: bool,
) -> tuple[float, list[str]]:
    """Compute frustration score (0.0-1.0) and list of flag reasons.

    retry_count and completed are passed in to avoid recomputing them
    (both are also needed by analyze_sessions).
    """
    score = 0.0
    flags: list[str] = []

    # Negative feedback
    neg_count = 0
    for t in traces:
        for s in score_lookup.get(t["id"], []):
            if s.get("value") is not None and s["value"] < 1:
                neg_count += 1
    if neg_count > 0:
        score += 0.4
        flags.append(f"negative_feedback ({neg_count}x)")

    # Errors
    error_count = sum(1 for t in traces if is_error_trace(t))
    if error_count > 0:
        score += 0.3
        flags.append(f"errors ({error_count}x)")

    # Retries
    if retry_count >= 2:
        score += 0.2
        flags.append(f"repeated_retries ({retry_count}x)")

    # Stuck in loop: many messages, no completed action
    if len(traces) > 8 and not completed:
        score += 0.3
        flags.append(f"no_completed_action ({len(traces)} messages)")

    # High latency
    max_latency = max(
        (t.get("latency") or 0 for t in traces),
        default=0,
    )
    if max_latency > 60:
        score += 0.1
        flags.append(f"high_latency ({max_latency:.0f}s)")

    # Frustration keywords
    if _has_frustration_keywords(user_messages):
        score += 0.2
        flags.append("frustration_keywords")

    return min(score, 1.0), flags


def _assign_severity(frustration_score: float, flags: list[str]) -> str:
    """Assign severity based on frustration score and flags."""
    if frustration_score >= 0.7:
        return "high"
    if frustration_score >= 0.4:
        return "medium"
    return "low"


def analyze_sessions(
    sessions: dict[str, list[dict]],
    score_lookup: dict[str, list[dict]],
    langfuse_base_url: str,
) -> tuple[list[SessionHealth], list[SessionHealth]]:
    """Analyze all sessions and return (all_sessions, flagged_sessions).

    A session is flagged if any of:
    - frustration_score > 0.3 (at least one signal)
    - has errors AND trace_count > 3 (persistent errors)
    - has negative feedback
    - retry_count > 2
    - >10 messages without any completed action
    """
    all_sessions: list[SessionHealth] = []
    flagged: list[SessionHealth] = []

    for session_id, traces in sessions.items():
        # Sort traces by timestamp
        traces.sort(key=lambda t: t.get("timestamp", ""))

        # Extract user info from first trace
        user_id = None
        user_email = None
        for t in traces:
            if t.get("userId"):
                user_id = t["userId"]
            if t.get("metadata") and isinstance(t["metadata"], dict):
                user_email = t["metadata"].get("user_email") or user_email

        # Gather user messages
        user_messages = [extract_user_message(t) for t in traces]
        user_messages = [m for m in user_messages if m.strip()]

        # Agents used
        agents = list({get_agent_tag(t) for t in traces if get_agent_tag(t)})

        # Compute shared values once (used by both frustration scoring and SessionHealth)
        retry_count = _detect_retries(user_messages)
        completed = _check_completed_action(traces)

        # Compute frustration
        frustration_score, flags = _compute_frustration_score(
            traces, user_messages, score_lookup,
            retry_count=retry_count, completed=completed,
        )

        # Count errors and negative feedback
        error_count = sum(1 for t in traces if is_error_trace(t))
        neg_feedback_count = 0
        for t in traces:
            for s in score_lookup.get(t["id"], []):
                if s.get("value") is not None and s["value"] < 1:
                    neg_feedback_count += 1

        # Total latency
        total_latency = sum(t.get("latency") or 0 for t in traces)

        # Build per-trace details
        trace_details: list[TraceDetail] = []
        for t in traces:
            trace_scores = score_lookup.get(t["id"], [])
            has_neg = any(
                s.get("value") is not None and s["value"] < 1 for s in trace_scores
            )
            trace_details.append(
                TraceDetail(
                    trace_id=t["id"],
                    timestamp=t.get("timestamp", ""),
                    agent=get_agent_tag(t) or "unknown",
                    user_message=extract_user_message(t),
                    ai_response=extract_ai_response(t),
                    latency=t.get("latency"),
                    cost=t.get("totalCost"),
                    is_error=is_error_trace(t),
                    has_negative_feedback=has_neg,
                    langfuse_url=f"{langfuse_base_url}/trace/{t['id']}",
                )
            )

        severity = _assign_severity(frustration_score, flags)

        session = SessionHealth(
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            trace_count=len(traces),
            agents_used=agents,
            total_latency=total_latency,
            had_errors=error_count > 0,
            error_count=error_count,
            had_negative_feedback=neg_feedback_count > 0,
            negative_feedback_count=neg_feedback_count,
            retry_count=retry_count,
            completed_action=completed,
            frustration_score=frustration_score,
            flags=flags,
            traces=trace_details,
            severity=severity,
        )
        all_sessions.append(session)

        # Flag the session if it has any signal
        is_flagged = (
            frustration_score > 0.3
            or (error_count > 0 and len(traces) > 3)
            or neg_feedback_count > 0
            or session.retry_count > 2
            or (len(traces) > 10 and not completed)
        )
        if is_flagged:
            flagged.append(session)

    # Sort flagged by severity (high first) then frustration score
    severity_order = {"high": 0, "medium": 1, "low": 2}
    flagged.sort(
        key=lambda s: (severity_order.get(s.severity, 3), -s.frustration_score)
    )

    return all_sessions, flagged
