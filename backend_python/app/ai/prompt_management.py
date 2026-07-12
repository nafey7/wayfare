"""Langfuse Prompt Management Module.

This module provides centralized prompt retrieval from Langfuse with:
- SDK-level caching (5-minute TTL with stale-while-revalidate)
- Fallback to hardcoded prompts if Langfuse unavailable
- Dynamic variable injection (current_date, current_year, next_year)

Usage:
    from app.ai.prompt_management import get_flight_prompt, get_hotel_prompt, get_router_prompt

    # Get prompts with automatic caching and fallback
    flight_prompt = get_flight_prompt()
    hotel_prompt = get_hotel_prompt()
    router_prompt = get_router_prompt()

Author: Voya AI Team
Created: 2025-01-23
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level state
_langfuse_available: bool | None = None
# SDK cache TTL — Langfuse SDK handles caching with stale-while-revalidate
# (serves stale prompt instantly while fetching new version in background).
_sdk_cache_ttl: int = 300  # 5 minutes


def _check_langfuse_availability() -> bool:
    """Check if Langfuse is available and configured.

    Returns:
        True if Langfuse is available, False otherwise
    """
    global _langfuse_available

    if _langfuse_available is not None:
        return _langfuse_available

    if not settings.LANGFUSE_ENABLED:
        logger.debug("Langfuse disabled in settings")
        _langfuse_available = False
        return False

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning("Langfuse API keys not configured for prompt management")
        _langfuse_available = False
        return False

    try:
        from langfuse import get_client

        # Test client initialization
        get_client()
        logger.info("✅ Langfuse prompt management initialized")
        _langfuse_available = True
        return True

    except ImportError:
        logger.error("Langfuse package not installed")
        _langfuse_available = False
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse for prompt management: {e}")
        _langfuse_available = False
        return False


def _get_current_date_variables() -> dict[str, Any]:
    """Get current date variables for prompt compilation.

    Returns:
        Dict with current_date, current_year, next_year
    """
    from app.domains.common import utc_date

    today = utc_date()
    return {
        "current_date": today.isoformat(),
        "current_year": today.year,
        "next_year": today.year + 1,
    }


def _fetch_from_langfuse(
    prompt_name: str,
    label: str = "production",
) -> str | None:
    """Fetch prompt from Langfuse.

    Args:
        prompt_name: Name of the prompt in Langfuse
        label: Label to fetch (default: "production")

    Returns:
        Compiled prompt string or None if fetch failed
    """
    if not _check_langfuse_availability():
        return None

    try:
        from langfuse import get_client

        client = get_client()

        # Fetch prompt from Langfuse
        # SDK handles caching with stale-while-revalidate: serves cached
        # prompt instantly, refreshes in background when TTL expires.
        langfuse_prompt = client.get_prompt(
            prompt_name, label=label, cache_ttl_seconds=_sdk_cache_ttl
        )

        # Get date variables for compilation
        variables = _get_current_date_variables()

        # Compile prompt with variables
        compiled_prompt = langfuse_prompt.compile(**variables)

        # Planning, tool, intent recognizer, and general travel handler prompts: Convert double braces to single braces for Python .format()
        # After .compile(), unknown variables remain as {{variable}}
        # Convert {{origin}} -> {origin} so Python .format() can replace them
        if prompt_name.startswith(("voya-planning-", "voya-tool-")) or prompt_name in (
            "voya-intent-recognizer",
        ):
            compiled_prompt = compiled_prompt.replace("{{", "{").replace("}}", "}")
            logger.info(
                f"Fetched prompt from Langfuse (converted {{{{}}}} to {{}}): {prompt_name} (label: {label})"
            )
        else:
            logger.info(
                f"✅ Fetched prompt from Langfuse: {prompt_name} (label: {label})"
            )

        return compiled_prompt

    except Exception as e:
        logger.error(f"❌ Failed to fetch prompt from Langfuse: {prompt_name} - {e}")
        return None


def _get_fallback_prompt(prompt_name: str) -> str:
    """Get hardcoded fallback prompt.

    Args:
        prompt_name: Name of the prompt

    Returns:
        Hardcoded prompt string

    Raises:
        ValueError: If prompt_name is unknown
    """
    # Import hardcoded prompts as fallback
    from app.ai.graph.prompts import (
        FLIGHT_SYSTEM_PROMPT,
        GENERAL_AGENT_PROMPT,
        HOTEL_SYSTEM_PROMPT,
        ITINERARY_AGENT_PROMPT,
    )
    from app.ai.graph.prompts.itinerary_agent import (
        ITINERARY_CHUNK_FILL_PROMPT,
        ITINERARY_DAY_FILL_PROMPT,
        ITINERARY_GENERATION_PROMPT,
        ITINERARY_SKELETON_PROMPT,
    )
    from app.ai.graph.tools.dates import DATE_PARSE_PROMPT

    fallback_map = {
        "voya-flight-agent": FLIGHT_SYSTEM_PROMPT,
        "voya-general-agent": GENERAL_AGENT_PROMPT,
        "voya-hotel-agent": HOTEL_SYSTEM_PROMPT,
        "voya-itinerary-agent": ITINERARY_AGENT_PROMPT,
        "voya-planning-itinerary-generation": ITINERARY_GENERATION_PROMPT,
        "voya-planning-itinerary-skeleton": ITINERARY_SKELETON_PROMPT,
        "voya-planning-itinerary-day-fill": ITINERARY_DAY_FILL_PROMPT,
        "voya-planning-itinerary-chunk-fill": ITINERARY_CHUNK_FILL_PROMPT,
        "voya-tool-date-parse": DATE_PARSE_PROMPT,
    }

    # Lazy import to avoid circular dependency
    try:
        from app.ai.graph.prompts.supervisor_v2_agent import SUPERVISOR_V2_PROMPT

        fallback_map["voya-supervisor-v2-agent"] = SUPERVISOR_V2_PROMPT
    except ImportError:
        pass

    if prompt_name not in fallback_map:
        raise ValueError(f"Unknown prompt name: {prompt_name}")

    # Format hardcoded prompt with current date variables
    variables = _get_current_date_variables()

    # NOTE: Planning prompts, intent recognizer, and tool prompts use custom variables for string formatting
    # Don't pass date variables to them as they're formatted later with specific context
    if prompt_name.startswith(("voya-planning-", "voya-tool-")) or prompt_name in (
        "voya-intent-recognizer",
    ):
        # Planning prompts: formatted later with trip context (origin, destination, etc.)
        # Intent recognizer: formatted later with message and context
        # Tool prompts: formatted later with tool-specific variables (e.g., reference_date, text)
        fallback_prompt = fallback_map[prompt_name]
    else:
        # Agent prompts (flight, hotel, router): use date variables immediately
        fallback_prompt = fallback_map[prompt_name].format(**variables)

    logger.warning(f"⚠️ Using fallback prompt for: {prompt_name}")
    return fallback_prompt


def get_prompt(
    prompt_name: str,
    label: str = "production",
    force_refresh: bool = False,  # noqa: ARG001 — kept for API compatibility
) -> str:
    """Get prompt from Langfuse with SDK caching and fallback.

    Retrieval strategy:
    1. Fetch from Langfuse (SDK handles caching with stale-while-revalidate)
    2. Fallback to hardcoded prompt if Langfuse fails

    Args:
        prompt_name: Name of the prompt (e.g., "voya-flight-agent")
        label: Label to fetch (default: "production")
        force_refresh: If True, ignored (SDK cache_ttl handles freshness)

    Returns:
        Compiled prompt string ready for use

    Raises:
        ValueError: If prompt_name is unknown and fallback fails
    """
    # Step 1: Try fetching from Langfuse (SDK caches with 5-min TTL)
    langfuse_prompt = _fetch_from_langfuse(prompt_name, label)
    if langfuse_prompt:
        return langfuse_prompt

    # Step 2: Fallback to hardcoded prompt
    return _get_fallback_prompt(prompt_name)


def get_flight_prompt(label: str | None = None, force_refresh: bool = False) -> str:
    """Get flight agent system prompt from Langfuse.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Compiled flight agent prompt with current date variables
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-flight-agent", label, force_refresh)


def get_hotel_prompt(label: str | None = None, force_refresh: bool = False) -> str:
    """Get hotel agent system prompt from Langfuse.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Compiled hotel agent prompt with current date variables
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-hotel-agent", label, force_refresh)


def get_general_agent_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Get general agent system prompt from Langfuse.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Compiled general agent prompt with current date variables
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-general-agent", label, force_refresh)


def get_itinerary_agent_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Get itinerary agent system prompt from Langfuse.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Compiled itinerary agent prompt with current date variables
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-itinerary-agent", label, force_refresh)


def get_itinerary_generation_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Get planning agent itinerary generation prompt from Langfuse.

    Used in ROUTE_REFINEMENT stage to create day-by-day itinerary.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Itinerary generation prompt template with {origin}, {destination}, etc.
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-planning-itinerary-generation", label, force_refresh)


def get_itinerary_skeleton_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Stage-1 prompt for two-stage itinerary generation (#1053 Phase 4 O1).

    Produces day titles + descriptions + budget + experiences. NO activities.
    A separate per-day call (see :func:`get_itinerary_day_fill_prompt`) fills
    activities in parallel.
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-planning-itinerary-skeleton", label, force_refresh)


def get_itinerary_day_fill_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Stage-2 single-day prompt (kept for backward-compat). Production uses chunk."""
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-planning-itinerary-day-fill", label, force_refresh)


def get_itinerary_chunk_fill_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Stage-2 chunk prompt for two-stage itinerary generation (#1140).

    Fills activities for a GROUP of consecutive days in one LLM call.
    Always invoked exactly ``min(num_days, TWO_STAGE_PARALLEL_LIMIT)``
    times in parallel so Stage 2 finishes in one batch regardless of
    trip length.
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-planning-itinerary-chunk-fill", label, force_refresh)


def get_date_parse_prompt(label: str | None = None, force_refresh: bool = False) -> str:
    """Get date parsing LLM prompt from Langfuse.

    This prompt is used by the parse_dates tool to instruct Gemini on how to parse dates.
    Returns the template with {reference_date} and {text} placeholders.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Date parsing prompt template (NOT compiled - has {reference_date}, {text} placeholders)
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-tool-date-parse", label, force_refresh)


def get_supervisor_v2_prompt(
    label: str | None = None, force_refresh: bool = False
) -> str:
    """Get Supervisor V2 classification prompt from Langfuse.

    Args:
        label: Prompt label to fetch (default: from settings.LANGFUSE_PROMPT_LABEL)
        force_refresh: If True, bypass cache

    Returns:
        Supervisor V2 prompt formatted with current date variables
    """
    if label is None:
        label = settings.LANGFUSE_PROMPT_LABEL
    return get_prompt("voya-supervisor-v2-agent", label, force_refresh)


def invalidate_prompt_cache(prompt_name: str | None = None) -> None:
    """Invalidate prompt cache.

    With SDK-level caching, prompts auto-refresh after the TTL expires
    (stale-while-revalidate). This function is kept for API compatibility
    but is a no-op — restart the process to force immediate refresh.

    Args:
        prompt_name: Specific prompt to invalidate, or None for all
    """
    logger.info(
        "Prompt cache invalidation requested (prompt=%s). "
        "SDK uses stale-while-revalidate with %ds TTL — "
        "prompts will refresh automatically.",
        prompt_name or "all",
        _sdk_cache_ttl,
    )


__all__ = [
    "get_date_parse_prompt",
    "get_flight_prompt",
    "get_general_agent_prompt",
    "get_hotel_prompt",
    "get_itinerary_agent_prompt",
    "get_itinerary_chunk_fill_prompt",
    "get_itinerary_day_fill_prompt",
    "get_itinerary_generation_prompt",
    "get_itinerary_skeleton_prompt",
    "get_prompt",
    "get_supervisor_v2_prompt",
    "invalidate_prompt_cache",
]
