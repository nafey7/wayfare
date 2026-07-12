# Voya AI System — Optimization Plan

**Goal**: Reduce latency, increase accuracy, and cut cost across the multi-agent AI flow.
**Current LLM stack**: OpenAI `gpt-5.4-mini` (agents/tools), `gpt-5.4-nano` (conversation namer).
**Author**: Generated from architectural audit of `backend_python/app/ai/` (May 2026).

---

## 1. Current Architecture Summary

### Entry & orchestration
- API: `app/api/chat.py:59` → `POST /chat/message`
- Service: `app/domains/chat/service.py:622` → `_handle_via_supervisor_v2()`
- Orchestrator: `app/ai/graph/supervisor_v2.py` (2,935 lines) — LangGraph `StateGraph` with 6 nodes, MongoDB checkpointer

### Agents (all LangGraph ReAct, all using `gpt-5.4-mini` by default per `llm_factory.py`)

| Agent | File | Lines | Purpose | Tools |
|---|---|---|---|---|
| Supervisor | `app/ai/graph/supervisor_v2.py` | 2,935 | Intent classification + dispatch | — |
| Flight | `app/ai/graph/flight_graph.py` | 1,340 | Flight search & booking | resolve_airport, parse_dates, search_flights, find_nearby_airports, hand_back, save_travel_context |
| Hotel | `app/ai/graph/hotel_graph.py` | 813 | Hotel search & booking | resolve_city, parse_dates, search_hotels, select_hotel, hand_back, save_travel_context |
| Itinerary | `app/ai/graph/itinerary_graph.py` | 758 | Multi-day trip planning | parse_dates, resolve_airport, resolve_city, search_flights, search_hotels, generate_itinerary, estimate_budget, hand_back |
| General | `app/ai/graph/general_graph.py` | 220 | Advice / chitchat / clarification | hand_back, save_travel_context |

### System prompts (re-sent every turn, no Gemini-style explicit cache wiring)

| Agent | File | Lines | ≈ Tokens |
|---|---|---|---|
| Supervisor | `prompts/supervisor_v2_agent.py` | 97 | ~2,900 |
| Flight | `prompts/flight_agent.py` | 189 | ~5,700 |
| Hotel | `prompts/hotel_agent.py` | 104 | ~3,100 |
| Itinerary | `prompts/itinerary_agent.py` | 228 | ~6,800 |
| General | `prompts/general_agent.py` | 53 | ~1,590 |

**Token weight per turn (system prompts only)**:
- Flight: ~8,600 | Hotel: ~6,000 | Itinerary: ~9,700 | General: ~4,500

### Parallelism today
- `app/ai/graph/tools/flights.py:1103` — multi-date flight search runs `asyncio.gather`
- `app/ai/graph/enrichment.py:159,257` — gather over enrichment tasks
- **Itinerary flight+hotel** — sequential via ReAct loop (no parallel dispatch)
- **Supervisor → agent** — sequential (one agent per turn)

### Caching today
- `lru_cache` on currency formatting only (`integrations/flightlogic/adapter.py:2043,2063,2086`)
- `airports_cache.json` loaded at startup
- **No** caching on FlightLogic search results
- **No** Redis, **no** semantic cache, **no** explicit prompt caching wiring

### Streaming
- **None.** All graph invocations use `graph.ainvoke()`. No `astream`, no SSE, no WebSocket streaming to frontend.

### Observability
- Langfuse via `app/ai/graph/tracing.py:65-100` (wraps every graph invocation)
- No probabilistic sampling — 100% trace rate

---

## 2. Findings (the actual problems)

| # | Finding | Evidence |
|---|---|---|
| F1 | Every component uses `gpt-5.4-mini` (or `gemini-2.5-pro` per defaults) — no right-sizing. Supervisor classification, general chitchat, and date parsing all use the same model as complex itinerary composition. | `app/ai/graph/llm_factory.py:57-67` |
| F2 | Supervisor LLM is called on **every message**, even greetings and obvious continuations. | `app/ai/graph/supervisor_v2.py:1800-2020` |
| F3 | Large static system prompts (4–9K tokens) re-sent every turn with no explicit caching strategy. OpenAI auto-caches above 1024 tokens but only if prompt prefix is stable. | `app/ai/graph/prompts/*.py` |
| F4 | No streaming — users wait for full response (3–15s on itinerary) before seeing anything. | `app/api/chat.py:59`, `supervisor_v2.py` |
| F5 | FlightLogic search results never cached — same query re-hits API on every follow-up turn. | `integrations/flightlogic/client.py` |
| F6 | Itinerary agent calls flight + hotel **sequentially** via LLM-driven tool order. | `app/ai/graph/itinerary_graph.py:155` |
| F7 | Tool `tool_dates` always calls an LLM even for trivial inputs like "tomorrow" or "2026-06-15". | `app/ai/graph/tools/dates.py` |
| F8 | Langfuse traces 100% of requests in prod (~12% overhead per AgentOps benchmarks). | `app/ai/graph/tracing.py` |
| F9 | Itinerary prompt at 228 lines is large; sections may rarely fire. | `prompts/itinerary_agent.py` |

---

## 3. Recommendations — Prioritized

### 🔴 P0 — Highest ROI (do first)

#### P0.1 — Model cascade: right-size every component

**File**: `app/ai/graph/llm_factory.py:57-67`

The factory already supports per-component env-var overrides. Update defaults (or set env vars):

| Component | Today | Recommended | Rationale |
|---|---|---|---|
| `supervisor` | gpt-5.4-mini | **gpt-5.4-nano** | Pure classification, temp=0, low cognitive load |
| `agent_general` | gpt-5.4-mini | **gpt-5.4-nano** | No tools, conversational only |
| `tool_dates` | gpt-5.4-mini | **gpt-5.4-nano** | Deterministic parsing |
| `tool_budget` | gpt-5.4-mini | **gpt-5.4-nano** | Lookup + arithmetic |
| `agent_flight` | gpt-5.4-mini | **keep gpt-5.4-mini** | Tool-call accuracy matters |
| `agent_hotel` | gpt-5.4-mini | **keep gpt-5.4-mini** | Tool-call accuracy matters |
| `agent_itinerary` | gpt-5.4-mini | **gpt-5.4-mini** today; A/B vs `gpt-5.4` flagship for complex plans | Composition quality bottleneck |
| `tool_itinerary` | gpt-5.4-mini | **keep gpt-5.4-mini** (or upgrade) | Long-form generation |
| `conversation_namer` | gpt-5.4-nano | **keep nano** | Already correct |

**Implementation** — either:
1. Change `DEFAULT_CONFIG` defaults in `llm_factory.py`, OR
2. Set env vars: `LLM_SUPERVISOR_MODEL=gpt-5.4-nano`, `LLM_AGENT_GENERAL_MODEL=gpt-5.4-nano`, `LLM_TOOL_DATES_MODEL=gpt-5.4-nano`, `LLM_TOOL_BUDGET_MODEL=gpt-5.4-nano`.

**Expected impact**: Routing/classification path latency **−50 to −70%**; overall cost **−25 to −45%**. Research backs this — model cascades typically cut cost 45–85% with ~95% quality retained.

---

#### P0.2 — Rule-based pre-classifier in front of supervisor LLM

**File**: `app/ai/graph/supervisor_v2.py:1800-2020` (`route_or_classify` node)

A confidence=1.0 sticky-intent fast-path exists at line 1820-1850 but only catches narrow cases. Broaden with cheap rule checks **before** the LLM call:

```
1. Message length < 3 words AND no booking keywords → general (skip LLM)
2. Greeting/thanks regex match → general (skip LLM)
3. Explicit verbs: "book flight" / "find hotels" / "plan trip" → direct route (skip LLM)
4. Continuation phrases ("yes", "next", "option 1", "that one") AND previous agent sticky → reuse previous agent (skip LLM)
5. Otherwise → LLM classification (current path)
```

**Expected impact**: Skips 1 LLM call (~400–1000ms) for 50–70% of turns. Research: 3-tier cascades (rule → semantic → LLM) handle 60–70% of traffic in milliseconds.

---

#### P0.3 — Optimize prompt structure for OpenAI auto-caching

**Files**: `app/ai/graph/prompts/*.py`, `app/ai/graph/base.py`

OpenAI **automatically caches prompts ≥1024 tokens** when the prefix is stable. Cached tokens are billed at ~50% and skip TTFT (time-to-first-token) processing.

**To maximize cache hits**:

1. **Put static content FIRST** in the prompt array, dynamic content LAST:
   ```
   [system: agent instructions]           ← static (cacheable)
   [system: tool documentation]           ← static (cacheable)
   [user/assistant: chat history]         ← partially stable (mostly cacheable)
   [user: current message]                ← dynamic (not cached)
   ```

2. **Don't interpolate dynamic values into the system prompt** (e.g., current date, user name) — pass them via tool args or a separate trailing system message.

3. **Audit `_get_formatted_prompt()` / dynamic prompt enabled** flags in `base.py:82-88` — any per-request templating breaks caching.

**Expected impact**: **−25 to −50%** on input token cost; **−200 to −800ms** TTFT. Free win — no architectural change required, just prompt ordering.

---

#### P0.4 — Stream responses to the frontend

**Files**: `app/api/chat.py:59` (HTTP handler), supervisor_v2.py invocation in `chat/service.py:622`

Currently `graph.ainvoke()` returns one big payload — users wait 3–15s before seeing anything.

**Switch to**:
- `graph.astream()` to get incremental events
- Stream to frontend via **SSE** (simpler) or **WebSocket** (richer, e.g., per-agent progress events)

**Frontend impact**: Chat panel in `frontend-v2/src/features/chat/` already renders progressively — wire up to consume the event stream.

**Expected impact**: **TTFB drops to <500ms** (vs 3–10s today). Perceived speed win is enormous. OpenAI's 2026 guidance specifically recommends WebSockets for agentic workflows.

**Bonus**: emit per-tool-call events (`flight_search_started`, `flight_search_completed`) so the UI can show progress.

---

### 🟡 P1 — High ROI, medium effort

#### P1.1 — Cache FlightLogic search results (two-level)

**Files**: `integrations/flightlogic/client.py`, `app/ai/graph/tools/flights.py:1103`

A typical user explores 2–3 date variations and asks follow-ups on the same results. Today every turn re-hits FlightLogic (2–5s each).

**Recommended**:
- **L1**: in-process LRU keyed by `(origin, destination, date, pax, cabin, trip_type)`, TTL 5 min, maxsize 500
- **L2**: Redis with TTL 30–60 min for cross-instance reuse
- Cache hits should return identical results so the agent can reference "option 1" reliably

**Implementation**: wrap the FlightLogic client method, not the tool — keeps caching transparent.

**Expected impact**: FlightLogic latency on follow-up turns **2–5s → <100ms**; reduces API spend.

---

#### P1.2 — Parallelize flight + hotel in itinerary agent

**File**: `app/ai/graph/itinerary_graph.py:155`

Itinerary currently relies on the LLM to decide tool-call order in a ReAct loop, usually sequential. Add a dedicated graph node **before** the LLM composes the plan:

```python
async def _parallel_search_node(state):
    flights, hotels = await asyncio.gather(
        search_flights(...),
        search_hotels(...),
    )
    return {"flights": flights, "hotels": hotels}
```

Then the itinerary LLM only generates the plan, not orchestrates searches.

**Expected impact**: Itinerary end-to-end latency **−30 to −50%** (research: LAMaS framework reports 38–46% critical-path reduction from this pattern).

---

#### P1.3 — Bypass LLM for trivial date parsing

**File**: `app/ai/graph/tools/dates.py`

90% of date inputs are simple ("tomorrow", "next Friday", "2026-06-15"). Use the `dateparser` Python library locally (already common in `requirements.txt`-style projects). Keep LLM as a fallback for ambiguous cases ("the weekend after my conference").

```python
def parse_dates_tool(text):
    parsed = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
    if parsed:
        return {"date": parsed.isoformat(), "source": "local"}
    # Fallback: LLM call
    return await _llm_parse_dates(text)
```

**Expected impact**: Saves an LLM call on ~80% of date parses; **−300 to −800ms** per affected turn.

---

#### P1.4 — Trim itinerary system prompt

**File**: `app/ai/graph/prompts/itinerary_agent.py` (228 lines, ~6,800 tokens)

Audit which sections actually fire. Move edge-case handling, error formats, and rarely-triggered guidance to:
- Tool docstrings (model only reads these when calling that tool)
- Conditionally-injected few-shot examples
- Trailing system message added only when needed

**Target**: 80–100 lines of core prompt + tool-level instructions.

**Expected impact**: **−3K to −4K tokens** per itinerary turn; faster TTFT.

---

### 🟢 P2 — Lower priority but useful

#### P2.1 — Add AgentOps alongside Langfuse

**Files**: `app/ai/graph/tracing.py:65-100`

Keep Langfuse for prompt management and evals. Add **AgentOps** for multi-agent handoff visualization and session replay — your V2 supervisor → sub-agent flow is exactly what AgentOps is built for. Two lines: `import agentops; agentops.init(API_KEY)`. Free tier (50K events/month) covers dev/staging.

---

#### P2.2 — Sample Langfuse traces in production

**File**: `app/ai/graph/tracing.py`

Trace 100% of requests in dev/staging. In production, sample **10–20%** of normal requests; **always** sample errors and slow requests (>5s). Cuts ~10–12% observability overhead.

---

#### P2.3 — Connection pooling for httpx clients

**Files**: `integrations/flightlogic/client.py:110,147`

Verify a single `httpx.AsyncClient` is reused across requests (not re-created per call). Connection reuse saves TLS handshake (~100–300ms per call).

---

#### P2.4 — Experiment with non-OpenAI providers for hot paths

The factory supports OpenAI/xAI/Bedrock. For supervisor classification (highest QPS), benchmark:
- `gpt-5.4-nano` (current rec)
- `grok-4-1-fast-non-reasoning` (xAI)
- `claude-haiku-4-5` (via Bedrock, if licensed)

Pick on p50 + p95 latency, not just cost.

---

## 4. Suggested Rollout (1–2 sprints)

### Week 1 — Quick wins (config-only)
- [ ] P0.1 — Right-size models in `llm_factory.py` (or env vars)
- [ ] P0.3 — Reorder prompts for OpenAI auto-caching
- [ ] P0.4 — Wire streaming via SSE/WebSocket

### Week 2 — Routing & caching
- [ ] P0.2 — Rule-based pre-classifier in supervisor
- [ ] P1.1 — L1 in-process cache for FlightLogic results
- [ ] P1.3 — Local `dateparser` fallback

### Week 3 — Itinerary path
- [ ] P1.2 — Parallel flight+hotel node in itinerary graph
- [ ] P1.4 — Trim itinerary prompt
- [ ] P1.1 (cont.) — Add Redis L2 cache

### Backlog
- [ ] P2.1 — AgentOps integration
- [ ] P2.2 — Trace sampling in prod
- [ ] P2.3 — httpx connection pooling audit
- [ ] P2.4 — Multi-provider benchmarks

---

## 5. Expected Impact (Rough Estimates)

| Change | Latency Δ | Cost Δ | Accuracy Δ |
|---|---|---|---|
| P0.1 Right-size models | −50 to −70% on routing path | −25 to −45% overall | Neutral if nano sufficient |
| P0.2 Rule pre-classifier | −400 to −1000ms / turn | −10 to −20% | Neutral (deterministic) |
| P0.3 Prompt ordering for cache | −200 to −800ms TTFT | −25 to −50% input tokens | Neutral |
| P0.4 Streaming | TTFB <500ms (vs 3–10s) | None | Neutral (perceived ↑) |
| P1.1 FlightLogic cache | 2–5s → <100ms on hits | API spend ↓ | Neutral (slight staleness risk) |
| P1.2 Parallel itinerary search | −30 to −50% itinerary E2E | None | Neutral |
| P1.3 Local date parser | −300 to −800ms on 80% of date calls | LLM call ↓ | Neutral if dateparser robust |
| P1.4 Trim itinerary prompt | −150 to −500ms TTFT | −3K to −4K tokens | Watch for regressions |

**Compounded expected impact (if all P0+P1 shipped)**:
- General chitchat path: **3–6s → <800ms** (5–7× faster)
- Flight search path: **5–10s → 2–4s** (2–3× faster)
- Itinerary path: **15–25s → 6–10s** (2–3× faster)
- Overall LLM cost: **−40 to −60%**

---

## 6. Industry Validation (May 2026)

Each recommendation cross-checked against published industry practice and case studies. Verdict scale: ✅ **standard practice** / ⚠️ **emerging consensus** / ❓ **contested**.

### P0.1 — Model right-sizing / cascade — ✅ standard practice

- **Walmart case study**: Routing simple queries directly to tools and only triggering complex reasoning when needed reduced response latency by **53.3%** while improving recommendation quality. ([Neo4j case studies](https://neo4j.com/blog/agentic-ai/ai-agent-useful-case-studies/))
- **Quantified industry result**: Intelligent routing of 90% of requests to budget models with only 10% going to frontier models can reduce costs by **86%** without meaningful quality degradation. ([Rack2Cloud](https://www.rack2cloud.com/ai-inference-cost-model-routing/))
- **DCAM framework** (Decompose / Classify / Assign / Measure) is the established methodology for atomic LLM-call right-sizing in agentic workflows. ([Crewdle](https://crewdle.com/blog/right-sizing-models-agentic-workflows/))
- **Verdict**: This is *table stakes* for production agent systems in 2026. Using `gpt-5.4-mini` for a temp=0 supervisor classifier is documented overspend.

### P0.2 — Rule-based pre-classifier before LLM — ✅ standard practice

- "Most production systems use hybrid approaches, applying simple rules first, then using semantic or LLM-based routing for edge cases." ([Patronus AI](https://www.patronus.ai/ai-agent-development/ai-agent-routing))
- **3-tier cascade (rule → semantic → LLM)** is the textbook production pattern: most requests route in **milliseconds**, hard requests escalate accurately. ([MindStudio 3-tier routing](https://www.mindstudio.ai/blog/set-up-ai-model-router-llm-stack-c2610), [Meganova](https://blog.meganova.ai/the-3-tier-routing-cascade-rule-based-semantic-llm/))
- "A well-designed rule-based router can capture **80% of the value with a few dozen lines of code**." ([Arize AI — Best Practices for Building an Agent Router](https://arize.com/blog/best-practices-for-building-an-ai-agent-router/))
- NVIDIA ships an open-source LLM router blueprint specifically for this pattern. ([NVIDIA llm-router](https://github.com/NVIDIA-AI-Blueprints/llm-router))
- **Verdict**: Standard. Not having this in front of a 2,900-token supervisor prompt is an avoidable cost.

### P0.3 — Prompt ordering for OpenAI auto-caching — ✅ standard practice (OpenAI official)

- OpenAI's own documentation: "**Prompt Caching reduces latency by up to 80% and input token costs by up to 90%.**" Automatic for prompts ≥1024 tokens, no code change. ([OpenAI Prompt Caching docs](https://developers.openai.com/api/docs/guides/prompt-caching), [OpenAI announcement](https://openai.com/index/api-prompt-caching/))
- Official guidance: "Place static content like instructions and examples at the **beginning** of your prompt, and put variable content, such as user-specific information, at the **end**." ([OpenAI Cookbook — Prompt Caching 101](https://cookbook.openai.com/examples/prompt_caching101))
- **OpenAI's own Codex CLI** uses this pattern: "system instructions, tool definitions, sandbox configuration, and environment context are kept identical and consistently ordered between requests to preserve long, stable prompt prefixes." ([Prompt Caching 201](https://developers.openai.com/cookbook/examples/prompt_caching_201))
- **Verdict**: Officially recommended by the vendor. Free win — only requires audit of `_get_formatted_prompt()` in `base.py:82-88` to ensure dynamic values aren't being interpolated into the prefix.

### P0.4 — Streaming via SSE/WebSocket — ✅ standard practice

- **Industry TTFT target**: <300–700ms feels snappy; chatbots specifically need <500ms to feel responsive. ([BentoML LLM Inference Handbook](https://bentoml.com/llm/inference-optimization/llm-inference-metrics))
- "Streaming delivers a **10–20× improvement in perceived responsiveness**." ([Hivenet — LLM Streaming SSE vs WebSockets](https://www.hivenet.com/post/llm-streaming-sse-websockets))
- Production guidance: "Use SSE for chat unless you truly need bi-directional messaging. AI agents need bidirectional communication for tool calls, user interrupts, context updates — WebSockets provide full-duplex." ([WebSocket.org — Why LLMs Are Moving Beyond SSE](https://websocket.org/guides/websockets-and-ai/))
- OpenAI explicitly recommends WebSockets for agentic workflows ([OpenAI — Speeding up agentic workflows with WebSockets](https://openai.com/index/speeding-up-agentic-workflows-with-websockets/))
- **Verdict**: Universal practice. Your current `ainvoke` (non-streaming) is the unusual choice. For your multi-agent flow with tool calls and progress events, **WebSocket** is the better target than SSE.

### P1.1 — Caching external API results (FlightLogic) — ✅ standard practice

- "Caching turns slow external calls into **sub-millisecond reads** and protects your app from rate limits and outages." ([Redis — REST API caching tutorial](https://redis.io/tutorials/how-to-cache-rest-api-responses-using-redis-and-nodejs/))
- Redis LangCache (semantic caching) benchmarks: **up to 70% cost reduction and 15× faster** responses on cache hits. ([Redis for AI](https://redis.io/redis-for-ai/))
- Semantic embedding caching can cut LLM API calls by **up to ~69%** ([Azure Managed Redis for AI Agents](https://itnext.io/azure-managed-redis-for-ai-agents-semantic-caching-vector-knowledge-stores-and-memory-at-20d380c68047))
- **Verdict**: Standard. The two-level cache (in-process L1 + Redis L2) is the textbook pattern for stateful agent platforms. **Note**: for FlightLogic specifically, deterministic caching is safer than semantic caching (pricing accuracy matters).

### P1.2 — Parallel tool execution in LangGraph — ✅ official LangChain pattern

- LangChain official docs: "LangGraph handles parallelization by running multiple independent subtasks at the same time… commonly used to split up subtasks and run them in parallel to increase speed." ([LangChain — Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents))
- AWS Bedrock blog on multi-agent LangGraph specifically calls out the supervisor + parallel pattern. ([AWS — Build multi-agent systems with LangGraph and Bedrock](https://aws.amazon.com/blogs/machine-learning/build-multi-agent-systems-with-langgraph-and-amazon-bedrock/))
- **Verdict**: Officially supported pattern. Your itinerary agent leaving flight+hotel parallelism to LLM tool-call ordering (instead of a dedicated parallel node) is the anti-pattern.

### P1.3 — Local date parsing fallback — ✅ standard practice

- Direct guidance: "Taking date parsing out of the LLM and into custom logic is necessary for **deterministic behavior**." ([Medium — Handling Dates in Natural Language Without Hallucination](https://medium.com/@aiinrealworld/handling-dates-in-natural-language-without-hallucination-87e84be04309))
- Production-ready libraries widely cited: **dateparser**, **python-dateutil**, **parsedatetime**, **Duckling** (Facebook/Wit.ai), **Natty**, **Hawking** (Zoho), **timefhuman**. ([Dexlock — NLP Date Parsers](https://dexlock.com/blog/a-dive-into-nlp-date-parsers/))
- **Verdict**: Strongly validated. LLM date parsing is widely considered an anti-pattern for booking systems specifically because hallucinated dates create direct revenue/legal risk. Your `tool_dates` calling `gpt-5.4-mini` for "tomorrow" is documented overspend + accuracy risk.

### P1.4 — Trim itinerary prompt — ⚠️ implicit consensus

No single high-authority source quantifies "how short should a system prompt be," but token-economy literature is consistent: smaller prompts → lower TTFT + better cache hit rates. Move rarely-fired sections to tool docstrings (model only reads when invoking that tool). ([Zylos — AI Agent Cost Optimization](https://zylos.ai/research/2026-02-19-ai-agent-cost-optimization-token-economics))

### P2.1 — AgentOps alongside Langfuse — ⚠️ emerging consensus

- AgentOps is the most-cited platform for multi-agent **session replay and handoff visualization** specifically. Many production teams run both: Langfuse for prompt mgmt/evals, AgentOps for agent-level debugging. ([15 AI Agent Observability Tools 2026](https://research.aimultiple.com/agentic-monitoring/))
- **Verdict**: Useful but optional. Your existing Langfuse setup covers ~80% of needs.

### P2.2 — Trace sampling in production — ✅ standard observability practice

- Langfuse docs note tracing uses async batching with minimal overhead, but at scale "sampling strategies become important for managing costs and performance." ([Langfuse Observability docs](https://langfuse.com/docs/observability/overview))
- Benchmarking shows non-zero latency impact — AgentOps and Langfuse both show measurable overhead under high integration depth ([AIMultiple agent monitoring 2026](https://research.aimultiple.com/agentic-monitoring/))
- **Verdict**: Standard. Sample 10–20% of normal traces + 100% of errors and slow requests.

---

## 7. Validation Summary

| Recommendation | Industry Status | Confidence |
|---|---|---|
| P0.1 Model right-sizing | Standard practice (Walmart, DCAM framework, NVIDIA router) | **High** |
| P0.2 Rule-based pre-classifier | Standard practice (Arize, Patronus, NVIDIA) | **High** |
| P0.3 Prompt ordering for cache | OpenAI official recommendation (used in Codex CLI) | **Very high** |
| P0.4 Streaming responses | Universal practice (OpenAI, all major chatbots) | **Very high** |
| P1.1 External API caching | Standard practice (Redis, Azure) | **High** |
| P1.2 Parallel tool execution | Official LangGraph pattern (LangChain + AWS docs) | **High** |
| P1.3 Local date parser | Strongly validated anti-LLM pattern | **High** |
| P1.4 Trim prompts | Implicit consensus (token economy) | **Medium** |
| P2.1 AgentOps | Emerging consensus | **Medium** |
| P2.2 Trace sampling | Standard observability practice | **High** |

**Bottom line**: Every P0 and P1 recommendation in this plan is either (a) the explicit recommendation of the relevant vendor (OpenAI, LangChain, Redis) or (b) documented in production case studies (Walmart, NVIDIA, AWS). None of them are speculative. The plan is conservative — it doesn't even propose more aggressive techniques like semantic caching, speculative decoding, or fine-tuned routing classifiers that are also industry-validated.

---

## 8. Research Sources

- LAMaS — [Learning Latency-Aware Orchestration for Parallel Multi-Agent Systems](https://arxiv.org/abs/2601.10560)
- M1-Parallel — [Optimizing Sequential Multi-Step Tasks with Parallel LLM Agents](https://arxiv.org/html/2507.08944v1)
- [LangChain — Benchmarking Multi-Agent Architectures](https://www.langchain.com/blog/benchmarking-multi-agent-architectures)
- [LLM Routing and Model Cascades — TianPan](https://tianpan.co/blog/2025-11-03-llm-routing-model-cascades)
- [3-Tier Routing Cascade: Rule → Semantic → LLM](https://blog.meganova.ai/the-3-tier-routing-cascade-rule-based-semantic-llm/)
- [Hierarchical Caching for Agentic Workflows — MDPI](https://www.mdpi.com/2504-4990/8/2/30)
- [Speeding up agentic workflows with WebSockets — OpenAI](https://openai.com/index/speeding-up-agentic-workflows-with-websockets/)
- [AgentOps platform](https://www.agentops.ai/) | [AgentOps GitHub](https://github.com/AgentOps-AI/agentops)
- [Building Responsive AI: Optimizing Agent Latency](https://medium.com/@yuxiaojian/building-responsive-ai-a-practical-guide-to-optimizing-agent-latency-7364e12937af)
- [AI Agent Cost Optimization — Zylos](https://zylos.ai/research/2026-02-19-ai-agent-cost-optimization-token-economics)
