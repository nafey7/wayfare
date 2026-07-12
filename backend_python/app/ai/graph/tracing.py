"""Langfuse tracing for LangGraph agents.

This module provides callback handlers for LLM observability via Langfuse.
Enables tracing of all LLM calls, tool usage, and agent reasoning.

Uses custom message_id as seed for deterministic trace_id generation,
enabling frontend feedback correlation without exposing internal Langfuse IDs.

Usage:
    from app.ai.graph.tracing import generate_message_id, traced_observation

    message_id = generate_message_id()
    with traced_observation(message_id, chat_id, user_id) as (_, callbacks, metadata):
        config = {"configurable": {"thread_id": chat_id}, "callbacks": callbacks, "metadata": metadata}
        result = await graph.ainvoke(input_state, config)
    # Return message_id to frontend for feedback
"""

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import sentry_sdk

from app.ai.graph.cost_tracking import TokenUsageCollector
from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level flag to track if langfuse is available
_langfuse_available: bool | None = None
# Module-level Langfuse client for scoring
_langfuse_client: Any = None


def generate_message_id() -> str:
    """Generate a unique message ID for feedback tracking.

    This ID is used as seed for Langfuse trace_id generation,
    enabling deterministic correlation between frontend and backend.
    """
    return f"msg_{uuid.uuid4().hex[:16]}"


def _message_id_to_trace_id(message_id: str) -> str | None:
    """Convert message_id to Langfuse trace_id deterministically.

    Uses Langfuse.create_trace_id(seed=message_id) for consistent
    trace ID generation across requests.
    """
    try:
        from langfuse import Langfuse

        return Langfuse.create_trace_id(seed=message_id)
    except ImportError:
        logger.debug("Langfuse not installed, cannot create trace_id")
        return None
    except Exception as e:
        logger.warning(f"Failed to create trace_id from message_id: {e}")
        return None


@contextmanager
def traced_observation(
    message_id: str,
    session_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    name: str = "langgraph-agent",
) -> Generator[tuple[Any, list[Any], dict[str, Any]], None, None]:
    """Context manager for traced LangGraph invocation with custom message_id.

    Creates a Langfuse observation span with a deterministic trace_id derived
    from message_id. This enables frontend feedback correlation.

    Args:
        message_id: Custom message ID (returned to frontend for feedback)
        session_id: Chat/conversation ID for grouping traces
        user_id: User ID for associating traces
        user_email: User email for display in Langfuse UI
        name: Name for the trace (e.g., "flight-agent", "hotel-agent")

    Yields:
        Tuple of (langfuse_client, callbacks_list, trace_metadata) for use in graph.ainvoke()
        The trace_metadata dict should be merged into the config's metadata for proper
        trace attribution (contains langfuse_session_id, langfuse_user_id, langfuse_tags).

    Example:
        message_id = generate_message_id()
        with traced_observation(message_id, chat_id, user_id, name="flight-agent") as (lf, callbacks, metadata):
            config = {"configurable": {"thread_id": chat_id}, "callbacks": callbacks, "metadata": metadata}
            result = await graph.ainvoke(input_state, config)
    """
    global _langfuse_available

    if not settings.LANGFUSE_ENABLED:
        yield None, [], {}
        return

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning(
            "Langfuse enabled but API keys not configured. "
            "Set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY."
        )
        yield None, [], {}
        return

    if _langfuse_available is False:
        yield None, [], {}
        return

    try:
        from langfuse import Langfuse, get_client
        from langfuse.langchain import CallbackHandler

        _langfuse_available = True

        # Get or create Langfuse client
        langfuse = get_client()

        # Create deterministic trace_id from message_id
        trace_id = Langfuse.create_trace_id(seed=message_id)

        # Set Sentry context for error correlation with Langfuse traces
        sentry_sdk.set_tag("langfuse_trace_id", trace_id)
        sentry_sdk.set_tag("langfuse_message_id", message_id)
        sentry_sdk.set_context(
            "langfuse",
            {
                "trace_id": trace_id,
                "message_id": message_id,
                "session_id": session_id,
                "trace_url": f"{settings.LANGFUSE_BASE_URL}/trace/{trace_id}",
            },
        )

        # Create callback handler with trace_context (langfuse 3.x API)
        # The handler extracts session_id, user_id, tags from chain metadata
        # using langfuse_* prefixed keys
        handler = CallbackHandler(
            trace_context={"trace_id": trace_id},
        )

        # Per-turn token + cost accumulator (issue #1053 P0.4). Sits alongside
        # the Langfuse handler in the callbacks list; aggregates token usage
        # across every LLM call in the turn. Totals are submitted as Langfuse
        # NUMERIC scores in the finally block so they become filterable.
        cost_collector = TokenUsageCollector()

        # Build metadata dict with langfuse-specific keys for trace attributes
        # These will be extracted by the handler during chain execution
        trace_metadata: dict[str, Any] = {
            "message_id": message_id,
            "langfuse_session_id": session_id,
            "langfuse_user_id": user_id,
            "langfuse_tags": ["langgraph", name],
        }
        if user_email:
            trace_metadata["user_email"] = user_email

        logger.debug(
            "Langfuse trace started: message_id=%s, trace_id=%s, session_id=%s, user_id=%s",
            message_id,
            trace_id,
            session_id,
            user_id,
        )

        try:
            # Yield handler + cost collector. Caller passes the callbacks list
            # to graph.ainvoke; the cost_collector accumulates token usage as
            # langchain emits on_llm_end events.
            yield langfuse, [handler, cost_collector], trace_metadata
        finally:
            # Submit cost/token totals as Langfuse NUMERIC scores (issue #1053
            # P0.4). Best-effort: failure here must never affect the chat
            # response, hence the broad except.
            try:
                totals = cost_collector.totals()
                if totals["total_tokens"] > 0:
                    cost = cost_collector.cost_usd()
                    langfuse.create_score(
                        name="tokens_per_turn",
                        value=float(totals["total_tokens"]),
                        trace_id=trace_id,
                        data_type="NUMERIC",
                    )
                    if cost > 0:
                        langfuse.create_score(
                            name="cost_per_turn_usd",
                            value=cost,
                            trace_id=trace_id,
                            data_type="NUMERIC",
                        )
                    logger.debug(
                        "Cost tracking: trace_id=%s tokens=%d cost=$%.6f",
                        trace_id,
                        totals["total_tokens"],
                        cost,
                    )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Cost tracking submission failed (non-fatal)", exc_info=True
                )

            # Clear Sentry context to avoid leaking to other requests.
            # set_context's runtime accepts None to clear the context, but the
            # current sentry-sdk stubs require dict[str, Any]; ignore the
            # stub mismatch rather than overwrite-with-{} which is a different
            # semantic.
            sentry_sdk.set_tag("langfuse_trace_id", None)
            sentry_sdk.set_tag("langfuse_message_id", None)
            sentry_sdk.set_context("langfuse", None)  # type: ignore[arg-type]

    except ImportError:
        _langfuse_available = False
        logger.error(
            "Langfuse enabled but package not installed. Run: pip install langfuse"
        )
        yield None, [], {}
    except Exception as e:
        logger.error(f"Failed to create Langfuse observation: {e}")
        yield None, [], {}


def _get_langfuse_client() -> Any:
    """Get or create Langfuse client singleton for scoring."""
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client

    if not settings.LANGFUSE_ENABLED:
        return None

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse()
        logger.info("Langfuse client created for scoring")
        return _langfuse_client

    except ImportError:
        logger.error("Langfuse package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to create Langfuse client: {e}")
        return None


def submit_feedback_to_langfuse(
    message_id: str | None = None,
    session_id: str | None = None,
    feedback_type: str = "thumbs_up",
    comment: str | None = None,
) -> bool:
    """Submit user feedback to Langfuse as a score.

    Converts message_id to trace_id deterministically for precise correlation.
    Falls back to session_id if message_id not available.

    Args:
        message_id: Our custom message ID (converted to trace_id)
        session_id: Chat/conversation ID (fallback if message_id not available)
        feedback_type: "thumbs_up" or "thumbs_down"
        comment: Optional user comment

    Returns:
        True if feedback was submitted successfully
    """
    if not message_id and not session_id:
        logger.warning("Neither message_id nor session_id provided for feedback")
        return False

    client = _get_langfuse_client()
    if client is None:
        logger.warning("Langfuse client not available for feedback submission")
        return False

    try:
        # Convert feedback type to numeric value
        value = 1 if feedback_type == "thumbs_up" else 0

        # Build score kwargs - use create_score() API
        score_kwargs: dict[str, Any] = {
            "name": "user-feedback",
            "value": value,
            "data_type": "NUMERIC",
        }

        if comment:
            score_kwargs["comment"] = comment

        # Convert message_id to trace_id for precise correlation
        if message_id:
            trace_id = _message_id_to_trace_id(message_id)
            if trace_id:
                score_kwargs["trace_id"] = trace_id
                logger.debug(
                    f"Submitting feedback: message_id={message_id}, trace_id={trace_id}"
                )
            else:
                logger.warning(
                    f"Could not convert message_id to trace_id: {message_id}"
                )
                return False
        else:
            logger.warning("No message_id provided for feedback")
            return False

        # Use create_score() instead of score()
        client.create_score(**score_kwargs)
        client.flush()

        logger.info(f"Feedback submitted to Langfuse: {feedback_type} for {message_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to submit feedback to Langfuse: {e}")
        return False


def cleanup_langfuse() -> None:
    """Clean up Langfuse resources.

    Call this during application shutdown to flush any pending traces.
    """
    global _langfuse_client

    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            logger.info("Langfuse client flushed")
        except Exception as e:
            logger.warning(f"Error flushing Langfuse client: {e}")
        finally:
            _langfuse_client = None


__all__ = [
    "cleanup_langfuse",
    "generate_message_id",
    "submit_feedback_to_langfuse",
    "traced_observation",
]
