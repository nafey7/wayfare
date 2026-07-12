#!/usr/bin/env python3
"""Voya Chat CLI - Interactive and scripted chat with Voya AI assistant.

Talk to Voya's chat API from the command line against local, staging, or prod.
Supports multi-turn conversations, timing collection, and scenario testing.

Usage:
    # Interactive chat on staging
    python voya_chat.py --env staging

    # Single message (outputs chat_id for resuming)
    python voya_chat.py --env staging -m "search flights from london to paris"

    # Multi-turn conversation (messages sent sequentially)
    python voya_chat.py --env staging \\
        -m "search flights from amsterdam to tokyo" \\
        -m "next week, 2 adults" \\
        -m "book the cheapest"

    # Resume a previous conversation
    python voya_chat.py --env staging --chat-id <id> -m "actually make it 3 adults"

    # JSON output (machine-readable with timing)
    python voya_chat.py --env staging -m "hi" --json

    # Run a test scenario from file
    python voya_chat.py --env staging --scenario scenarios/02_flight_basic/2.6_all_fields_one_message.json

    # List/manage conversations
    python voya_chat.py --env staging --conversations
    python voya_chat.py --env staging --history --chat-id <id>
    python voya_chat.py --env staging --clear --chat-id <id>

Scenario file format (JSON):
    {
      "name": "flight_booking_happy_path",
      "description": "Test basic flight search flow",
      "messages": [
        {"send": "search flights", "expect_type": "ai_response", "max_time_ms": 10000},
        {"send": "london to paris next week", "expect_type": "flight_search_results", "max_time_ms": 60000},
        {"send": "book option 1"}
      ]
    }

Credentials are resolved in order:
    1. CLI args: --email/--password
    2. Environment variables: VOYA_EMAIL, VOYA_PASSWORD
    3. Secrets file: .local/secrets/chat_<env> (gitignored, for personal use)
    4. Defaults: testuser@example.com / Test123! (local/staging only)
    5. Interactive prompt (prod)
"""

import argparse
import getpass
import json
import os
import re
try:
    import readline  # enables arrow keys and history in input()  # noqa: F401
except ImportError:
    pass  # Windows: readline not available; arrow keys just won't work in input()
import signal
import sys
import time

# Ensure stdout handles Unicode on Windows (cp1252 can't encode → ✈ etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SECRETS_DIR = PROJECT_ROOT / ".local" / "secrets"

ENV_URLS = {
    "local": "http://localhost:8000",
    "test": "http://localhost:8001",
    "staging": "https://staging.myvoya.ai",
    "prod": "https://app.myvoya.ai",
}

# Default test user (seeded on local/staging, NOT on prod)
DEFAULT_TEST_USER = {
    "email": "testuser@example.com",
    "password": "Test123!",  # pragma: allowlist secret
}


def load_credentials(env: str, email: str | None, password: str | None) -> tuple[str, str]:
    """Resolve credentials from args, env vars, secrets file, defaults, or interactive prompt."""
    if email and password:
        return email, password

    # 1. Environment variables
    env_email = os.environ.get("VOYA_EMAIL")
    env_password = os.environ.get("VOYA_PASSWORD")
    if env_email and env_password:
        return env_email, env_password

    # 2. Secrets file (.local/secrets/chat_<env>)
    secrets_file = SECRETS_DIR / f"chat_{env}"
    if secrets_file.exists():
        config = {}
        for line in secrets_file.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
        if "EMAIL" in config and "PASSWORD" in config:
            return config["EMAIL"], config["PASSWORD"]

    # 3. Default test user for non-prod environments
    if env in ("local", "test", "staging"):
        return DEFAULT_TEST_USER["email"], DEFAULT_TEST_USER["password"]

    # 4. Interactive prompt for prod
    print(f"No credentials found for {env}. Enter manually:")
    email = email or input("  Email: ").strip()
    password = password or getpass.getpass("  Password: ")
    return email, password


def api_request(
    base_url: str,
    method: str,
    endpoint: str,
    token: str | None = None,
    body: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Make an HTTP request to the Voya API."""
    url = f"{base_url}/api/{endpoint}"
    if params:
        url += "?" + urlencode({k: v for k, v in params.items() if v is not None})

    data = json.dumps(body).encode() if body else None

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "VoyaChatCLI/1.0",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, data=data, headers=headers, method=method)

    # Preserve POST method on redirect (urllib defaults to GET)
    class PostRedirectHandler(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return Request(newurl, data=req.data, headers=dict(req.headers), method=req.method)

    opener = build_opener(PostRedirectHandler)

    try:
        with opener.open(req, timeout=180) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body_text)
            detail = err.get("detail", body_text)
        except json.JSONDecodeError:
            detail = body_text
        return {"_error": True, "_status": e.code, "_detail": detail}


def login(base_url: str, email: str, password: str) -> dict:
    """Login and return the full auth response."""
    result = api_request(base_url, "POST", "auth/login", body={
        "email": email,
        "password": password,
    })
    if result.get("_error"):
        print(f"Login failed ({result['_status']}): {result['_detail']}", file=sys.stderr)
        sys.exit(1)
    return result


def refresh_token(base_url: str, refresh_tok: str) -> dict | None:
    """Refresh the access token."""
    result = api_request(base_url, "POST", "auth/refresh", body={
        "refresh_token": refresh_tok,
    })
    if result.get("_error"):
        return None
    return result


def send_message_raw(base_url: str, token: str, message: str, chat_id: str | None) -> dict:
    """Send a chat message (raw API call)."""
    body = {"message": message}
    if chat_id:
        body["chat_id"] = chat_id
    return api_request(base_url, "POST", "chat/message", token=token, body=body)


def get_history(base_url: str, token: str, chat_id: str | None, limit: int = 50) -> dict:
    """Get chat history."""
    endpoint = f"chat/{chat_id}" if chat_id else "chat/latest"
    return api_request(base_url, "GET", endpoint, token=token, params={"limit": limit})


def get_conversations(base_url: str, token: str, limit: int = 10) -> dict:
    """List conversations."""
    return api_request(base_url, "GET", "chat/conversations", token=token, params={"limit": limit})


def clear_chat(base_url: str, token: str, chat_id: str | None) -> dict:
    """Clear a chat."""
    endpoint = f"chat/{chat_id}" if chat_id else "chat/latest"
    return api_request(base_url, "DELETE", endpoint, token=token)


# -- Formatting ----------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"


def format_response(resp: dict, timing_ms: float | None = None) -> str:
    """Format a chat response for terminal display."""
    if resp.get("_error"):
        return f"{RED}Error ({resp['_status']}): {resp['_detail']}{RESET}"

    parts = []

    # Main message
    message = resp.get("message", "")
    if message:
        parts.append(f"{GREEN}{message}{RESET}")

    # Response metadata line
    meta = []
    if resp.get("type") and resp["type"] != "message":
        meta.append(f"type={resp['type']}")
    if resp.get("intent_name"):
        meta.append(f"intent={resp['intent_name']}")
    if resp.get("confidence"):
        meta.append(f"conf={resp['confidence']:.2f}")
    if timing_ms is not None:
        if timing_ms >= 1000:
            meta.append(f"time={timing_ms/1000:.1f}s")
        else:
            meta.append(f"time={timing_ms:.0f}ms")
    if resp.get("message_id"):
        meta.append(f"msg={resp['message_id']}")
    if meta:
        parts.append(f"{DIM}  [{', '.join(meta)}]{RESET}")

    # Structured data summary
    data = resp.get("data")
    if data and isinstance(data, dict):
        parts.append(format_data_summary(resp.get("type", ""), data))

    return "\n".join(parts)


def format_data_summary(resp_type: str, data: dict) -> str:
    """Format structured response data (flights, hotels, etc.)."""
    lines = []

    if resp_type == "flight_search_results":
        summary = data.get("summary", {})
        if summary:
            lines.append(f"\n{YELLOW}--- Flight Results ---{RESET}")
            lines.append(f"  Total: {summary.get('total_flights', '?')} flights "
                         f"({summary.get('direct_count', '?')} direct)")
            price = summary.get("price_range", {})
            if price:
                lines.append(f"  Price: ${price.get('min', '?')} - ${price.get('max', '?')}")
            airlines = summary.get("airlines", [])
            if airlines:
                lines.append(f"  Airlines: {', '.join(airlines[:8])}")

        categories = data.get("categories", {})
        for cat_name, cat_data in categories.items():
            flights = cat_data.get("flights", [])
            if flights:
                lines.append(f"\n  {BOLD}{cat_name.replace('_', ' ').title()}{RESET}:")
                for i, f in enumerate(flights[:3], 1):
                    airline = f.get("airline", "?")
                    price_val = f.get("total_price") or f.get("price", "?")
                    dep = f.get("departure_time", "?")
                    arr = f.get("arrival_time", "?")
                    stops = f.get("stops", "?")
                    lines.append(f"    {i}. {airline} | {dep}-{arr} | {stops} stop(s) | ${price_val}")

    elif resp_type == "hotel_search_results":
        summary = data.get("summary", {})
        if summary:
            lines.append(f"\n{YELLOW}--- Hotel Results ---{RESET}")
            lines.append(f"  Total: {summary.get('total_hotels', '?')} hotels")
            price = summary.get("price_range", {})
            if price:
                lines.append(f"  Price: ${price.get('min', '?')} - ${price.get('max', '?')}")

        categories = data.get("categories", {})
        for cat_name, cat_data in categories.items():
            hotels = cat_data.get("hotels", [])
            if hotels:
                lines.append(f"\n  {BOLD}{cat_name.replace('_', ' ').title()}{RESET}:")
                for i, h in enumerate(hotels[:3], 1):
                    name = h.get("name", "?")
                    stars = h.get("star_rating", "?")
                    price_val = h.get("total_price") or h.get("price", "?")
                    lines.append(f"    {i}. {name} ({stars}*) | ${price_val}")

    elif data:
        keys = [k for k in data.keys() if not k.startswith("_")]
        lines.append(f"\n{DIM}  [data: {keys}]{RESET}")

    return "\n".join(lines)


# -- Chat Session --------------------------------------------------------------

class ChatSession:
    def __init__(self, base_url: str, auth_response: dict, chat_id: str | None = None):
        self.base_url = base_url
        self.access_token = auth_response["access_token"]
        self.refresh_tok = auth_response.get("refresh_token")
        self.user = auth_response.get("user", {})
        self.chat_id = chat_id
        self.message_count = 0
        self.show_raw = False
        self.last_response = None
        self.turn_log: list[dict] = []  # Collects all turns with timing

    def ensure_token(self):
        """Refresh token if needed."""
        if self.message_count > 0 and self.message_count % 25 == 0 and self.refresh_tok:
            result = refresh_token(self.base_url, self.refresh_tok)
            if result:
                self.access_token = result["access_token"]
                self.refresh_tok = result.get("refresh_token", self.refresh_tok)
                print(f"{DIM}  [token refreshed]{RESET}", file=sys.stderr)

    def send(self, message: str) -> tuple[dict, float]:
        """Send a message. Returns (response, response_time_ms)."""
        self.ensure_token()

        start = time.monotonic()
        resp = send_message_raw(self.base_url, self.access_token, message, self.chat_id)

        # Retry on 401
        if resp.get("_error") and resp.get("_status") == 401 and self.refresh_tok:
            ref = refresh_token(self.base_url, self.refresh_tok)
            if ref:
                self.access_token = ref["access_token"]
                self.refresh_tok = ref.get("refresh_token", self.refresh_tok)
                start = time.monotonic()
                resp = send_message_raw(self.base_url, self.access_token, message, self.chat_id)

        elapsed_ms = (time.monotonic() - start) * 1000

        if not resp.get("_error"):
            self.chat_id = resp.get("chat_id", self.chat_id)
            self.message_count += 1
            self.last_response = resp

        # Log turn
        turn = {
            "turn": self.message_count,
            "user_message": message,
            "response_time_ms": round(elapsed_ms, 1),
            "chat_id": self.chat_id,
            "type": resp.get("type"),
            "intent": resp.get("intent_name"),
            "confidence": resp.get("confidence"),
            "message_id": resp.get("message_id"),
            "ai_message": resp.get("message", "")[:500],
            "has_data": bool(resp.get("data")),
            "error": resp.get("_error"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.turn_log.append(turn)

        return resp, elapsed_ms

    def get_summary(self) -> dict:
        """Return a summary of the session for JSON output."""
        times = [t["response_time_ms"] for t in self.turn_log if not t.get("error")]
        return {
            "chat_id": self.chat_id,
            "env": None,  # Filled by caller
            "total_turns": len(self.turn_log),
            "total_time_ms": round(sum(times), 1) if times else 0,
            "avg_time_ms": round(sum(times) / len(times), 1) if times else 0,
            "max_time_ms": round(max(times), 1) if times else 0,
            "turns": self.turn_log,
        }

    def handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True if handled."""
        parts = cmd.strip().split(None, 1)
        cmd_name = parts[0].lower()

        if cmd_name in ("/quit", "/exit", "/q"):
            print(f"\n{DIM}Goodbye!{RESET}")
            sys.exit(0)

        elif cmd_name == "/new":
            self.chat_id = None
            self.message_count = 0
            self.turn_log = []
            print(f"{CYAN}  Starting new conversation{RESET}")
            return True

        elif cmd_name == "/history":
            hist = get_history(self.base_url, self.access_token, self.chat_id)
            if hist.get("_error"):
                print(f"{RED}  Error: {hist['_detail']}{RESET}")
            else:
                messages = hist.get("messages", [])
                if not messages:
                    print(f"{DIM}  No messages yet{RESET}")
                for msg in messages:
                    sender = msg.get("sender", "?")
                    text = msg.get("message", "")[:120]
                    mtype = msg.get("type", "message")
                    color = BLUE if sender == "USER" else GREEN
                    suffix = f" {DIM}[{mtype}]{RESET}" if mtype != "message" else ""
                    print(f"  {color}{sender}{RESET}: {text}{suffix}")
            return True

        elif cmd_name == "/conversations":
            convos = get_conversations(self.base_url, self.access_token)
            if convos.get("_error"):
                print(f"{RED}  Error: {convos['_detail']}{RESET}")
            else:
                for c in convos.get("conversations", []):
                    cid = c.get("chat_id", "?")
                    count = c.get("message_count", c.get("count", "?"))
                    active = " (active)" if cid == self.chat_id else ""
                    print(f"  {cid}  [{count} msgs]{active}")
            return True

        elif cmd_name == "/clear":
            result = clear_chat(self.base_url, self.access_token, self.chat_id)
            if result.get("_error"):
                print(f"{RED}  Error: {result['_detail']}{RESET}")
            else:
                print(f"{CYAN}  Chat cleared: {result.get('message', 'ok')}{RESET}")
                self.chat_id = None
            return True

        elif cmd_name == "/info":
            print(f"  Chat ID:  {self.chat_id or 'none (new)'}")
            print(f"  User:     {self.user.get('email', '?')}")
            print(f"  Messages: {self.message_count}")
            if self.turn_log:
                times = [t["response_time_ms"] for t in self.turn_log if not t.get("error")]
                if times:
                    print(f"  Timing:   avg={sum(times)/len(times):.0f}ms  max={max(times):.0f}ms  total={sum(times):.0f}ms")
            return True

        elif cmd_name == "/raw":
            self.show_raw = not self.show_raw
            print(f"  Raw JSON display: {'on' if self.show_raw else 'off'}")
            return True

        elif cmd_name == "/last":
            if self.last_response:
                print(json.dumps(self.last_response, indent=2, default=str))
            else:
                print(f"{DIM}  No response yet{RESET}")
            return True

        elif cmd_name == "/timing":
            if not self.turn_log:
                print(f"{DIM}  No turns yet{RESET}")
            else:
                print(f"\n  {'#':<4} {'Time':>8}  {'Type':<25} {'Message'}")
                print(f"  {'-'*80}")
                for t in self.turn_log:
                    ms = t["response_time_ms"]
                    time_str = f"{ms/1000:.1f}s" if ms >= 1000 else f"{ms:.0f}ms"
                    color = RED if ms > 30000 else YELLOW if ms > 10000 else ""
                    reset = RESET if color else ""
                    print(f"  {t['turn']:<4} {color}{time_str:>8}{reset}  {(t.get('type') or 'message'):<25} {t['user_message'][:40]}")
            return True

        elif cmd_name.startswith("/"):
            print(f"{DIM}  Unknown command: {cmd_name}{RESET}")
            print(f"{DIM}  /new /history /conversations /clear /info /raw /last /timing /quit{RESET}")
            return True

        return False


# -- Interactive mode ----------------------------------------------------------

def print_welcome(env: str, base_url: str, user: dict, chat_id: str | None):
    """Print welcome banner."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Voya Chat CLI{RESET} - {CYAN}{env}{RESET} ({base_url})")
    print(f"  User: {user.get('email', '?')} ({user.get('first_name', '')} {user.get('last_name', '')})")
    if chat_id:
        print(f"  Chat: {chat_id} (continuing)")
    else:
        print(f"  Chat: new conversation")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{DIM}  /new /history /conversations /clear /info /timing /raw /last /quit{RESET}")
    print(f"{DIM}  Ctrl+C to exit{RESET}\n")


def interactive_loop(session: ChatSession, env: str, base_url: str):
    """Run the interactive chat REPL."""
    print_welcome(env, base_url, session.user, session.chat_id)

    def sigint_handler(sig, frame):
        print(f"\n{DIM}Goodbye!{RESET}")
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    while True:
        try:
            user_input = input(f"{BLUE}You>{RESET} ").strip()
        except EOFError:
            print(f"\n{DIM}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            session.handle_command(user_input)
            continue

        # Send message with timing
        print(f"{DIM}  Sending...{RESET}", end="\r")
        resp, elapsed_ms = session.send(user_input)

        # Clear the sending line
        print(" " * 40, end="\r")

        # Show chat_id on first message
        if session.message_count == 1:
            print(f"{DIM}  chat_id: {session.chat_id}{RESET}")

        if session.show_raw:
            resp["_timing_ms"] = round(elapsed_ms, 1)
            print(json.dumps(resp, indent=2, default=str))
        else:
            print(f"{GREEN}Voya>{RESET} {format_response(resp, elapsed_ms)}")
        print()


# -- Scripted modes ------------------------------------------------------------

def run_messages(session: ChatSession, messages: list[str], output_json: bool = False, env: str = ""):
    """Send a sequence of messages, collecting timing for each."""
    results = []

    for i, msg in enumerate(messages):
        if not output_json:
            print(f"{BLUE}[{i+1}/{len(messages)}] You>{RESET} {msg}")

        resp, elapsed_ms = session.send(msg)

        if not output_json:
            # Show chat_id on first turn
            if i == 0:
                print(f"{DIM}  chat_id: {session.chat_id}{RESET}")
            print(f"{GREEN}Voya>{RESET} {format_response(resp, elapsed_ms)}")
            print()

        results.append({
            "turn": i + 1,
            "user_message": msg,
            "response_time_ms": round(elapsed_ms, 1),
            "chat_id": session.chat_id,
            "type": resp.get("type"),
            "intent": resp.get("intent_name"),
            "confidence": resp.get("confidence"),
            "message_id": resp.get("message_id"),
            "ai_message": resp.get("message", ""),
            "has_data": bool(resp.get("data")),
            "error": bool(resp.get("_error")),
            "error_detail": resp.get("_detail") if resp.get("_error") else None,
        })

    if output_json:
        summary = session.get_summary()
        summary["env"] = env
        print(json.dumps(summary, indent=2, default=str))
    else:
        # Print session summary
        times = [r["response_time_ms"] for r in results if not r.get("error")]
        if times:
            print(f"{DIM}--- Session Summary ---{RESET}")
            print(f"{DIM}  chat_id: {session.chat_id}{RESET}")
            print(f"{DIM}  turns: {len(results)}  "
                  f"avg: {sum(times)/len(times):.0f}ms  "
                  f"max: {max(times):.0f}ms  "
                  f"total: {sum(times):.0f}ms{RESET}")


def _resolve_scenario_templates(text: str) -> str:
    """Resolve date templates in scenario JSON text before parsing.

    Supported patterns:
      {{today+N}}          → ISO date N days from today  (e.g. 2026-05-17)
      {{today+N:natural}}  → human-readable date         (e.g. "May 17, 2026")
      {{today+N:FORMAT}}   → strftime format             (e.g. {{today+30:%d/%m/%Y}})
      {{month+N}}          → month name N months ahead   (e.g. "October")

    Note: negative offsets (today-N) are not supported; use today+0 for today.
    """
    today = date.today()

    def _replace_today(m: re.Match) -> str:
        days = int(m.group(1))
        fmt = m.group(2)
        target = today + timedelta(days=days)
        if not fmt:
            return target.isoformat()
        if fmt == "natural":
            return f"{target.strftime('%B')} {target.day}, {target.year}"
        return target.strftime(fmt)

    def _replace_month(m: re.Match) -> str:
        months_ahead = int(m.group(1))
        month = today.month + months_ahead
        year = today.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return date(year, month, 1).strftime("%B")

    text = re.sub(r"\{\{today\+(\d+)(?::(.*?))?\}\}", _replace_today, text)
    text = re.sub(r"\{\{month\+(\d+)\}\}", _replace_month, text)
    return text


def _run_step_assertions(step: dict, resp: dict, elapsed_ms: float) -> list[tuple[str, bool, str]]:
    """Return list of (check_name, passed, detail) for a single step's assertions."""
    checks: list[tuple[str, bool, str]] = []

    if resp.get("_error"):
        checks.append(("no_error", False, f"got error: {resp.get('_detail', '?')[:60]}"))
        return checks

    expect_type = step.get("expect_type")
    expect_type_in = step.get("expect_type_in")
    expect_intent = step.get("expect_intent")
    expect_has_data = step.get("expect_has_data")
    max_time_ms = step.get("max_time_ms")
    expect_contains = step.get("expect_contains")
    expect_contains_all = step.get("expect_contains_all")
    expect_contains_any = step.get("expect_contains_any")
    expect_not_contains = step.get("expect_not_contains")
    expect_has_suggestions = step.get("expect_has_suggestions")
    expect_search_params = step.get("expect_search_params")
    expect_min_results = step.get("expect_min_results")
    # #1053 P0.2 — locks the #1038 side-search promise (itinerary responses
    # ship full flights/hotels arrays + a day-count consistent with the
    # requested trip duration). Read from response.data; tolerant of both
    # the flat shape and the nested ``data.data`` shape.
    expect_min_flights = step.get("expect_min_flights")
    expect_min_hotels = step.get("expect_min_hotels")
    expect_min_days = step.get("expect_min_days")
    expect_max_flights = step.get("expect_max_flights")
    expect_max_hotels = step.get("expect_max_hotels")

    if expect_type:
        if isinstance(expect_type, list):
            ok = resp.get("type") in expect_type
        else:
            ok = resp.get("type") == expect_type
        checks.append(("type", ok, f"expected={expect_type} got={resp.get('type')}"))
    if expect_type_in:
        ok = resp.get("type") in expect_type_in
        checks.append(("type_in", ok, f"expected in {expect_type_in} got={resp.get('type')}"))
    if expect_intent:
        ok = resp.get("intent_name") == expect_intent
        checks.append(("intent", ok, f"expected={expect_intent} got={resp.get('intent_name')}"))
    if expect_has_data is not None:
        ok = bool(resp.get("data")) == expect_has_data
        checks.append(("has_data", ok, f"expected={expect_has_data} got={bool(resp.get('data'))}"))
    if max_time_ms is not None:
        ok = elapsed_ms <= max_time_ms
        checks.append(("max_time", ok, f"{elapsed_ms:.0f}ms <= {max_time_ms}ms"))

    ai_msg_lower = (resp.get("message") or "").lower()

    if expect_contains:
        if isinstance(expect_contains, list):
            # Legacy: list = all must match
            for term in expect_contains:
                ok = term.lower() in ai_msg_lower
                checks.append(("contains", ok, f"'{term}' in response"))
        else:
            ok = expect_contains.lower() in ai_msg_lower
            checks.append(("contains", ok, f"'{expect_contains}' in response"))
    if expect_contains_all:
        for term in expect_contains_all:
            ok = term.lower() in ai_msg_lower
            checks.append(("contains_all", ok, f"'{term}' in response"))
    if expect_contains_any:
        ok = any(term.lower() in ai_msg_lower for term in expect_contains_any)
        checks.append(("contains_any", ok, f"any of {expect_contains_any} in response"))
    if expect_not_contains:
        terms = expect_not_contains if isinstance(expect_not_contains, list) else [expect_not_contains]
        for term in terms:
            ok = term.lower() not in ai_msg_lower
            checks.append(("not_contains", ok, f"'{term}' absent from response"))
    if expect_has_suggestions is not None:
        # Suggestions come through data.suggestions (structured) or inline [SUGGESTIONS] tag
        data = resp.get("data") or {}
        structured = data.get("suggestions") or []
        inline_count = (resp.get("message") or "").count("[SUGGESTIONS]")
        has_suggestions = len(structured) > 0 or inline_count > 0
        if isinstance(expect_has_suggestions, bool):
            ok = has_suggestions == expect_has_suggestions
            checks.append(("has_suggestions", ok, f"expected={expect_has_suggestions} got={has_suggestions} (n={len(structured)})"))
        else:
            # int: expected exact count
            ok = len(structured) == expect_has_suggestions
            checks.append(("has_suggestions", ok, f"expected={expect_has_suggestions} got={len(structured)}"))

    if expect_search_params:
        # Flight/hotel data is double-nested: resp.data.data.search_params
        # (ChatResponse.data wraps the supervisor result which has its own "data" key)
        top_data = resp.get("data") or {}
        inner_data = top_data.get("data") or {}
        actual_params = (
            inner_data.get("search_params")
            or top_data.get("search_params")
            or resp.get("collected_params")
            or {}
        )
        for param_key, expected_val in expect_search_params.items():
            actual_val = actual_params.get(param_key)
            if "." in param_key:
                parts = param_key.split(".")
                actual_val = actual_params
                for part in parts:
                    actual_val = (actual_val or {}).get(part) if isinstance(actual_val, dict) else None
            if isinstance(expected_val, str) and isinstance(actual_val, str):
                ok = expected_val.lower() == actual_val.lower()
            else:
                ok = actual_val == expected_val
            checks.append(("search_param", ok, f"{param_key}: expected={expected_val} got={actual_val}"))
    if expect_min_results is not None:
        # Categories live inside resp.data.data.categories (double-nested)
        top_data = resp.get("data") or {}
        inner_data = top_data.get("data") or {}
        categories = inner_data.get("categories") or top_data.get("categories") or {}
        seen_ids = set()
        for cat_data in categories.values():
            for item in cat_data.get("flights", []) + cat_data.get("hotels", []):
                item_id = item.get("sequence_number") or item.get("hotel_code") or id(item)
                seen_ids.add(item_id)
        result_count = len(seen_ids)
        ok = result_count >= expect_min_results
        checks.append(("min_results", ok, f"got {result_count} >= {expect_min_results}"))

    # #1053 P0.2 — itinerary side-search promises (#1038):
    # ``data.flights`` / ``data.hotels`` are flat top-level arrays on the
    # itinerary response (or nested under ``data.data`` on legacy shapes).
    # ``data.structured_itinerary.itineraryItems`` carries the day list.
    if (
        expect_min_flights is not None
        or expect_min_hotels is not None
        or expect_min_days is not None
        or expect_max_flights is not None
        or expect_max_hotels is not None
    ):
        top_data = resp.get("data") or {}
        inner_data = top_data.get("data") if isinstance(top_data.get("data"), dict) else {}
        flights = top_data.get("flights") or inner_data.get("flights") or []
        hotels = top_data.get("hotels") or inner_data.get("hotels") or []
        structured = (
            top_data.get("structured_itinerary")
            or inner_data.get("structured_itinerary")
            or {}
        )
        days = structured.get("itineraryItems") or [] if isinstance(structured, dict) else []
        flight_count = len(flights) if isinstance(flights, list) else 0
        hotel_count = len(hotels) if isinstance(hotels, list) else 0
        day_count = len(days) if isinstance(days, list) else 0

        if expect_min_flights is not None:
            ok = flight_count >= expect_min_flights
            checks.append(
                ("min_flights", ok, f"got {flight_count} >= {expect_min_flights}")
            )
        if expect_max_flights is not None:
            ok = flight_count <= expect_max_flights
            checks.append(
                ("max_flights", ok, f"got {flight_count} <= {expect_max_flights}")
            )
        if expect_min_hotels is not None:
            ok = hotel_count >= expect_min_hotels
            checks.append(
                ("min_hotels", ok, f"got {hotel_count} >= {expect_min_hotels}")
            )
        if expect_max_hotels is not None:
            ok = hotel_count <= expect_max_hotels
            checks.append(
                ("max_hotels", ok, f"got {hotel_count} <= {expect_max_hotels}")
            )
        if expect_min_days is not None:
            ok = day_count >= expect_min_days
            checks.append(("min_days", ok, f"got {day_count} >= {expect_min_days}"))

    return checks


def _resolve_scenario_path(scenario_path: str) -> Path | None:
    """Find scenario file by name or relative path."""
    path = Path(scenario_path)
    if path.is_absolute() and path.exists():
        return path
    candidates = [
        Path(scenario_path),
        SCRIPT_DIR / "scenarios" / scenario_path,
        SCRIPT_DIR / "scenarios" / f"{scenario_path}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Recursive search under scenarios/ (for subdir organization)
    stem = Path(scenario_path).stem
    for c in (SCRIPT_DIR / "scenarios").rglob(f"{stem}.json"):
        return c
    return None


def run_scenario(session: ChatSession, scenario_path: str, env: str = "", quiet: bool = False) -> dict:
    """Run a test scenario from a JSON file. Returns result summary dict (does not exit)."""
    path = _resolve_scenario_path(scenario_path)
    if path is None:
        print(f"{RED}Scenario file not found: {scenario_path}{RESET}", file=sys.stderr)
        return {"name": scenario_path, "found": False, "passed": 0, "failed": 1, "error": "not_found"}

    scenario = json.loads(_resolve_scenario_templates(path.read_text(encoding="utf-8")))
    if not isinstance(scenario, dict):
        if not quiet:
            print(f"{DIM}Skipping {path.name} (unsupported format){RESET}")
        return {"name": path.stem, "found": True, "passed": 0, "failed": 0, "skipped": True}
    name = scenario.get("name", path.stem)
    description = scenario.get("description", "")
    messages = scenario.get("messages", [])

    if not quiet:
        print(f"\n{BOLD}Scenario: {name}{RESET}")
        if description:
            print(f"{DIM}{description}{RESET}")
        print(f"{DIM}Steps: {len(messages)} | Env: {env}{RESET}")
        print(f"{'-'*60}")

    results = []
    passed = 0
    failed = 0

    for i, step in enumerate(messages):
        msg = step.get("send", "")

        if not quiet:
            print(f"\n{BLUE}[Step {i+1}] You>{RESET} {msg}")

        resp, elapsed_ms = session.send(msg)

        if not quiet:
            if i == 0:
                print(f"{DIM}  chat_id: {session.chat_id}{RESET}")
            print(f"{GREEN}Voya>{RESET} {format_response(resp, elapsed_ms)}")

        checks = _run_step_assertions(step, resp, elapsed_ms)
        step_passed = all(c[1] for c in checks) if checks else True

        if not quiet:
            for check_name, ok, detail in checks:
                symbol = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
                print(f"  {symbol} {check_name}: {detail}")

        if step_passed:
            passed += 1
        else:
            failed += 1

        results.append({
            "step": i + 1,
            "send": msg,
            "response_time_ms": round(elapsed_ms, 1),
            "type": resp.get("type"),
            "intent": resp.get("intent_name"),
            "confidence": resp.get("confidence"),
            "message_id": resp.get("message_id"),
            "search_params": (resp.get("data") or {}).get("search_params") or resp.get("collected_params"),
            "summary": (resp.get("data") or {}).get("summary"),
            "ai_message": (resp.get("message") or "")[:300],
            "checks": [{"name": c[0], "passed": c[1], "detail": c[2]} for c in checks],
            "passed": step_passed,
        })

    times = [r["response_time_ms"] for r in results]
    status = f"{GREEN}PASS{RESET}" if failed == 0 else f"{RED}FAIL{RESET}"

    if not quiet:
        print(f"\n{'='*60}")
        print(f"  {BOLD}{name}{RESET}: {status} ({passed}/{passed + failed} steps)")
        print(f"  chat_id: {session.chat_id}")
        if times:
            print(f"  timing: avg={sum(times)/len(times):.0f}ms  max={max(times):.0f}ms  total={sum(times):.0f}ms")

    # Write per-scenario result file
    results_dir = SCRIPT_DIR / "scenario_results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = results_dir / f"{name}_{env}_{ts}.json"
    result_data = {
        "scenario": name,
        "description": description,
        "env": env,
        "chat_id": session.chat_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": failed,
        "total_time_ms": round(sum(times), 1) if times else 0,
        "avg_time_ms": round(sum(times) / len(times), 1) if times else 0,
        "max_time_ms": round(max(times), 1) if times else 0,
        "steps": results,
    }
    result_file.write_text(json.dumps(result_data, indent=2, default=str))
    if not quiet:
        print(f"  results: {result_file}")

    return {
        "name": name,
        "path": str(path.relative_to(SCRIPT_DIR) if path.is_relative_to(SCRIPT_DIR) else path),
        "found": True,
        "passed": passed,
        "failed": failed,
        "total_steps": passed + failed,
        "total_time_ms": round(sum(times), 1) if times else 0,
        "chat_id": session.chat_id,
    }


def run_scenario_dir(
    base_url: str, auth: dict, dir_path: str, env: str, quiet: bool = False,
    email: str | None = None, password: str | None = None,
) -> int:
    """Run all scenarios under a directory. Each scenario gets a fresh chat. Returns exit code."""
    root = Path(dir_path)
    if not root.is_absolute():
        for candidate in [Path(dir_path), SCRIPT_DIR / dir_path, SCRIPT_DIR / "scenarios" / dir_path]:
            if candidate.exists():
                root = candidate
                break

    if not root.exists() or not root.is_dir():
        print(f"{RED}Scenario directory not found: {dir_path}{RESET}", file=sys.stderr)
        return 2

    scenario_files = sorted(root.rglob("*.json"))
    if not scenario_files:
        print(f"{RED}No scenarios found under {root}{RESET}", file=sys.stderr)
        return 2

    print(f"\n{BOLD}Running {len(scenario_files)} scenarios under {root}{RESET}\n")

    summaries = []
    total_passed = 0
    total_failed = 0

    # Track auth age. JWT default TTL is 30 min — refresh every 20 min to stay safe.
    auth_obtained_at = time.monotonic()
    AUTH_REFRESH_INTERVAL_SEC = 20 * 60

    for idx, sf in enumerate(scenario_files, 1):
        rel = sf.relative_to(root)

        # Proactively refresh auth if it's getting old, to avoid 401s mid-run.
        age = time.monotonic() - auth_obtained_at
        if age > AUTH_REFRESH_INTERVAL_SEC:
            refreshed = None
            if auth.get("refresh_token"):
                refreshed = refresh_token(base_url, auth["refresh_token"])
            if refreshed is None and email and password:
                # Refresh failed (or no refresh token) — fall back to re-login.
                print(f"{DIM}  [auth: re-logging in (age={age / 60:.1f}min)]{RESET}", file=sys.stderr)
                refreshed = login(base_url, email, password)
            if refreshed:
                auth = refreshed
                auth_obtained_at = time.monotonic()
                print(f"{DIM}  [auth refreshed]{RESET}", file=sys.stderr)

        print(f"{DIM}[{idx}/{len(scenario_files)}]{RESET} {rel}")
        # Fresh session per scenario
        session = ChatSession(base_url, auth)
        summary = run_scenario(session, str(sf), env=env, quiet=quiet)
        if summary.get("skipped"):
            print(f"    -> {DIM}SKIP{RESET} (unsupported format)\n")
            continue
        summaries.append(summary)
        total_passed += summary.get("passed", 0)
        total_failed += summary.get("failed", 0)
        status = f"{GREEN}PASS{RESET}" if summary.get("failed", 0) == 0 else f"{RED}FAIL{RESET}"
        print(f"    -> {status} ({summary.get('passed', 0)}/{summary.get('total_steps', 0)} steps)\n")

    # Final aggregate summary
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}AGGREGATE RESULTS ({env}){RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"  Scenarios run: {len(summaries)}")
    print(f"  {GREEN}Passed scenarios: {sum(1 for s in summaries if s.get('failed', 0) == 0)}{RESET}")
    print(f"  {RED}Failed scenarios: {sum(1 for s in summaries if s.get('failed', 0) > 0)}{RESET}")
    print(f"  Steps: {total_passed} passed, {total_failed} failed")
    print()
    print(f"{BOLD}Per-scenario breakdown:{RESET}")
    for s in summaries:
        mark = f"{GREEN}PASS{RESET}" if s.get("failed", 0) == 0 else f"{RED}FAIL{RESET}"
        print(f"  {mark}  {s.get('path', s.get('name'))}  ({s.get('passed', 0)}/{s.get('total_steps', 0)})")

    # Write aggregate report
    results_dir = SCRIPT_DIR / "scenario_results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    agg_file = results_dir / f"_aggregate_{env}_{ts}.json"
    agg_file.write_text(json.dumps({
        "env": env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(summaries),
        "scenarios_passed": sum(1 for s in summaries if s.get("failed", 0) == 0),
        "scenarios_failed": sum(1 for s in summaries if s.get("failed", 0) > 0),
        "steps_passed": total_passed,
        "steps_failed": total_failed,
        "scenarios": summaries,
    }, indent=2, default=str))
    print(f"\n  Aggregate report: {agg_file}")

    return 0 if total_failed == 0 else 1


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Chat with Voya AI from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--env", default="staging", choices=["local", "test", "staging", "prod"],
                        help="Environment (default: staging)")
    parser.add_argument("--email", help="Login email")
    parser.add_argument("--password", help="Login password")
    parser.add_argument("--chat-id", help="Continue existing conversation")

    # Message modes
    parser.add_argument("-m", "--message", action="append", dest="messages",
                        help="Send message (repeat for multi-turn: -m 'hi' -m 'search flights')")
    parser.add_argument("--json", action="store_true",
                        help="JSON output with timing (for scripting)")
    parser.add_argument("--scenario", help="Run test scenario from JSON file")
    parser.add_argument("--scenario-dir", dest="scenario_dir",
                        help="Run all scenarios under a directory (recursively). Each scenario gets a fresh chat.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-step output in scenario runs (only show pass/fail summary)")

    # Management modes
    parser.add_argument("--conversations", action="store_true", help="List conversations")
    parser.add_argument("--history", action="store_true", help="Show chat history")
    parser.add_argument("--clear", action="store_true", help="Clear chat")

    args = parser.parse_args()

    base_url = ENV_URLS[args.env]
    email, password = load_credentials(args.env, args.email, args.password)

    # Login
    if not args.json:
        print(f"{DIM}Logging in to {args.env} ({base_url})...{RESET}", file=sys.stderr)
    auth = login(base_url, email, password)
    if not args.json:
        print(f"{DIM}Logged in as {auth.get('user', {}).get('email', '?')}{RESET}", file=sys.stderr)

    session = ChatSession(base_url, auth, args.chat_id)

    # Management modes
    if args.conversations:
        session.handle_command("/conversations")
        return

    if args.history:
        session.handle_command("/history")
        return

    if args.clear:
        session.handle_command("/clear")
        return

    # Scenario directory mode (run all scenarios under a folder)
    if args.scenario_dir:
        exit_code = run_scenario_dir(
            base_url, auth, args.scenario_dir, env=args.env, quiet=args.quiet,
            email=email, password=password,
        )
        sys.exit(exit_code)

    # Single scenario mode
    if args.scenario:
        summary = run_scenario(session, args.scenario, env=args.env, quiet=args.quiet)
        sys.exit(0 if summary.get("failed", 0) == 0 else 1)

    # Message mode (single or multi-turn)
    if args.messages:
        run_messages(session, args.messages, output_json=args.json, env=args.env)
        return

    # Interactive mode
    interactive_loop(session, args.env, base_url)


if __name__ == "__main__":
    main()
