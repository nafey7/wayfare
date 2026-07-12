"""Shared utilities for V2 multi-agent graph modules.

Centralizes duplicated helpers (API key retrieval, checkpointer factory,
agent engine factory) that were previously copy-pasted across flight_graph.py,
hotel_graph.py, itinerary_graph.py, general_graph.py, and supervisor_v2.py.

Usage:
    from app.ai.graph.base import get_api_key, create_checkpointer, create_agent_engine
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRequest,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
    dynamic_prompt,
)
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth error types — shared between ModelRetryMiddleware (skip retry) and
# _dispatch_agent (user-friendly fallback).  Issue #808, Category 1.
# Lazily built: missing provider packages are silently skipped.
# ---------------------------------------------------------------------------
_auth_errors: list[type[Exception]] = []
try:
    from openai import AuthenticationError as _OAIAuthError

    _auth_errors.append(_OAIAuthError)
except ImportError:
    pass
try:
    from google.api_core.exceptions import Unauthenticated as _GoogleAuthError

    _auth_errors.append(_GoogleAuthError)
except ImportError:
    pass
# If neither provider is installed, this tuple is empty and the except clause
# catches nothing — auth errors fall through to the generic Exception handler.
_AUTH_ERRORS: tuple[type[Exception], ...] = tuple(_auth_errors)


def _should_retry_model_error(exc: Exception) -> bool:
    """Return True if the model error is transient and worth retrying.

    Auth errors (401 / invalid API key) are never retried — they propagate
    to ``_dispatch_agent``'s ``_AUTH_ERRORS`` handler for a user-friendly
    fallback message.
    """
    return not isinstance(exc, _AUTH_ERRORS)


@dataclass
class PromptContext:
    """Runtime context for dynamic prompt injection.

    Passed via ``context=PromptContext(prompt_fn=get_flight_prompt)`` at
    ``ainvoke`` time so the agent fetches a fresh prompt from Langfuse on
    every invocation instead of using the one baked in at compile time.
    """

    prompt_fn: Callable[[], str] = field(default=lambda: "You are a helpful assistant.")


@dynamic_prompt
def _resolve_dynamic_prompt(request: ModelRequest) -> str:
    """Middleware that resolves the system prompt at invocation time.

    Calls ``prompt_fn()`` from the runtime context, which fetches the latest
    prompt from Langfuse (with SDK-level 5-min cache + stale-while-revalidate).
    """
    return request.runtime.context.prompt_fn()


# 24-hour TTL for checkpoint documents (in seconds).
# Checkpoints are short-term conversation memory — with one chat per user,
# stale checkpoints from old conversations confuse agents on new queries.
# MongoDB's background TTL thread deletes expired documents automatically.
CHECKPOINT_TTL_SECONDS = 30 * 24 * 60 * 60  # 2_592_000 (30 days)


def get_api_key() -> str:
    """Get Google API key for LangChain.

    Checks GEMINI_API_KEY first, then GOOGLE_API_KEY.

    Returns:
        API key string

    Raises:
        ValueError: If no API key is configured
    """
    api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError(
            "No Gemini API key configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
        )
    return api_key


def create_checkpointer(
    collection_prefix: str,
) -> tuple[MongoDBSaver, "MongoClient[dict[str, Any]]"]:
    """Create a MongoDB checkpointer with named collections and TTL.

    Each agent uses a distinct collection prefix to avoid cross-agent
    checkpoint collision. A 24-hour TTL index is applied so MongoDB
    automatically removes expired checkpoint documents.

    Args:
        collection_prefix: Collection name prefix (e.g. "flight", "hotel",
            "supervisor_v2"). Produces "{prefix}_checkpoints" and
            "{prefix}_checkpoint_writes".

    Returns:
        Tuple of (MongoDBSaver, MongoClient) — caller must store both
        to prevent the client from being garbage-collected.
    """
    client: MongoClient[dict[str, Any]] = MongoClient(settings.MONGODB_URI)
    # Drop stale TTL indexes whose expireAfterSeconds differs from the
    # current CHECKPOINT_TTL_SECONDS — MongoDB rejects create_index when
    # an index with the same name but different options already exists.
    _reconcile_ttl_indexes(client, collection_prefix)
    checkpointer = MongoDBSaver(
        client,
        db_name=settings.DATABASE_NAME,
        checkpoint_collection_name=f"{collection_prefix}_checkpoints",
        writes_collection_name=f"{collection_prefix}_checkpoint_writes",
        ttl=CHECKPOINT_TTL_SECONDS,
    )
    # Backfill created_at on existing documents so the TTL index covers them.
    # Runs once per singleton init (cheap: only updates docs missing the field).
    _backfill_checkpoint_created_at(client, collection_prefix)

    logger.info(
        "Created MongoDB checkpointer '%s' (TTL=%dd) for database: %s",
        collection_prefix,
        CHECKPOINT_TTL_SECONDS // 86400,
        settings.DATABASE_NAME,
    )
    return checkpointer, client


def _reconcile_ttl_indexes(
    client: "MongoClient[dict[str, Any]]",
    collection_prefix: str,
) -> None:
    """Drop TTL indexes whose expireAfterSeconds doesn't match the current value.

    MongoDB refuses to create an index with the same key but different options.
    This runs once per singleton init so TTL changes deploy cleanly without
    manual index drops.
    """
    db = client[settings.DATABASE_NAME]
    for suffix in ("checkpoints", "checkpoint_writes"):
        coll_name = f"{collection_prefix}_{suffix}"
        try:
            for idx in db[coll_name].list_indexes():
                if idx.get("expireAfterSeconds") is not None:
                    existing_ttl = idx["expireAfterSeconds"]
                    if existing_ttl != CHECKPOINT_TTL_SECONDS:
                        logger.info(
                            "Dropping stale TTL index '%s' on %s (old=%ds, new=%ds)",
                            idx["name"],
                            coll_name,
                            existing_ttl,
                            CHECKPOINT_TTL_SECONDS,
                        )
                        db[coll_name].drop_index(idx["name"])
        except Exception:
            logger.warning(
                "Failed to reconcile TTL indexes on %s",
                coll_name,
                exc_info=True,
            )


def _backfill_checkpoint_created_at(
    client: "MongoClient[dict[str, Any]]",
    collection_prefix: str,
) -> None:
    """Add created_at to existing checkpoint docs that lack it.

    This is a one-time migration so MongoDB's TTL index can expire
    pre-existing documents. Safe to run repeatedly — only touches
    documents where created_at is missing.
    """
    db = client[settings.DATABASE_NAME]
    now = datetime.now(tz=UTC)

    for suffix in ("checkpoints", "checkpoint_writes"):
        coll = db[f"{collection_prefix}_{suffix}"]
        try:
            result = coll.update_many(
                {"created_at": {"$exists": False}},
                {"$set": {"created_at": now}},
            )
            if result.modified_count:
                logger.info(
                    "Backfilled created_at on %d docs in %s_%s",
                    result.modified_count,
                    collection_prefix,
                    suffix,
                )
        except Exception:
            logger.warning(
                "Failed to backfill created_at on %s_%s",
                collection_prefix,
                suffix,
                exc_info=True,
            )


def create_agent_engine(
    *,
    tools: list[Any],
    component: str = "agent_general",
    prompt_fn: Callable[[], str] | None = None,
    checkpointer: MongoDBSaver | None = None,
    state_schema: type | None = None,
    run_limit: int = 10,
    tool_call_limit: int = 30,
    temperature: float = 0.3,
    include_tool_retry: bool = True,
    dynamic_prompt_enabled: bool = False,
) -> Any:
    """Create a ReAct agent engine with standard middleware stack.

    Factory shared by all V2 specialist agents. Eliminates the duplicated
    _create_*_engine() functions across flight/hotel/itinerary/general graphs.

    Prompt modes:
    - **Static** (``prompt_fn`` provided, ``dynamic_prompt_enabled=False``):
      Prompt is resolved once at compile time. Used by V1 standalone agents.
    - **Dynamic** (``dynamic_prompt_enabled=True``):
      No prompt baked in at compile time.  Caller must pass
      ``context=PromptContext(prompt_fn=...)`` at ``ainvoke`` time so the
      ``@dynamic_prompt`` middleware fetches a fresh prompt from Langfuse
      on every invocation.

    Middleware stack (in order):
    0. dynamic_prompt — resolve system prompt at invocation time (dynamic mode only)
    1. ContextEditingMiddleware — clear old tool outputs when context grows large
    2. ModelRetryMiddleware — retry on transient Gemini API errors
    3. ModelFallbackMiddleware — fall back to flash model on persistent failure
    4. ToolRetryMiddleware — retry failed tool calls with backoff (optional)
    5. ToolCallLimitMiddleware — cap total tool executions per run
    6. ModelCallLimitMiddleware — prevent runaway agent loops

    Args:
        tools: List of LangChain tools for the agent
        prompt_fn: Callable that returns the formatted system prompt string.
            Required for static mode, ignored when dynamic_prompt_enabled=True.
        checkpointer: MongoDB checkpointer (None for stateless inner agents)
        state_schema: Optional state schema (V1 standalone agents only)
        run_limit: Max LLM invocations per agent turn (default 10)
        tool_call_limit: Max tool executions per agent turn (default 30)
        temperature: LLM temperature for main model (default 0.3)
        include_tool_retry: Whether to include ToolRetryMiddleware (default True)
        dynamic_prompt_enabled: If True, use @dynamic_prompt middleware instead
            of baking the prompt at compile time (default False)

    Returns:
        Compiled LangGraph agent
    """
    from app.ai.graph.llm_factory import create_fallback_llm, create_llm

    llm = create_llm(component, temperature=temperature)
    fallback_llm = create_fallback_llm(component, temperature=temperature)

    # NOTE: SummarizationMiddleware was evaluated (issue #808) but not needed.
    # The actual production crash was orphaned ToolMessages from windowing,
    # fixed by _strip_orphaned_tool_messages() in supervisor_v2.py.
    # Existing layers are sufficient for current conversation lengths:
    # - MAX_AGENT_HISTORY=20 windows recent messages per agent
    # - compact_tool_messages() compresses large tool outputs post-dispatch
    # - prune_old_messages() removes stale messages from checkpoints
    # - _strip_orphaned_tool_messages() removes orphaned ToolMessages
    # - shared_context preserves cross-agent data as structured state
    middleware: list[Any] = []
    if dynamic_prompt_enabled:
        # 0. Resolve system prompt dynamically at invocation time
        middleware.append(_resolve_dynamic_prompt)
    middleware.extend(
        [
            # 1. Clear old tool outputs when context grows large (keep last 3)
            ContextEditingMiddleware(
                edits=[ClearToolUsesEdit(keep=3)],
            ),
            # 2. Retry on transient Gemini API errors (rate limits, 503s).
            #    Auth errors are excluded — they never self-heal and must
            #    propagate to _dispatch_agent's _AUTH_ERRORS handler.
            ModelRetryMiddleware(
                max_retries=2,
                backoff_factor=2,
                retry_on=_should_retry_model_error,
                on_failure="error",
            ),
            # 3. Fall back to flash model if pro keeps failing
            ModelFallbackMiddleware(llm, fallback_llm),
        ]
    )
    if include_tool_retry:
        # 4. Retry failed tool calls with backoff
        middleware.append(ToolRetryMiddleware(max_retries=2, backoff_factor=2))
    # 5. Cap total tool executions per run
    middleware.append(ToolCallLimitMiddleware(run_limit=tool_call_limit))
    # 6. Prevent runaway agent loops
    middleware.append(ModelCallLimitMiddleware(run_limit=run_limit))

    kwargs: dict[str, Any] = {
        "model": llm,
        "tools": tools,
        "checkpointer": checkpointer,
        "middleware": middleware,
    }

    if dynamic_prompt_enabled:
        # Dynamic mode: prompt resolved at invocation time via PromptContext
        kwargs["context_schema"] = PromptContext
    elif prompt_fn is not None:
        # Static mode: prompt baked in at compile time
        kwargs["system_prompt"] = prompt_fn()
    else:
        raise ValueError("Either prompt_fn or dynamic_prompt_enabled must be set")

    if state_schema is not None:
        kwargs["state_schema"] = state_schema

    return create_agent(**kwargs)
