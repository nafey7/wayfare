"""Paginated trace and score fetching for Langfuse."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Reuse utilities from the existing langfuse_traces.py
_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from langfuse_traces import api_request, load_env  # noqa: E402

# Project root for finding .env files
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MAX_PAGES = 100  # Safety cap: 100 pages * 100 per page = 10,000 traces max


def _load_dotenv(env_path: Path) -> None:
    """Load a .env file into os.environ (simple parser, no dependencies)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Only set if not already in environment (env vars take precedence)
        if key not in os.environ:
            os.environ[key] = value


def load_config() -> dict:
    """Load Langfuse credentials.

    Resolution order:
    1. .local/secrets/langfuse_prod (production credentials, highest priority)
    2. Environment variables (already set in shell)
    3. backend_python/.env file (local dev credentials, lowest priority)
    """
    # 1. Try prod secrets file first (always preferred for trace review)
    secrets_file = _PROJECT_ROOT / ".local" / "secrets" / "langfuse_prod"
    if secrets_file.exists():
        config: dict[str, str] = {}
        for line in secrets_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            config[key] = value
        if config.get("LANGFUSE_PUBLIC_KEY") and config.get("LANGFUSE_SECRET_KEY"):
            config.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
            return config

    # 2. Check environment variables
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        return {
            "LANGFUSE_PUBLIC_KEY": os.environ["LANGFUSE_PUBLIC_KEY"],
            "LANGFUSE_SECRET_KEY": os.environ["LANGFUSE_SECRET_KEY"],
            "LANGFUSE_BASE_URL": os.environ.get(
                "LANGFUSE_BASE_URL", "https://cloud.langfuse.com"
            ),
        }

    # 3. Fall back to backend_python/.env
    _load_dotenv(_PROJECT_ROOT / "backend_python" / ".env")
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        return {
            "LANGFUSE_PUBLIC_KEY": os.environ["LANGFUSE_PUBLIC_KEY"],
            "LANGFUSE_SECRET_KEY": os.environ["LANGFUSE_SECRET_KEY"],
            "LANGFUSE_BASE_URL": os.environ.get(
                "LANGFUSE_BASE_URL", "https://cloud.langfuse.com"
            ),
        }

    raise RuntimeError(
        "Langfuse credentials not found. Set LANGFUSE_PUBLIC_KEY + "
        "LANGFUSE_SECRET_KEY env vars or create .local/secrets/langfuse_prod"
    )


def fetch_traces_for_period(
    config: dict,
    days: int,
    tags: list[str] | None = None,
) -> list[dict]:
    """Fetch ALL production traces for a date range, paginating through all pages.

    Returns up to MAX_PAGES * 100 = 10,000 traces.
    """
    from_time = datetime.now(timezone.utc) - timedelta(days=days)
    params: dict = {
        "fromTimestamp": from_time.isoformat(),
        "limit": 100,
        "orderBy": "timestamp.DESC",
    }
    if tags:
        params["tags"] = tags

    all_traces: list[dict] = []
    page = 1

    while page <= MAX_PAGES:
        params["page"] = page
        try:
            result = api_request(config, "traces", params)
        except SystemExit:
            print(
                f"Warning: API error on page {page}, returning "
                f"{len(all_traces)} traces fetched so far",
                file=sys.stderr,
            )
            break

        traces = result.get("data", [])
        if not traces:
            break

        all_traces.extend(traces)
        meta = result.get("meta", {})
        total_pages = meta.get("totalPages", 1)

        if page >= total_pages:
            break
        page += 1

    return all_traces


def fetch_scores_for_period(config: dict, days: int) -> list[dict]:
    """Fetch all user-feedback scores for a date range."""
    from_time = datetime.now(timezone.utc) - timedelta(days=days)
    params: dict = {
        "name": "user-feedback",
        "fromTimestamp": from_time.isoformat(),
        "limit": 100,
    }

    all_scores: list[dict] = []
    page = 1

    while page <= MAX_PAGES:
        params["page"] = page
        try:
            result = api_request(config, "scores", params)
        except SystemExit:
            print(
                f"Warning: API error fetching scores on page {page}",
                file=sys.stderr,
            )
            break

        scores = result.get("data", [])
        if not scores:
            break

        all_scores.extend(scores)
        meta = result.get("meta", {})
        if page >= meta.get("totalPages", 1):
            break
        page += 1

    return all_scores


def fetch_trace_observations(config: dict, trace_id: str) -> list[dict]:
    """Fetch all observations (LLM calls, tool calls, spans) for a single trace."""
    all_obs: list[dict] = []
    page = 1
    while page <= 20:  # Safety cap
        try:
            result = api_request(config, "observations", {
                "traceId": trace_id,
                "page": page,
                "limit": 100,
            })
        except SystemExit:
            break
        obs = result.get("data", [])
        if not obs:
            break
        all_obs.extend(obs)
        meta = result.get("meta", {})
        if page >= meta.get("totalPages", 1):
            break
        page += 1
    return all_obs


def enrich_traces_with_observations(
    config: dict,
    sessions: list["SessionHealth"],
) -> None:
    """Fetch observations for all traces in flagged sessions and attach them.

    Modifies traces in-place by adding '_observations' key.
    This gives the LLM reviewer full context: tool calls, LLM reasoning, etc.
    """
    total = sum(s.trace_count for s in sessions)
    fetched = 0
    for session in sessions:
        for trace_detail in session.traces:
            fetched += 1
            print(
                f"\rFetching trace details... {fetched}/{total}",
                end="",
                file=sys.stderr,
            )
            trace_detail._observations = fetch_trace_observations(
                config, trace_detail.trace_id
            )
    if total:
        print(file=sys.stderr)


def group_traces_by_session(traces: list[dict]) -> dict[str, list[dict]]:
    """Group traces by sessionId."""
    sessions: dict[str, list[dict]] = {}
    for t in traces:
        sid = t.get("sessionId")
        if sid:
            sessions.setdefault(sid, []).append(t)
    return sessions


def build_score_lookup(scores: list[dict]) -> dict[str, list[dict]]:
    """Build a lookup from traceId -> list of scores."""
    lookup: dict[str, list[dict]] = {}
    for s in scores:
        tid = s.get("traceId")
        if tid:
            lookup.setdefault(tid, []).append(s)
    return lookup
