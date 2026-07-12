"""Quantitative per-agent metrics computation.

Pure computation on fetched data — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

AGENT_TAGS = [
    "supervisor-v2",
    "flight-agent",
    "hotel-agent",
    "itinerary-agent",
    "general-agent",
]

ERROR_KEYWORDS = ["error", "exception", "failed", "traceback", "timeout", "500"]


@dataclass
class AgentMetrics:
    agent_name: str
    total_traces: int = 0
    error_count: int = 0
    success_rate: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_max: float = 0.0
    avg_cost: float = 0.0
    total_cost: float = 0.0
    feedback_positive: int = 0
    feedback_negative: int = 0


@dataclass
class OverallMetrics:
    period_start: str = ""
    period_end: str = ""
    total_traces: int = 0
    total_sessions: int = 0
    unique_users: int = 0
    agents: dict[str, AgentMetrics] = field(default_factory=dict)
    total_cost: float = 0.0
    overall_error_rate: float = 0.0
    overall_success_rate: float = 0.0


def _percentile(sorted_values: list[float], p: int) -> float:
    """Compute percentile from a pre-sorted list. Pure Python."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[-1]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def is_error_trace(trace: dict) -> bool:
    """Detect if a trace represents an error."""
    if trace.get("level") == "ERROR":
        return True

    status = (trace.get("statusMessage") or "").lower()
    if any(kw in status for kw in ERROR_KEYWORDS):
        return True

    # Check output for error indicators in the first AI message
    output = trace.get("output")
    if isinstance(output, dict):
        messages = output.get("messages", [])
        for msg in messages:
            if msg.get("type") == "ai":
                content = msg.get("content", "")
                if isinstance(content, str) and "error" in content.lower()[:100]:
                    return True
    return False


def get_agent_tag(trace: dict) -> str | None:
    """Get the agent tag from a trace, excluding 'langgraph'."""
    for tag in trace.get("tags", []):
        if tag in AGENT_TAGS:
            return tag
    return None


def compute_agent_metrics(
    traces: list[dict],
    score_lookup: dict[str, list[dict]],
) -> dict[str, AgentMetrics]:
    """Compute per-agent metrics from traces and scores."""
    by_agent: dict[str, list[dict]] = {}
    for t in traces:
        agent = get_agent_tag(t)
        if agent:
            by_agent.setdefault(agent, []).append(t)

    result: dict[str, AgentMetrics] = {}

    for agent_name, agent_traces in by_agent.items():
        m = AgentMetrics(agent_name=agent_name)
        m.total_traces = len(agent_traces)

        # Errors
        m.error_count = sum(1 for t in agent_traces if is_error_trace(t))
        m.success_rate = (
            (m.total_traces - m.error_count) / m.total_traces * 100
            if m.total_traces > 0
            else 0.0
        )

        # Latency
        latencies = sorted(
            t["latency"] for t in agent_traces if t.get("latency") is not None
        )
        if latencies:
            m.latency_p50 = _percentile(latencies, 50)
            m.latency_p95 = _percentile(latencies, 95)
            m.latency_max = latencies[-1]

        # Cost
        costs = [t["totalCost"] for t in agent_traces if t.get("totalCost") is not None]
        if costs:
            m.total_cost = sum(costs)
            m.avg_cost = m.total_cost / len(costs)

        # Feedback
        for t in agent_traces:
            for score in score_lookup.get(t["id"], []):
                val = score.get("value")
                if val is not None:
                    if val >= 1:
                        m.feedback_positive += 1
                    else:
                        m.feedback_negative += 1

        result[agent_name] = m

    return result


def compute_overall_metrics(
    traces: list[dict],
    agent_metrics: dict[str, AgentMetrics],
    sessions: dict[str, list[dict]],
    period_start: str,
    period_end: str,
) -> OverallMetrics:
    """Compute overall metrics from all traces."""
    users = {t.get("userId") for t in traces if t.get("userId")}
    total_errors = sum(m.error_count for m in agent_metrics.values())
    total_traces = len(traces)

    return OverallMetrics(
        period_start=period_start,
        period_end=period_end,
        total_traces=total_traces,
        total_sessions=len(sessions),
        unique_users=len(users),
        agents=agent_metrics,
        total_cost=sum(m.total_cost for m in agent_metrics.values()),
        overall_error_rate=(
            (total_errors / total_traces * 100) if total_traces > 0 else 0.0
        ),
        overall_success_rate=(
            ((total_traces - total_errors) / total_traces * 100)
            if total_traces > 0
            else 0.0
        ),
    )
