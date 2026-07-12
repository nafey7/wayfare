"""LangGraph general travel agent.

This module creates and manages the agent for general travel queries
(weather, visa, tips, greetings, destination advice).
Uses MongoDB checkpointer for conversation state persistence.
No tools in V1 — knowledge-based only.
"""

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.ai.graph.base import create_agent_engine, create_checkpointer
from app.ai.graph.tools import hand_back_to_supervisor, save_travel_context
from app.ai.graph.tracing import generate_message_id, traced_observation
from app.ai.graph.utils import (
    build_hand_back_response,
    detect_hand_back_tool,
    extract_last_ai_message,
)

logger = logging.getLogger(__name__)

# Module-level singletons
_general_checkpointer: MongoDBSaver | None = None
_general_mongo_client: MongoClient[dict[str, Any]] | None = None
_general_compiled_graph: Any = None
_general_inner_agent: Any = None


def _get_formatted_prompt() -> str:
    """Get the system prompt from Langfuse with fallback to hardcoded."""
    from app.ai.prompt_management import get_general_agent_prompt

    return get_general_agent_prompt()


_GENERAL_TOOLS = [hand_back_to_supervisor, save_travel_context]


def _create_general_engine(checkpointer: MongoDBSaver | None = None) -> Any:
    """Create general agent engine with static prompt (V1 standalone path)."""
    return create_agent_engine(
        tools=_GENERAL_TOOLS,
        component="agent_general",
        prompt_fn=_get_formatted_prompt,
        checkpointer=checkpointer,
        include_tool_retry=False,
    )


def get_general_inner_agent() -> Any:
    """Get stateless general agent engine for V2 supervisor (dynamic prompt).

    Uses ``dynamic_prompt_enabled=True`` so the system prompt is fetched fresh
    from Langfuse on every invocation via ``PromptContext``.
    """
    global _general_inner_agent
    if _general_inner_agent is None:
        logger.info("Creating stateless general inner agent for V2 supervisor")
        _general_inner_agent = create_agent_engine(
            tools=_GENERAL_TOOLS,
            component="agent_general",
            dynamic_prompt_enabled=True,
            include_tool_retry=False,
        )
    return _general_inner_agent


def get_general_graph() -> Any:
    """Get compiled general agent graph with MongoDB checkpointer (singleton).

    V1 path — standalone graph with its own checkpointer.
    """
    global _general_compiled_graph, _general_checkpointer, _general_mongo_client

    if _general_compiled_graph is None:
        logger.info("Creating general agent graph with MongoDB checkpointer")
        _general_checkpointer, _general_mongo_client = create_checkpointer("general")
        _general_compiled_graph = _create_general_engine(
            checkpointer=_general_checkpointer
        )

    return _general_compiled_graph


def process_general_messages(
    all_messages: list[Any],
    message_id: str = "",
) -> dict[str, Any]:
    """Process general agent messages into a response dict.

    Shared between V1 invoke_general_graph and V2 supervisor dispatch.
    Handles hand_back detection and AI response extraction.
    """
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        return build_hand_back_response(all_messages, hand_back, message_id)

    response_message = extract_last_ai_message(all_messages)

    if not response_message:
        response_message = (
            "I'd love to help with your travel plans! "
            "Could you tell me more about what you're looking for?"
        )

    return {
        "message": response_message,
        "type": "ai_response",
        "signal": "done",
        "done_reason": "query_answered",
        "message_id": message_id,
    }


async def invoke_general_graph(
    message: str,
    user_id: str,
    chat_id: str,
    user_email: str | None = None,
    intent_name: str = "general_query",
    is_detour: bool = False,
    context_hint: str | None = None,
) -> dict[str, Any]:
    """Invoke general agent graph and return response.

    Args:
        message: User's message text
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (used as thread_id for checkpointing)
        user_email: Optional user email for tracing
        intent_name: The detected intent name for tracing/analytics
        is_detour: If True, signal done after answering (triggers auto-return
            to previous agent). If False, signal needs_input for follow-ups.

    Returns:
        Dict with message, type, intent_name, message_id, response_time
    """
    graph = get_general_graph()
    message_id = generate_message_id()
    start_time = time.time()

    config: dict[str, Any] = {"configurable": {"thread_id": chat_id}}

    # context_hint (from supervisor on agent switch) is a SystemMessage so user
    # content cannot escape into the context bracket (prompt injection prevention).
    messages: list[Any] = []
    if context_hint:
        messages.append(SystemMessage(content=context_hint))
    messages.append(HumanMessage(content=message))
    input_state: dict[str, Any] = {
        "messages": messages,
    }

    logger.debug(
        "Invoking general graph for chat_id=%s, is_detour=%s, message=%s...",
        chat_id,
        is_detour,
        message[:50],
    )

    with traced_observation(
        message_id=message_id,
        session_id=chat_id,
        user_id=user_id,
        user_email=user_email,
        name="general-agent",
    ) as (_, callbacks, trace_metadata):
        if callbacks:
            config["callbacks"] = callbacks
        if trace_metadata:
            config["metadata"] = trace_metadata

        try:
            result = await graph.ainvoke(input_state, config)
        except Exception as e:
            logger.error("General graph invocation failed: %s", e, exc_info=True)
            return {
                "message": "I'd love to help with your travel question! Could you try asking again?",
                "type": "fallback_response",
                "intent_name": intent_name,
                "message_id": message_id,
                "response_time": time.time() - start_time,
            }

        all_messages = result.get("messages", [])
        response = process_general_messages(all_messages, message_id)
        response["intent_name"] = intent_name
        response["response_time"] = time.time() - start_time

        logger.debug(
            "General graph response for chat_id=%s: %s...",
            chat_id,
            response.get("message", "")[:100],
        )

        return response


def cleanup_general_graph() -> None:
    """Close MongoDB connection on shutdown."""
    global _general_checkpointer, _general_mongo_client, _general_compiled_graph

    if _general_mongo_client:
        _general_mongo_client.close()
        logger.info("General graph MongoDB connection closed")

    _general_checkpointer = None
    _general_mongo_client = None
    _general_compiled_graph = None
    # Note: _general_inner_agent is NOT cleaned up here — it has no DB connection


__all__ = [
    "cleanup_general_graph",
    "get_general_graph",
    "get_general_inner_agent",
    "invoke_general_graph",
    "process_general_messages",
]
