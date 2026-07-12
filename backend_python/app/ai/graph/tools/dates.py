"""Date parsing tool for LangGraph flight/hotel agent.

This tool uses LLM-based date parsing with structured output to extract dates
from natural language expressions.
"""

import calendar
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.domains.common import utc_date

logger = logging.getLogger(__name__)

MAX_DEPARTURE_WINDOW_DAYS = 31

# Patterns that resolve to specific dates but whose exact meaning is ambiguous
# to the user (e.g. "next weekend" could be Fri-Sun or Sat-Sun).
# When these match, the tool instructs the agent to confirm dates before searching.
_AMBIGUOUS_RELATIVE_PATTERNS = re.compile(
    r"(?:next|this|coming|last)\s+(?:week(?:end|nd)?|month)|"
    r"end\s+of\s+(?:the\s+)?(?:month|week)|"
    r"beginning\s+of\s+(?:the\s+)?(?:month|week)|"
    r"(?:next|this|coming)\s+(?:few|couple)\s+(?:of\s+)?days",
    re.IGNORECASE,
)

# Month-only patterns: "october 2026", "next october", "in april", "may", etc.
# When these match and departure_date is day-01, the user gave only a month —
# the agent should ask for specific dates instead of assuming the 1st.
_MONTH_ONLY_PATTERN = re.compile(
    r"^(?:in\s+)?(?:next\s+|this\s+|coming\s+)?"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{4})?\s*$",
    re.IGNORECASE,
)

# Flexibility keywords that convert a single departure_date to a departure window.
_FLEXIBILITY_TRIGGERS = re.compile(
    r"\b(?:sometime|flexible|anytime|any time|budget-friendly|off-peak|"
    r"off peak|whenever|cheapest)\b",
    re.IGNORECASE,
)

# Business-trip context keywords. When matched alongside "next week" / "this week",
# default duration is 5 days (Mon-Fri) instead of 7 (Mon-Sun).
_BUSINESS_CONTEXT_PATTERN = re.compile(
    r"\b(?:business|work|conference|meeting|client|corporate)\s+"
    r"(?:trip|travel|visit|engagement)?\b",
    re.IGNORECASE,
)

# Quick pre-check: reject input that contains no date-like tokens before
# invoking the LLM.  Prevents hallucinated dates on pure-destination text.
_DATE_HINT_PATTERN = re.compile(
    r"""
    \d                          # any digit (dates, durations)
    | \b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b  # month names (abbrev or full)
    | \b(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?\b              # day names
    | \b(?:today|tomorrow|tonight|yesterday)\b                 # relative words
    | \b(?:next|last|this|after|before|coming|following)\b     # relative modifiers
    | \b(?:week|month|year|day|night|weekend|fortnight)\b      # time units
    | \b(?:spring|summer|autumn|fall|winter)\b                 # seasons
    | \b(?:morning|evening|afternoon)\b
    | \b(?:early|mid|late|end|beginning|start)\b               # range modifiers
    | \b(?:anytime|any\s+time|sometime|whenever|flexible|cheapest)\b  # flexibility signals
    | \b(?:q[1-4])\b                                           # quarters
    | \b(?:christmas|easter|thanksgiving|new\s*year|halloween|diwali       # Western/Hindu
          |eid|ramadan|holi|chinese\s*new\s*year|carnival|songkran         # Global
          |dussehra|navratri|raksha\s*bandhan|loy\s*krathong|vesak        # Asian
          |thaipusam|mardi\s*gras|matariki)\b                             # Other
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Duration-only pattern: text that specifies ONLY how long (not when).
# Examples: "5 days", "a week", "3 night trip", "two weeks", "10 day vacation"
# These should NOT auto-pick departure dates — the agent must ask the user when.
_DURATION_ONLY_PATTERN = re.compile(
    r"^(?:(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+)?"
    r"(?:day|days|night|nights|week|weeks|fortnight|fortnights)"
    r"(?:\s+(?:trip|vacation|holiday|getaway|break))?\s*$",
    re.IGNORECASE,
)

# Broader duration detection: matches duration mentions embedded in longer text.
# E.g. "4-day trip to Rome", "a week vacation to Tokyo", "5 day holiday".
_HAS_DURATION = re.compile(
    r"\b(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)[- ]?"
    r"(?:day|days|night|nights|week|weeks|fortnight|fortnights)\b",
    re.IGNORECASE,
)

# Explicit date anchor: strong indicators that the user specified WHEN, not just how long.
# Excludes bare digits and duration words — those appear in "4-day" which is not a date.
_HAS_EXPLICIT_DATE_ANCHOR = re.compile(
    # "may" requires a following digit to avoid matching the auxiliary verb
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b|"
    r"\bmay\s+\d|"
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"mon|tue|wed|thu|fri|sat|sun)\b|"
    r"\b(?:today|tomorrow|tonight|yesterday)\b|"
    r"\b(?:next|this|coming)\s|"
    r"\bstarting\s|"
    # Relative offset from reference_date: "in 2 weeks", "in a month", "in three days".
    # This IS a date anchor (sets departure_date = reference + offset), distinct from
    # "for 2 weeks" which is duration. Without this, "in 2 weeks, back two weeks after"
    # short-circuits as duration-only and the LLM never sees the departure offset.
    r"\bin\s+(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:day|days|week|weeks|month|months|fortnight|fortnights)\b|"
    # "N days from now / today / tomorrow" — same semantics as "in N days"
    # but a phrasing the regex used to miss, so the supervisor's
    # duration-without-date guard fired incorrectly (see #1105).
    r"\b(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:day|days|week|weeks|month|months|fortnight|fortnights)\s+"
    r"from\s+(?:now|today|tomorrow)\b|"
    r"\b\d{4}[-/]|"
    r"\b\d{1,2}[-/]\d{1,2}",
    re.IGNORECASE,
)

# Map word numbers to integers for duration extraction.
_WORD_TO_NUM: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _extract_duration_days(text: str) -> int | None:
    """Extract numeric duration in days from duration-only text.

    Maps word numbers ("two") and unit words ("week"→7, "fortnight"→14)
    to an integer day count.  Returns None when no number is found.
    """
    normalized = text.strip().lower()
    # Try digit first
    digit_match = re.search(r"\d+", normalized)
    num: int
    if digit_match:
        num = int(digit_match.group())
    else:
        # Try word number
        found: int | None = None
        for word, val in _WORD_TO_NUM.items():
            if re.search(rf"\b{word}\b", normalized):
                found = val
                break
        if found is None:
            return None
        num = found

    # Multiply by unit
    if re.search(r"\bfortnight", normalized):
        return num * 14
    if re.search(r"\bweek", normalized):
        return num * 7
    # day/night → 1:1
    return num


# Hardcoded prompt as fallback (primary source is Langfuse)
DATE_PARSE_PROMPT = """Parse travel date expression → YYYY-MM-DD.

Reference date: {reference_date} | Destination: {destination} | Trip duration: {trip_duration_days} days

## Critical Rules (READ FIRST)
1. **Future dates only**: Every date you output MUST be ≥ reference_date. \
If a holiday/event is past for the current year, use the NEXT year's occurrence. \
Think: "Is this date before {reference_date}? If yes → next year."
2. **YYYY-MM-DD format always** — no exceptions.
3. **Use the `reasoning` field**: Before setting any date field, write your step-by-step \
calculation in `reasoning`. Show: what the expression means → what date that maps to → \
is it future? → final answer. This is mandatory.
4. **Duration convention (NEW — read carefully)**: \
`trip_duration_days` is ALWAYS the count of CALENDAR DAYS INCLUSIVE of both \
`departure_date` and `return_date`. Equivalently: \
`trip_duration_days = (return_date - departure_date).days + 1`. \
The four user phrasings map differently — be precise: \
  - **"N days" / "N-day trip" / "for N days"** → STAY length = N days inclusive. \
`trip_duration_days = N`, `return_date = departure_date + (N - 1)`. \
Example: "7-day trip starting Jun 19" → depart=Jun 19, return=Jun 25, duration=7. \
  - **"N nights" / "N-night stay" / "for N nights"** → N OVERNIGHT stays = N+1 calendar days inclusive. \
`trip_duration_days = N + 1`, `return_date = departure_date + N`. \
Example: "7 nights starting Jun 19" → depart=Jun 19, return=Jun 26, duration=8. \
  - **"return X days/weeks later" / "back X afterwards"** → OFFSET semantics, NOT stay length. \
`return_date = departure_date + X`, `trip_duration_days = X + 1` (computed inclusive). \
Example: "Jun 19, returning a week later" → depart=Jun 19, return=Jun 26, duration=8. \
  - **Explicit range "A to B"** → both dates are given by the user, just count: \
`trip_duration_days = (B - A).days + 1`. Example: "Jun 19 to Jun 25" → duration=7. \
**NEVER confuse "N days" with "N nights" — they differ by ONE calendar day.** \
Always show the inclusive-days arithmetic in `reasoning`.

## Core Rules
- Extract ONLY date-relevant parts — ignore passenger counts, preferences, etc. \
E.g. "next Friday for 5 days, 2 adults" → parse "next Friday for 5 days"
- Dates without year: use current/next year (whichever is future)
- Relative dates ("tomorrow", "next Friday", "next week"): calculate from reference_date
  - "next week" / "this week" / "coming week" (no specific day) → \
Mon to Sun of that week (or Mon-Fri for business context — see below). \
Set departure_date, return_date, is_range=True, trip_duration_days. NOT a departure window.
    - **Business context** ("business trip", "work trip", "conference", "meeting", \
"client visit") → Mon-Fri (5 days). \
E.g. "Business trip to NYC for next week" → Mon-Fri, trip_duration_days=5
    - **Otherwise** (leisure, family, vacation, or no context) → Mon-Sun (7 days)
    - **"next week for N days/nights"** → anchor=next Monday, then apply the \
duration convention: return = anchor + (N - 1) for days, anchor + N for nights. \
trip_duration_days = N (days) or N+1 (nights). \
E.g. "next week for 5 days" on ref 2026-05-20 (Wed) → next Monday is \
2026-05-25, return=2026-05-29 (5 days inclusive Mon-Fri), trip_duration_days=5. \
Do NOT respond with an "I couldn't parse" error for this pattern — it's well-defined.
  - "next month" / "this month" (no specific day) → 1st to last day of that month. \
Set departure_date, return_date, is_range=True. NOT a departure window.
- Day-name ranges ("Tue-Thu", "Mon to Wed", "Friday-Sunday", "Wed-Fri"): \
find the NEXT occurrence of the first day from reference_date as departure, \
then the next occurrence of the second day as return. is_range=True. \
  - "Tue-Thu" on ref 2026-04-23 (Wed) → departure=2026-04-28 (next Tue), return=2026-04-30 (Thu)
  - "Fri-Sun" → departure=next Fri, return=next Sun. \
Abbreviated day names (Mon, Tue, Wed, Thu, Fri, Sat, Sun) are valid.
- Date + duration: set departure_date, return_date = departure + (duration - 1), trip_duration_days. \
**Duration is counted in calendar days INCLUSIVE of departure and return** — a "7-day trip" \
covers 7 calendar days, so return = departure + 6. E.g. "March 10 for a week" → \
departure=Mar 10, return=Mar 16, trip_duration_days=7 (Mar 10..16 = 7 days inclusive). \
"5-day trip starting June 1" → departure=Jun 1, return=Jun 5, trip_duration_days=5.
- "after X days/weeks" with reference_date ≠ today: departure_date = reference_date + X. \
Do NOT set trip_duration_days. Infer: "after week"=7, "after month"=30, "after a few days"=3.
- **"in N days/weeks/months"** (relative offset) → departure_date = reference_date + N units. \
E.g. "in 2 weeks" → departure_date=reference+14d. "in a month" → departure_date=reference+30d. \
Set is_range=False unless a return offset follows.
- **"in N + back/return X afterwards/later" pattern** — TWO offsets, both relative to today. \
"back/return X afterwards" is an OFFSET (return = departure + X), distinct from "for X days" \
(stay = X calendar days inclusive). Follow the duration convention strictly: \
"in 2 weeks, back two weeks afterwards" → departure=reference+14d, return=departure+14d, \
is_range=True, **trip_duration_days=15** (15 calendar days inclusive). \
"in a month, returning a week later" → departure=reference+30d, return=departure+7d, \
is_range=True, **trip_duration_days=8**. \
"in 10 days for 5 days" → "for 5 days" is STAY length → return=departure+4 (5 days inclusive), \
**trip_duration_days=5**. \
Do NOT collapse "back X afterwards" into trip_duration_days only — also set return_date.
- **Existing departure context (state-aware parsing)**: If the caller passes \
`departure_date` (i.e. a departure has already been collected) and the new text is a \
SINGLE date with no explicit "departure"/"start"/"from" verb, prefer setting it as the \
**return_date** rather than the departure_date. E.g. existing departure=2026-05-18 + \
"May 22" → set departure_date=null, return_date=2026-05-22 (the post-LLM validator \
will fill departure from context). The validator also handles this as a safety net, \
but the prompt should already prefer this interpretation.
- Vague timeframes: "early [month]" = 3rd, "mid [month]" = 15th, "late [month]" = 25th
- Invalid dates (Feb 30, April 31): set error message
- Colloquial durations: "a couple of days"=2, "a few days"=3, "several days"=5, \
"a week"=7, "a long weekend"=3, "a fortnight"=14, "a month"=30. \
Missing article/number = 1 (e.g. "after week" = 7 days).
- Urgent keywords ("ASAP", "right away", "last minute", "same day", \
"earliest available", "next available") → departure_date=reference_date
- "whenever is cheapest"/"most affordable time" → is_departure_window=True
- Corrections ("change to May 20", "not May, I meant June", "actually June 10 instead") → \
extract the CORRECTED date. If the correction contains a clear month+day or date range, parse it. \
"correction: June 5 to June 12" → departure=Jun 5, return=Jun 12. \
Only set error when NO date at all can be extracted (e.g. "no wait, the week after").
- **"around/near/close to [holiday or date]"** → extract the holiday/date itself. \
"around Christmas" → departure_date=Dec 25. "close to Valentine's Day" → departure_date=Feb 14. \
"near the end of June" → departure_date=Jun 25. Do NOT return null for these.
- **Holiday season / year-spanning**: "over the holidays" / "holiday season" → \
departure_date=Dec 20, return_date=Jan 2, is_range=True. \
"between Christmas and New Year's" → departure_date=Dec 25, return_date=Jan 1, is_range=True. \
"New Year's week" → departure_date=Dec 28, return_date=Jan 3, is_range=True.

## Return-Focused & Checkout Expressions
When user specifies only a return/checkout date without departure:
- "need to be home by the 10th" → return_date=next-month 10th, is_range=False
- "flying back on Friday" → return_date=next Friday
- "checkout on the 15th" → return_date=next-month 15th
- "back by Sunday" → return_date=next Sunday
Set return_date. Do NOT set departure_date (the agent will ask for it).

## Business Travel Patterns
- "Monday to Friday" = weekday range. If reference_date IS that day (e.g. today is Monday), \
start THIS week. Otherwise start NEXT week.
- "midweek" = Wednesday. "overnight trip [day]" = 1 night stay = depart [day], return next day, \
trip_duration_days=2 (2 calendar days inclusive).
- "day trip [day]" = departure only, no return.
- Multi-leg trips ("3 days in Paris then 4 in Rome"): sum all durations for trip_duration_days.

## Holiday Destination Disambiguation
When destination is provided, prefer the LOCAL holiday over the US default:
- "Independence Day" + India → Aug 15 (NOT Jul 4)
- "Independence Day" + Mexico → Sep 16 (NOT Jul 4)
- "National Day" + context → use that country's national day
Without destination: default to US interpretation.

## Date Ranges (is_range=True)
Two specific dates with "to", "-", or "through" → is_range=True with departure_date + return_date.
- "Feb 15-20" → departure=Feb 15, return=Feb 20
- "from May 20 to 25" → departure=May 20, return=May 25 ("from" + specific dates = range, NOT window)

## Numeric Short Forms (DD-MM / DD/MM)
Two integers separated by a hyphen, slash, or dot where BOTH are 1-31 and there is \
NO accompanying month name or year → interpret as a date in short form.

**Disambiguation rule (CRITICAL — read carefully):**
- **First number > 12** → MUST be DD-MM. Only one interpretation is valid. \
E.g. "15-5" → day=15, month=5 → 2026-05-15 (May 15). \
E.g. "23/4" → day=23, month=4 → 2026-04-23.
- **Both numbers 1-12 → GENUINELY AMBIGUOUS** (could be DD-MM or MM-DD). \
Do NOT silently guess. Set ``error="Ambiguous date short form"`` and return \
``departure_date=null``. The agent will ask the user to clarify. \
E.g. "3/7" could be March 7 (US MM-DD) or July 3 (DD-MM). \
E.g. "5-7" could be May 7 or July 5. \
E.g. "12.6" could be December 6 or June 12.
- **NEITHER interpretation valid** (e.g. "31-2" — Feb 31 invalid AND 31 isn't \
a valid month) → set ``error`` and return null.

The reasoning field MUST explicitly state which branch was applied.

**"from X to Y" rule**: "from" + specific date + "to" + specific date = ALWAYS is_range=True. \
"from" only signals a departure window when followed by "onwards", "or after", or no end date.

## Night-based Stays
"X night" / "X and Y night" means the guest stays OVERNIGHT on those days. \
Check-in = first named day, check-out = day AFTER the last named day. \
**N nights = N+1 calendar days inclusive (see duration convention above).**
- "Friday night" → check-in Fri, check-out Sat (1 night, trip_duration_days=2)
- "Friday and Saturday night" → check-in Fri, check-out Sun (2 nights, trip_duration_days=3)
- "Thursday through Saturday night" → check-in Thu, check-out Sun (3 nights, trip_duration_days=4)
Return departure_date = check-in, return_date = check-out, is_range=True.


## Weekend References (is_range=True, NOT departure window)
Weekend expressions → concrete date ranges, not departure windows. \
Calculate actual Fri/Sat-Sun dates from reference_date. is_range=True. NEVER return an error.
- "next weekend" → Sat-Sun | "long weekend" → Fri-Sun (include Friday)
- "last weekend of this month" → last Sat-Sun | "first weekend of May" → first Sat-Sun in May

**"weekend" vs "week"** — DIFFERENT:
- "first weekend of May" → is_range=True (specific Fri-Sun dates)
- "first week of May" → is_departure_window=True (May 1-7, flexible departure)

## Seasonal & Holiday Dates
Convert seasonal/holiday references to dates using destination for disambiguation \
(e.g., "cherry blossom" in Japan vs DC, hemisphere for "summer"/"winter").
- With trip_duration_days: pick peak dates, return departure_date only, keep duration
- Without trip_duration_days: return full seasonal range as departure_date + return_date

## Month + Year Only (NOT a departure window)
Month name only (no day, no flexibility signal) → departure_date=YYYY-MM-01, is_departure_window=False. \
Flexibility signals ("anytime in", "sometime in", "flexible") CHANGE it to a departure window:
- "October 2026" / "in April" → departure_date=01, is_departure_window=False
- "anytime in April" → is_departure_window=True, start=Apr 1, end=Apr 30

## Departure Window (is_departure_window=True)
Triggered by flexibility language ("anytime", "sometime", "flexible") or named periods \
("first week of", "last week of", "first half of"). Do NOT set departure_date or return_date.

**Bounded** (start + end): departure_window_start + departure_window_end.
- "first week of May" → start=May 1, end=May 7
- "after April 20, before April 25" → start=Apr 21, end=Apr 24

**Open-ended** (no end): departure_window_start only, end=null.
- "April 28 or after" → start=Apr 28, end=null
- "from May 1 onwards" → start=May 1, end=null

## Disambiguation Priority (check in order)
1. Two specific dates with "to"/"-"/"through" → is_range=True
2. "weekend" (not "week") → is_range=True (Fri/Sat-Sun)
3. Flexibility language or named periods ("first week") → is_departure_window=True
4. "onwards"/"or after" with no end → is_departure_window=True (open-ended)
5. Single date + duration → is_range=True + trip_duration_days
6. Month name only → departure_date=YYYY-MM-01
7. Single date or relative time → departure_date only

When is_departure_window=True: do NOT set departure_date or return_date.

## Common Mistakes (WRONG → RIGHT)
- ❌ Easter 2026 when reference_date is 2026-04-20 (Easter Apr 5 is PAST) → ✅ Easter 2027 = 2027-03-28
- ❌ "summer" + Sydney → Jun-Aug (that's NORTHERN) → ✅ Dec-Feb (southern hemisphere)
- ❌ "first week of May" → is_range=True → ✅ is_departure_window=True, start=May 1, end=May 7
- ❌ "from May 1 onwards" → departure_date=May 1 → ✅ is_departure_window=True, start=May 1, end=null
- ❌ "Feb 15-20" → is_range=False → ✅ is_range=True (two dates with "-")
- ❌ "anytime in June" → departure_date=Jun 1 → ✅ is_departure_window=True, start=Jun 1, end=Jun 30

## Few-Shot Examples
(reference_date=2026-04-20 for all examples)

**Example 1 — Date range with duration ("N days"):**
Input: "May 10 for a week"
reasoning: "May 10 2026 is future (after Apr 20). Duration 'a week' = 7 calendar days inclusive. \
Return = May 10 + (7 - 1) = May 16."
→ departure_date=2026-05-10, return_date=2026-05-16, is_range=true, trip_duration_days=7

**Example 1b — N nights stay (different from N days):**
Input: "May 10 for 7 nights"
reasoning: "Stay = 7 nights = 8 calendar days inclusive (depart Sat May 10, sleep 7 nights, \
checkout Sat May 17). Return = May 10 + 7 = May 17."
→ departure_date=2026-05-10, return_date=2026-05-17, is_range=true, trip_duration_days=8

**Example 1c — Offset semantics ("X days later"):**
Input: "Jun 19, returning a week later"
reasoning: "Jun 19 2026 is future. 'A week later' = offset = +7 days. \
Return = Jun 19 + 7 = Jun 26. Inclusive calendar days = 8."
→ departure_date=2026-06-19, return_date=2026-06-26, is_range=true, trip_duration_days=8

**Example 2 — Holiday (past → next year):**
Input: "during Easter" (destination: Not specified)
reasoning: "Easter 2026 = Apr 5. Apr 5 < Apr 20 (reference), so past. Next: Easter 2027 = Mar 28. \
No trip_duration_days, so return full range: Mar 28 to Apr 3 (Easter week = 7 days inclusive)."
→ departure_date=2027-03-28, return_date=2027-04-03, is_range=true, trip_duration_days=7

**Example 3 — Seasonal with destination:**
Input: "cherry blossom season" (destination: Tokyo, Japan)
reasoning: "Cherry blossom in Japan ≈ Mar 25 - Apr 10. In 2026, Apr 10 < Apr 20 → season ended. \
Next occurrence: 2027-03-25 to 2027-04-10."
→ departure_date=2027-03-25, return_date=2027-04-10, is_range=true, trip_duration_days=16

**Example 4 — Departure window (flexible):**
Input: "anytime in June"
reasoning: "'Anytime' = flexibility signal → departure window. June 2026 is future. Window = Jun 1 to Jun 30."
→ is_departure_window=true, departure_window_start=2026-06-01, departure_window_end=2026-06-30

**Example 5 — Open-ended window:**
Input: "from May 1 onwards"
reasoning: "'Onwards' = open-ended window. May 1 is future. Start=May 1, no end date."
→ is_departure_window=true, departure_window_start=2026-05-01, departure_window_end=null

**Example 6 — Correction with clear date:**
Input: "not May, I meant June"
reasoning: "User corrects month from May to June. Extract 'June' → June 1, 2026. Future date ✓."
→ departure_date=2026-06-01

**Example 7 — "Around" a holiday:**
Input: "around Christmas"
reasoning: "'Around' = approximate. Extract core date: Christmas = Dec 25, 2026. Future ✓."
→ departure_date=2026-12-25

**Example 8 — Year-spanning holiday period:**
Input: "over the holidays"
reasoning: "'The holidays' = Christmas/New Year period. Dec 20 to Jan 2 range."
→ departure_date=2026-12-20, return_date=2027-01-02, is_range=true

## Holiday & Event Reference (2026-2027)

### Movable Holidays (2026 / 2027)
Holiday               | 2026          | 2027
----------------------|---------------|---------------
Easter                | Apr 5         | Mar 28
Good Friday           | Apr 3         | Mar 26
Easter Monday         | Apr 6         | Mar 29
Ash Wednesday         | Feb 18        | Feb 10
Mardi Gras            | Feb 17        | Feb 9
Carnival              | Feb 13-17     | Feb 5-9
Pentecost/Whit Monday | May 25        | May 17
MLK Day               | Jan 19        | Jan 18
Presidents' Day       | Feb 16        | Feb 15
Memorial Day          | May 25        | May 31
Labor Day             | Sep 7         | Sep 6
Columbus Day          | Oct 12        | Oct 11
Thanksgiving (US)     | Nov 26        | Nov 25
Black Friday          | Nov 27        | Nov 26
Cyber Monday          | Nov 30        | Nov 29
Canadian Thanksgiving | Oct 12        | Oct 11
King's Birthday (AU)  | Jun 8         | Jun 14
Matariki (NZ)         | Jul 10        | Jun 25
Ramadan               | Feb 18-Mar 19 | Feb 8-Mar 9
Eid al-Fitr           | Mar 20-22     | Mar 10-12
Eid al-Adha           | May 27-30     | May 17-20
Diwali                | Nov 8         | Oct 29
Holi                  | Mar 14        | Mar 3
Chinese New Year      | Feb 17        | Feb 6
Songkran (Thailand)   | Apr 13-15     | Apr 13-15
Tet (Vietnam)         | Feb 17-23     | Feb 6-12
Vesak                 | May 1         | May 20
Dussehra              | Oct 20        | Oct 9
Navratri              | Oct 11-19     | Sep 30-Oct 9
Ganesh Chaturthi      | Sep 14        | Sep 3
Onam                  | Aug 16-26     | Sep 1-11
Raksha Bandhan        | Aug 28        | Aug 17
Loy Krathong (TH)     | Nov 25        | Nov 14
Yi Peng (Chiang Mai)  | Nov 25-27     | Nov 14-16
Thaipusam             | —             | Jan 22
Golden Week (Japan)   | Apr 29-May 5  | Apr 29-May 5
Fallas (Valencia)     | Mar 15-19     | Mar 15-19
Inti Raymi (Cusco)    | Jun 24        | Jun 24
Day of the Dead       | Nov 1-2       | Nov 1-2
Vendimia (Mendoza)    | —             | Mar 1-8

### Major Events (2026 / 2027)
Event                  | 2026          | 2027
-----------------------|---------------|---------------
Super Bowl             | Feb 8         | Feb 14
SXSW                   | Mar 13-22     | Mar 12-21
Coachella              | Apr 10-19     | Apr 9-18
Vivid Sydney           | May 22-Jun 13 | May 28-Jun 19
Glastonbury            | —             | Jun 23-27
Wimbledon              | Jun 29-Jul 12 | Jun 28-Jul 11
Edinburgh Fringe       | Aug 7-31      | Aug 6-30
Oktoberfest            | Sep 19-Oct 4  | Sep 18-Oct 3
Art Basel Miami        | Dec 3-7       | Dec 2-6
Web Summit (Lisbon)    | Nov 2-5       | Nov 1-4
Dubai Expo             | Oct 1-31      | Oct 1-31
World Cup 2026         | Jun 11-Jul 19 | —
NYFW                   | Sep 10-17     | Sep 9-16
Milan Fashion Week     | Sep 22-28     | Sep 21-27
Paris Fashion Week     | Sep 28-Oct 6  | Sep 27-Oct 5
Tour de France         | Jul 4-26      | Jul 3-25

### Seasons by Destination
Season/Activity    | Region              | Dates
-------------------|---------------------|------------------
Spring             | Northern hemisphere | Mar 1 - May 31
Summer             | Northern hemisphere | Jun 1 - Aug 31
Autumn/Fall        | Northern hemisphere | Sep 1 - Nov 30
Winter             | Northern hemisphere | Dec 1 - Feb 28
Summer             | Southern hemisphere | Dec 1 - Feb 28
Winter             | Southern hemisphere | Jun 1 - Aug 31
Autumn             | Southern hemisphere | Mar 1 - May 31
Spring             | Southern hemisphere | Sep 1 - Nov 30
Cherry blossom     | Japan               | Mar 25 - Apr 10
Cherry blossom     | Washington DC       | Mar 20 - Apr 12
Autumn foliage     | New England/Vermont | Sep 15 - Oct 31
Autumn foliage     | Japan               | Oct 25 - Dec 5
Ski season         | Alps/Colorado       | Nov 15 - Apr 15
Ski season         | Japan               | Dec 1 - Mar 31
Ski season         | New Zealand         | Jun 1 - Sep 30
Monsoon            | India               | Jun 1 - Sep 30
Monsoon/Rainy      | Thailand/SE Asia    | May 15 - Oct 31
Dry season         | Bali                | Apr 1 - Oct 31
Dry season         | Costa Rica          | Dec 1 - Apr 30
Peak season        | Maldives            | Nov 1 - Apr 30
Peak season        | Caribbean           | Dec 15 - Apr 15
Peak season        | Europe              | Jun 1 - Aug 31
Off season         | Europe              | Nov 1 - Mar 31
Shoulder season    | Europe              | Apr 1 - May 31
Northern lights    | Iceland/Norway      | Sep 15 - Mar 15
Tulip season       | Netherlands         | Mar 15 - May 15
Lavender           | Provence            | Jun 15 - Aug 15
Safari (migration) | Kenya               | Jul 1 - Oct 31
Safari             | Tanzania            | Jun 1 - Sep 30
Whale watching     | Iceland             | Jun 15 - Aug 31
Whale watching     | Hawaii              | Dec 1 - Apr 30
School spring break| US/UK               | Mar 15 - Mar 29
School summer break| US/UK               | Jun 15 - Aug 31
Winter break       | US/UK               | Dec 20 - Jan 3

## Date Expression
"{text}"
"""


class DateInput(BaseModel):
    """Input schema for date parsing."""

    text: str = Field(
        description="Text containing date references (e.g., 'next Tuesday', 'Jan 15-20', 'tomorrow', 'March for 7 days', 'January 15 for 2 weeks', 'cherry blossom season')"
    )
    departure_date: str | None = Field(
        None,
        description="Optional departure date in YYYY-MM-DD format. If provided and text is 'after X days', will calculate return date from this departure.",
    )
    destination: str | None = Field(
        None,
        description="Optional destination city/country for seasonal date disambiguation (e.g., 'Tokyo', 'Tokyo, Japan', 'New England'). Important for seasonal references like 'cherry blossom season' or 'autumn foliage'.",
    )


class DateParsingResult(BaseModel):
    """Structured output for LLM-based date parsing."""

    reasoning: str = Field(
        description=(
            "Step-by-step reasoning BEFORE setting date fields. Show: "
            "1) What the expression means, 2) Calculate the date, "
            "3) Check: is it ≥ reference_date? If not → next year. "
            "4) Final answer. Example: 'Easter 2026 = Apr 5. "
            "Apr 5 < Apr 20 (ref) → past. Next: Easter 2027 = Mar 28.'"
        ),
    )
    departure_date: str | None = Field(
        None, description="Departure date in YYYY-MM-DD format"
    )
    return_date: str | None = Field(
        None, description="Return date in YYYY-MM-DD format (if range provided)"
    )
    is_range: bool = Field(
        False, description="Whether this is a date range (e.g., 'Feb 15-20')"
    )
    trip_duration_days: int | None = Field(
        None, description="Trip duration in days if mentioned (e.g., 'for 7 days')"
    )
    error: str | None = Field(
        None, description="Error message if date cannot be parsed"
    )
    # Departure window fields — flexible departure date range (one-way only)
    departure_window_start: str | None = Field(
        None,
        description="Start of flexible departure window in YYYY-MM-DD (inclusive)",
    )
    departure_window_end: str | None = Field(
        None,
        description=(
            "End of flexible departure window in YYYY-MM-DD (inclusive). "
            "Null for open-ended windows (e.g. 'April 28 or after') — "
            "the validator auto-fills this with departure_window_start + MAX_DEPARTURE_WINDOW_DAYS."
        ),
    )
    is_departure_window: bool = Field(
        False,
        description=(
            "True when user gives a flexible departure window "
            "(e.g. 'after April 20, before April 25', 'between April 21 and 24', "
            "'sometime next week'). NOT round-trip — this is a range of possible "
            "departure dates."
        ),
    )


def _try_deterministic_parse(text: str, reference_date: str) -> dict[str, Any] | None:
    """Try to parse trivial date expressions deterministically without LLM.

    Handles keywords like "now", "today", "tonight", "tomorrow" that should
    never be sent to the LLM — they have unambiguous meanings.

    Supports optional duration suffix: "now for 3 nights", "today for 1 week".

    Returns:
        Parsed result dict if matched, or None to fall through to LLM.
    """
    normalized = text.strip().lower()

    # Fast-path: already a valid ISO date (YYYY-MM-DD) — no LLM needed.
    # update_trip_info passes already-parsed ISO dates through parse_dates as a
    # safety net; this avoids an unnecessary LLM call in that path.
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text.strip()):
        try:
            date.fromisoformat(text.strip())
            return {
                "departure_date": text.strip(),
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": text,
                "instruction": "Dates parsed successfully. Proceed with the search.",
            }
        except ValueError:
            pass  # fall through to LLM parsing

    # Quarter references: "Q3", "Q3 2027", "q1"
    quarter_match = re.match(r"^q([1-4])(?:\s+(\d{4}))?\s*$", normalized)
    if quarter_match:
        q = int(quarter_match.group(1))
        year = int(quarter_match.group(2)) if quarter_match.group(2) else None
        quarter_months = {
            1: "January-March",
            2: "April-June",
            3: "July-September",
            4: "October-December",
        }
        quarter_examples = {
            1: "e.g. Jan 15-18",
            2: "e.g. May 5-8",
            3: "e.g. Jul 10-13",
            4: "e.g. Oct 20-23",
        }
        ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
        if year is None:
            quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
            year = ref.year if ref.month <= quarter_end_months[q] else ref.year + 1
        label = f"Q{q} {year}"
        logger.info(
            "Deterministic parse '%s' -> %s (%s)", text, label, quarter_months[q]
        )
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": None,
            "error": None,
            "parsed_from": text,
            "instruction": (
                f"{label} is {quarter_months[q]}. "
                f"Ask the user for specific dates ({quarter_examples[q]}). "
                f"Also ask for any OTHER missing required fields (e.g. destination) in the same message."
            ),
        }

    # Match: "now/today/tonight" optionally followed by "for X night(s)/day(s)/week(s)"
    pattern = (
        r"^(?:from\s+)?"
        r"(now|today|tonight|tomorrow)"
        r"(?:\s+for\s+(\d+)\s*(night|nights|day|days|week|weeks))?"
        r"\s*$"
    )
    match = re.match(pattern, normalized)
    if not match:
        return None

    keyword = match.group(1)
    duration_value = int(match.group(2)) if match.group(2) else None
    duration_unit = match.group(3) if match.group(3) else None

    ref = datetime.strptime(reference_date, "%Y-%m-%d").date()

    if keyword in ("now", "today", "tonight"):
        departure = ref
    elif keyword == "tomorrow":
        departure = ref + timedelta(days=1)

    result: dict[str, Any] = {
        "departure_date": departure.strftime("%Y-%m-%d"),
        "return_date": None,
        "is_range": False,
        "trip_duration_days": None,
        "error": None,
        "parsed_from": text,
        "instruction": "Dates parsed successfully. Proceed with the search.",
    }

    if duration_value and duration_unit:
        # Duration convention (aligned with parse_dates LLM prompt):
        #   trip_duration_days = calendar days INCLUSIVE of departure and return.
        #   "N days"   = stay N calendar days  → return = depart + (N - 1)
        #   "N nights" = stay N nights         → return = depart + N      → duration = N + 1
        #   "N weeks"  = stay N*7 days         → return = depart + (N*7 - 1)
        if duration_unit.startswith("week"):
            calendar_days = duration_value * 7
            offset = calendar_days - 1
        elif duration_unit.startswith("night"):
            # N nights = N+1 calendar days (depart + N overnight stays + checkout day).
            offset = duration_value
            calendar_days = duration_value + 1
        else:
            # "day" / "days": N calendar days inclusive.
            calendar_days = duration_value
            offset = duration_value - 1

        return_date = departure + timedelta(days=offset)
        result["return_date"] = return_date.strftime("%Y-%m-%d")
        result["is_range"] = True
        result["trip_duration_days"] = calendar_days

    logger.info(
        "Deterministic parse '%s' -> departure=%s, return=%s, duration=%s",
        text,
        result["departure_date"],
        result.get("return_date"),
        result.get("trip_duration_days"),
    )
    return result


_ABBREVIATION_MAP = {
    r"\bwknd\b": "weekend",
    r"\bweeknd\b": "weekend",
    r"\bwk\b": "week",
    r"\btmrw\b": "tomorrow",
    r"\btmw\b": "tomorrow",
    r"\bmon\b": "Monday",
    r"\btue\b": "Tuesday",
    r"\bwed\b": "Wednesday",
    r"\bthu\b": "Thursday",
    r"\bfri\b": "Friday",
    r"\bsat\b": "Saturday",
    r"\bsun\b": "Sunday",
}


def _normalize_abbreviations(text: str) -> str:
    """Expand common date abbreviations so smaller LLMs can parse them."""
    result = text
    for pattern, replacement in _ABBREVIATION_MAP.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    if result != text:
        logger.info("Normalized abbreviations: '%s' -> '%s'", text, result)
    return result


async def _parse_dates_with_llm(
    text: str,
    reference_date: str | None = None,
    destination: str | None = None,
    trip_duration_days: int | None = None,
) -> dict[str, Any]:
    """Parse dates using LLM with structured output.

    This replaces the old library-based approach with a flexible LLM-based approach
    that can handle ambiguous dates and natural language better.

    Tries deterministic parsing first for trivial expressions (now, today, tomorrow).
    Falls through to LLM for complex expressions.

    Args:
        text: Natural language date expression
        reference_date: Today's date in YYYY-MM-DD format (defaults to current date)
        destination: Destination city/country for seasonal date disambiguation (e.g., "Tokyo, Japan")
        trip_duration_days: Expected trip duration to constrain seasonal date ranges (e.g., 14)

    Returns:
        Dict with departure_date, return_date, is_range, trip_duration_days, error
    """
    if reference_date is None:
        reference_date = utc_date().strftime("%Y-%m-%d")

    # Quick sanity check: reject input that contains no date-like tokens at all.
    # Prevents the LLM from hallucinating dates (e.g. "next week") when the user
    # said something like "I want to visit Beijing and Shanghai".
    if not _DATE_HINT_PATTERN.search(text):
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": None,
            "error": "no_date_found",
            "parsed_from": text,
            "instruction": (
                "No date or time expression found in the text. "
                "Ask the user for their travel dates."
            ),
        }

    # Try deterministic parsing first — avoids LLM for trivial expressions
    deterministic = _try_deterministic_parse(text, reference_date)
    if deterministic is not None:
        return deterministic

    # Duration-only text ("5 days", "a week trip") — no date anchor.
    # Return duration info without calling LLM; instruct agent to ask for
    # departure date instead of letting the LLM auto-pick one.
    if _DURATION_ONLY_PATTERN.match(text.strip()):
        num = _extract_duration_days(text)
        logger.info("Duration-only input '%s' -> %s days, no departure date", text, num)
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": num,
            "error": None,
            "parsed_from": text,
            "instruction": (
                f"The user specified a duration ({num} days) but no departure date. "
                "Ask ONLY for the departure date — do NOT re-ask duration or destination."
            ),
        }

    # Broader duration-without-date check: catches duration embedded in longer text
    # like "4-day trip to Rome" or "a week vacation to Tokyo" where the strict
    # _DURATION_ONLY_PATTERN doesn't match (it only handles standalone duration).
    stripped = text.strip()
    if _HAS_DURATION.search(stripped) and not _HAS_EXPLICIT_DATE_ANCHOR.search(
        stripped
    ):
        num = _extract_duration_days(text)
        logger.info("Duration-without-date-anchor input '%s' -> %s days", text, num)
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": num,
            "error": None,
            "parsed_from": text,
            "instruction": (
                f"The user specified a duration ({num} days) but no departure date. "
                "Ask ONLY for the departure date — do NOT re-ask duration or destination."
            ),
        }

    # Normalize common abbreviations before sending to LLM —
    # smaller LLM models struggle with informal spelling.
    text = _normalize_abbreviations(text)

    from app.ai.graph.llm_factory import create_llm

    try:
        llm = create_llm("tool_dates", temperature=0.0)
    except ValueError as e:
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": None,
            "error": str(e),
        }

    # Fetch prompt from Langfuse (with fallback to hardcoded)
    try:
        from app.ai.prompt_management import get_date_parse_prompt

        prompt_template = get_date_parse_prompt()
    except Exception as e:
        logger.warning("Failed to fetch date parse prompt from Langfuse: %s", e)
        prompt_template = DATE_PARSE_PROMPT

    # Format prompt with all context
    prompt_text = prompt_template.format(
        reference_date=reference_date,
        text=text,
        destination=destination or "Not specified",
        trip_duration_days=trip_duration_days or "Not specified",
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", prompt_text), ("human", "Parse the date expression.")]
    )

    chain = prompt | llm.with_structured_output(DateParsingResult)

    try:
        result = await chain.ainvoke({})
        # `with_structured_output(DateParsingResult)` returns the Pydantic
        # model in production; tests sometimes mock it. Duck-type model_dump()
        # to satisfy mypy's `dict | BaseModel` union without breaking mocks.
        result_dict: dict[str, Any] = (
            result.model_dump() if hasattr(result, "model_dump") else dict(result)
        )

        # Log CoT reasoning and results for debugging
        reasoning = result_dict.pop("reasoning", None)
        logger.info(
            "LLM parsed '%s' -> reasoning=%s, departure=%s, return=%s, duration=%s, window=%s/%s/%s",
            text,
            reasoning,
            result_dict.get("departure_date"),
            result_dict.get("return_date"),
            result_dict.get("trip_duration_days"),
            result_dict.get("is_departure_window"),
            result_dict.get("departure_window_start"),
            result_dict.get("departure_window_end"),
        )

        # Add parsed_from field for backward compatibility
        result_dict["parsed_from"] = text
        # Pass reference_date to validator for consistent past-date checks
        result_dict["_reference_date"] = reference_date

        # Add instruction field for agent
        if result_dict.get("error"):
            result_dict["instruction"] = (
                "Inform the user about the date parsing error and ask for clarification."
            )
        elif result_dict.get("is_departure_window"):
            # Placeholder — _validate_parsed_dates will replace with chunk-aware instruction
            result_dict["instruction"] = "Departure window detected."
        elif _AMBIGUOUS_RELATIVE_PATTERNS.search(text):
            # Ambiguous relative expression (next weekend, next week, etc.)
            # — confirm resolved dates with the user before proceeding.
            dep = result_dict.get("departure_date")
            ret = result_dict.get("return_date")
            if not dep:
                result_dict["instruction"] = (
                    "Could not resolve dates from that expression. "
                    "Ask the user for specific dates."
                )
            elif not ret:
                # Departure resolved but no return — auto-fill duration for week
                # phrases so the agent has a usable range to confirm.
                # Business trips default to Mon-Fri (5 days), leisure to Mon-Sun (7).
                from datetime import datetime as _dt
                from datetime import timedelta as _td

                week_match = re.search(
                    r"\b(?:next|this|coming)\s+week\b", text, re.IGNORECASE
                )
                if week_match:
                    is_business = bool(_BUSINESS_CONTEXT_PATTERN.search(text))
                    duration = 5 if is_business else 7
                    try:
                        dep_d = _dt.strptime(dep, "%Y-%m-%d").date()
                        ret_d = dep_d + _td(days=duration - 1)
                        ret = ret_d.strftime("%Y-%m-%d")
                        result_dict["return_date"] = ret
                        result_dict["is_range"] = True
                        result_dict["trip_duration_days"] = duration
                    except ValueError:
                        pass
                if ret:
                    duration = result_dict.get("trip_duration_days") or 7
                    context_note = (
                        "business week, Mon-Fri" if duration == 5 else "next week"
                    )
                    result_dict["instruction"] = (
                        f"Dates inferred from ambiguous expression: {dep} to {ret} "
                        f"({duration} days, {context_note}). "
                        f"⚠️ Do NOT generate the itinerary yet. FIRST send a TEXT "
                        f"message acknowledging the inferred dates AND asking for any "
                        f"other missing required fields (destination if vague like "
                        f"'beach vacation', passengers, etc.) in the SAME message. "
                        f"Example with concrete destination: 'I've got {dep} to {ret} "
                        f"({context_note}) — does that work?' "
                        f"Example with vague destination: 'Got dates {dep} to {ret} "
                        f"({context_note}). Which specific city for your trip?' "
                        f"Wait for the user's reply before calling generate_itinerary."
                    )
                else:
                    result_dict["instruction"] = (
                        f"Departure {dep} resolved but no return date. "
                        f"Ask ONLY for return date or duration."
                    )
            else:
                _trip_dur: Any = result_dict.get("trip_duration_days")
                duration_note = f" ({_trip_dur} days)" if _trip_dur else ""
                result_dict["instruction"] = (
                    f"Dates inferred from ambiguous expression: {dep} to {ret}{duration_note}. "
                    f"⚠️ Do NOT generate the itinerary yet. FIRST send a TEXT message "
                    f"acknowledging the inferred dates AND asking for any other missing "
                    f"required fields (destination if vague, passengers) in the SAME "
                    f"message. Example: "
                    f"'I've got {dep} to {ret}{duration_note} — does that work? "
                    f"<and any other missing-field question here>' "
                    f"Wait for the user's reply before calling generate_itinerary."
                )
        elif (
            result_dict.get("departure_date")
            and not result_dict.get("return_date")
            and _MONTH_ONLY_PATTERN.match(text)
            and result_dict["departure_date"].endswith("-01")
        ):
            # Month-only input like "october 2026" — don't assume day 1
            month_label = text.strip()
            result_dict["instruction"] = (
                f"The user only specified a month ('{month_label}'), not specific dates. "
                f"Do NOT assume the 1st of the month. "
                f"Ask: 'What specific dates in {month_label} are you thinking?'"
            )
        elif result_dict.get("departure_date") and not result_dict.get("return_date"):
            result_dict["instruction"] = (
                "Only a departure/check-in date was parsed (no return/check-out date). "
                "If the user already provided duration or an end date, trust that — "
                "do NOT re-ask. Otherwise ask ONLY for the missing end date or duration."
            )
        else:
            result_dict["instruction"] = (
                "Dates parsed successfully. Proceed with the search."
            )

        return result_dict
    except Exception as e:
        logger.error("LLM date parsing failed for '%s': %s", text, e)
        return {
            "departure_date": None,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": None,
            "error": f"Could not parse date from: '{text}'",
            "parsed_from": text,
            "_reference_date": reference_date,
            "instruction": "Inform the user the date could not be parsed and ask them to rephrase.",
        }


@tool("parse_dates", args_schema=DateInput)
async def parse_dates(
    text: str, departure_date: str | None = None, destination: str | None = None
) -> dict[str, Any]:
    """Parse dates from natural language using LLM.

    Use this tool when the user mentions travel dates to extract
    departure and return dates in YYYY-MM-DD format.

    Args:
        text: Date expression to parse
        departure_date: Optional departure date for context. If provided and text is "after X days",
                       will calculate return date from this departure date.
        destination: Optional destination for seasonal date disambiguation (e.g., "Tokyo", "New England").
                    Important for seasonal references like "cherry blossom season" or "autumn foliage".

    Note:
        This tool intentionally does NOT expose trip_duration_days parameter (available in
        _parse_dates_with_llm). Rationale: Hotel/flight agents need full seasonal ranges,
        while planning agent needs duration constraints and calls _parse_dates_with_llm directly.

    Handles:
    - Relative: "tomorrow", "next Tuesday", "in 2 weeks"
    - Absolute: "January 15", "15/01/2025", "Jan 15th"
    - Ranges: "Monday to Friday", "15th for a week", "Dec 5-10"
    - Full date ranges: "December 20, 2025 to December 25, 2025"
    - Duration-based: "March for 7 days", "January 15 for 2 weeks"
    - Colloquial: "a couple of days", "a long weekend", "early March"
    - Seasonal: "cherry blossom season", "autumn foliage", "monsoon season"
    - Invalid dates: "Feb 30", "April 31" (returns error)
    - Context-based: "after 10 days" (with departure_date) → calculates return date

    Returns dates in YYYY-MM-DD format ready for flight/hotel search.
    """
    # When text is a "after X days/weeks" offset, use departure_date as the
    # reference anchor so LLM computes return = departure + offset. For ALL
    # other cases the reference is today — using departure_date as reference
    # makes the LLM auto-roll past dates to next year (e.g. "May 15" after a
    # May 18 departure becomes 2027-05-15, a year-long trip — wrong).
    use_dep_as_ref = bool(
        departure_date
        and re.search(
            r"^\s*after\s+(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
            r"(?:day|days|week|weeks|month|months)\b",
            text.lower(),
        )
    )
    reference_date = departure_date if use_dep_as_ref else None
    _t0 = time.monotonic()
    result = await _parse_dates_with_llm(text, reference_date, destination=destination)
    # Demoted to DEBUG post-#1014 — was INFO for the Langfuse trace review and
    # now produces noise on every parse_dates call in production.
    logger.debug(
        "[TIMING] parse_dates.llm_call: %.2fs  text=%r",
        time.monotonic() - _t0,
        text[:60],
    )

    # Pass existing departure_date to the validator so it can swap-to-return
    # (new date AFTER existing) or preserve-and-error (new date BEFORE existing).
    # Fixes Session 2 bug: parse_dates was overwriting an existing departure
    # because it had no state context. See issue #1014.
    if departure_date:
        result["_existing_departure"] = departure_date

    # Deterministic post-LLM validation: catch dates the LLM got wrong
    return _validate_parsed_dates(result)


def _split_into_chunks(start: str, end: str, chunk_size: int = 6) -> list[list[str]]:
    """Split a date range into chunks of ``chunk_size`` days.

    Args:
        start: Inclusive start date (YYYY-MM-DD).
        end: Inclusive end date (YYYY-MM-DD).
        chunk_size: Maximum dates per chunk (default 6).

    Returns:
        List of chunks, each chunk is a list of YYYY-MM-DD strings.
        Example for Apr 15 → May 5 (chunk_size=6):
          [["2026-04-15"..."2026-04-20"],
           ["2026-04-21"..."2026-04-26"],
           ["2026-04-27"..."2026-05-02"],
           ["2026-05-03"..."2026-05-05"]]
    """
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()

    chunks: list[list[str]] = []
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=chunk_size - 1), end_date)
        chunk: list[str] = []
        d = current
        while d <= chunk_end:
            chunk.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
        chunks.append(chunk)
        current = chunk_end + timedelta(days=1)
    return chunks


def _safe_roll_next_year(d: date) -> date:
    """Roll a date forward to the next year, handling Feb 29 safely."""
    try:
        return d.replace(year=d.year + 1)
    except ValueError:
        # Feb 29 in a leap year → use Feb 28 next year
        return d.replace(year=d.year + 1, day=28)


def _validate_parsed_dates(result: dict[str, Any]) -> dict[str, Any]:
    """Validate parsed dates deterministically after LLM parsing.

    Hard checks that override LLM output:
    - **State-aware swap-to-return**: if caller passed `_existing_departure` AND
      LLM returned a single date strictly AFTER it with no return → swap parsed
      date to `return_date`, restore `departure_date`. Fixes Session 2 (#1014).
    - departure_date in the past → auto-roll to next year (or error if still past)
    - return_date before departure_date → set error, clear return date
    - Force is_range=True when both departure and return dates present
    - departure_window: clip start to today if partially past, reject if fully past
    """
    # Use reference_date if present (for benchmark reproducibility),
    # otherwise fall back to real today.
    today = result.pop("_reference_date", None) or utc_date().strftime("%Y-%m-%d")
    existing_dep_str = result.pop("_existing_departure", None)

    # ── Context-aware error instruction ───
    # When parsing fails AND we have an existing departure in context, the agent
    # should NOT invent generic suggestions ("May 15, May 5, May 15-20") that may
    # divert the user from the trip already in progress. Replace the generic
    # instruction with one that references the existing trip.
    if existing_dep_str and result.get("error") and not result.get("departure_date"):
        result["instruction"] = (
            f"The user's input could not be parsed as a date. The trip already has "
            f"departure_date={existing_dep_str} collected. Ask for clarification but "
            f"keep the EXISTING trip context front-and-center. Do NOT suggest dates "
            f"that fall before {existing_dep_str} as new departures. Prefer suggestions "
            f"like: (a) 'Did you mean to give a return date? e.g. {existing_dep_str} + "
            f"N days', (b) 'Did you mean to change the departure?', "
            f"(c) 'Did you mean a specific date in this trip's timeframe?'. "
            f"Quote the existing departure_date={existing_dep_str} verbatim in your reply."
        )

    # ── State-aware swap-to-return ───
    # If the caller already had a departure_date and the LLM returned a NEW
    # single date that lands strictly after the existing departure with no
    # return — interpret it as the RETURN date, not a new departure. Without
    # this, "May 18" said after the agent already collected dep=May 14 would
    # silently overwrite the departure (Session 2 bug).
    if existing_dep_str:
        parsed_dep = result.get("departure_date")
        parsed_ret = result.get("return_date")
        if parsed_dep and not parsed_ret:
            try:
                existing = datetime.strptime(existing_dep_str, "%Y-%m-%d").date()
                new = datetime.strptime(parsed_dep, "%Y-%m-%d").date()
                if new > existing:
                    # SWAP: new date strictly after existing → it's the return
                    logger.info(
                        "swap-to-return: existing_dep=%s, new=%s — interpreting as return",
                        existing_dep_str,
                        parsed_dep,
                    )
                    result["departure_date"] = existing_dep_str
                    result["return_date"] = parsed_dep
                    result["is_range"] = True
                    if not result.get("trip_duration_days"):
                        result["trip_duration_days"] = (new - existing).days
                    result["instruction"] = (
                        "Dates parsed successfully. Proceed with the search."
                    )
                elif new < existing:
                    # NEW DATE BEFORE EXISTING — ambiguous. Likely an LLM hallucination
                    # from prior dialog (e.g. user said "1" and LLM resolved it to a
                    # date from a previous list). Do NOT overwrite the existing
                    # departure; surface the conflict so the agent can ask the user.
                    logger.info(
                        "parse_dates ambiguous: new=%s < existing_dep=%s — preserving existing",
                        parsed_dep,
                        existing_dep_str,
                    )
                    result["departure_date"] = existing_dep_str
                    result["return_date"] = None
                    result["error"] = (
                        f"Could not unambiguously parse a new date — '{parsed_dep}' lands "
                        f"before the existing departure ({existing_dep_str})."
                    )
                    result["instruction"] = (
                        f"The user's input could not be resolved to a coherent new date. "
                        f"Existing departure_date={existing_dep_str} is preserved. "
                        f"Ask the user explicitly: 'Did you want to change the departure "
                        f"date, or were you giving me the return date?' Do NOT silently "
                        f"overwrite the departure."
                    )
                # else new == existing — no-op (user re-stated existing departure)
            except (ValueError, TypeError):
                pass

    dep = result.get("departure_date")
    ret = result.get("return_date")

    if dep:
        try:
            dep_date = datetime.strptime(dep, "%Y-%m-%d").date()
            today_date = datetime.strptime(today, "%Y-%m-%d").date()

            if dep_date < today_date:
                if ret:
                    try:
                        ret_date = datetime.strptime(ret, "%Y-%m-%d").date()
                        if ret_date >= today_date:
                            # Mid-season: departure is past but return is future
                            # Shift departure to today so the range is still usable.
                            logger.info(
                                "Past departure %s with future return %s — shifting departure to today (%s)",
                                dep,
                                ret,
                                today,
                            )
                            result["departure_date"] = today
                            dep = today
                            # Don't return — fall through to is_range enforcement below
                        else:
                            # Both departure AND return are past — roll both to next year
                            delta = ret_date - dep_date
                            rolled = _safe_roll_next_year(dep_date)
                            rolled_ret = rolled + delta
                            if rolled >= today_date:
                                logger.info(
                                    "Past range %s to %s — auto-rolled to %s to %s",
                                    dep,
                                    ret,
                                    rolled.strftime("%Y-%m-%d"),
                                    rolled_ret.strftime("%Y-%m-%d"),
                                )
                                result["departure_date"] = rolled.strftime("%Y-%m-%d")
                                result["return_date"] = rolled_ret.strftime("%Y-%m-%d")
                                dep = result["departure_date"]
                                ret = result["return_date"]
                            # else: fall through to single-date auto-roll below
                    except ValueError:
                        pass

                # If departure is still past (no return, or roll above didn't apply)
                dep_date = datetime.strptime(
                    result.get("departure_date", dep), "%Y-%m-%d"
                ).date()
                if dep_date < today_date:
                    # Auto-roll forward until date is in the future
                    rolled = _safe_roll_next_year(dep_date)
                    while rolled < today_date and rolled.year <= today_date.year + 5:
                        rolled = _safe_roll_next_year(rolled)
                    if rolled >= today_date:
                        logger.info(
                            "Past departure %s — auto-rolled to next year: %s",
                            dep,
                            rolled.strftime("%Y-%m-%d"),
                        )
                        result["departure_date"] = rolled.strftime("%Y-%m-%d")
                        dep = result["departure_date"]
                        # Roll return date too if present and also past
                        if ret:
                            try:
                                ret_date = datetime.strptime(ret, "%Y-%m-%d").date()
                                if ret_date < today_date:
                                    delta = ret_date - dep_date
                                    rolled_ret = rolled + delta
                                    result["return_date"] = rolled_ret.strftime(
                                        "%Y-%m-%d"
                                    )
                                    ret = result["return_date"]
                            except ValueError:
                                pass
                    else:
                        # Even next year is past (shouldn't happen, but safety net)
                        logger.warning(
                            "LLM returned past departure date %s, even next year %s is past",
                            dep,
                            rolled.strftime("%Y-%m-%d"),
                        )
                        result["departure_date"] = None
                        result["error"] = (
                            f"The departure date {dep} is in the past "
                            f"(today is {today}). Please provide a future date."
                        )
                        result["instruction"] = (
                            "Tell the user the date is in the past and ask ONLY for "
                            "new dates. Do NOT re-ask for other fields already "
                            "extracted from the message."
                        )
                        return result
        except ValueError:
            pass  # Can't parse — let downstream handle it

    if dep and ret:
        try:
            dep_date = datetime.strptime(dep, "%Y-%m-%d").date()
            ret_date = datetime.strptime(ret, "%Y-%m-%d").date()

            # Force is_range when both dates are present (LLM sometimes forgets)
            if not result.get("is_range"):
                result["is_range"] = True

            if ret_date < dep_date:
                # Year-spanning season/range: if return month is well before
                # departure month, the LLM likely forgot to bump the year
                # (e.g. Nov-Apr Maldives peak). Require month_gap >= 2 to
                # avoid false positives on adjacent-month reversals (Nov→Oct).
                rolled_ret = _safe_roll_next_year(ret_date)
                month_gap = dep_date.month - ret_date.month
                if month_gap >= 2 and rolled_ret > dep_date:
                    logger.info(
                        "Year-spanning range: return %s < departure %s — "
                        "auto-rolled return to %s",
                        ret,
                        dep,
                        rolled_ret.strftime("%Y-%m-%d"),
                    )
                    result["return_date"] = rolled_ret.strftime("%Y-%m-%d")
                    ret = result["return_date"]
                else:
                    # Suggest corrected date (same weekday, next week after departure)
                    corrected = ret_date + timedelta(days=7)
                    while corrected <= dep_date:
                        corrected += timedelta(days=7)
                    corrected_str = corrected.strftime("%Y-%m-%d")
                    logger.warning(
                        "Return %s before departure %s — suggesting %s",
                        ret,
                        dep,
                        corrected_str,
                    )
                    result["return_date"] = None
                    result["error"] = (
                        f"The return date ({ret}) is before the departure date ({dep})."
                    )
                    result["instruction"] = (
                        f"Tell the user: the return date lands before departure. "
                        f"Did you mean {corrected_str} (the {corrected.strftime('%A')} after departure)? "
                        f"Or provide the correct return date."
                    )
        except ValueError:
            pass

    # ── Force is_departure_window for flexibility keywords ───
    parsed_text = result.get("parsed_from", "").lower()
    if (
        dep
        and not ret
        and not result.get("is_departure_window")
        and _FLEXIBILITY_TRIGGERS.search(parsed_text)
    ):
        # Convert single departure_date to a departure window for the month
        try:
            dep_date = datetime.strptime(dep, "%Y-%m-%d").date()
            _, last_day = calendar.monthrange(dep_date.year, dep_date.month)
            result["departure_window_start"] = dep
            result["departure_window_end"] = date(
                dep_date.year, dep_date.month, last_day
            ).strftime("%Y-%m-%d")
            result["is_departure_window"] = True
            result["departure_date"] = None
            dep = None
            logger.info(
                "Flexibility keyword detected in '%s' — converted to departure window",
                parsed_text,
            )
        except ValueError:
            pass

    # ── Departure window validation ──────────────────────────────────
    ws = result.get("departure_window_start")
    we = result.get("departure_window_end")

    # Open-ended window ("April 28 or after"): auto-fill end with MAX window
    if ws and not we and result.get("is_departure_window"):
        try:
            ws_date = datetime.strptime(ws, "%Y-%m-%d").date()
            auto_end = ws_date + timedelta(days=MAX_DEPARTURE_WINDOW_DAYS - 1)
            we = auto_end.strftime("%Y-%m-%d")
            result["departure_window_end"] = we
            logger.info(
                "Open-ended window from %s — auto-set end to %s (%d days)",
                ws,
                we,
                MAX_DEPARTURE_WINDOW_DAYS,
            )
        except ValueError:
            pass

    if ws and we and result.get("is_departure_window"):
        try:
            today_date = datetime.strptime(today, "%Y-%m-%d").date()
            ws_date = datetime.strptime(ws, "%Y-%m-%d").date()
            we_date = datetime.strptime(we, "%Y-%m-%d").date()

            # Reject if end is before start
            if we_date < ws_date:
                result["departure_window_start"] = None
                result["departure_window_end"] = None
                result["is_departure_window"] = False
                result["error"] = (
                    f"Window end {we} is before window start {ws}. "
                    "Please provide a valid date range."
                )
                result["instruction"] = "Ask the user for a valid departure window."
                return result

            # Reject window that exceeds the maximum allowed size
            if (we_date - ws_date).days + 1 > MAX_DEPARTURE_WINDOW_DAYS:
                result["departure_window_start"] = None
                result["departure_window_end"] = None
                result["is_departure_window"] = False
                result["error"] = (
                    f"Departure window too large ({(we_date - ws_date).days + 1} days). "
                    f"Maximum is {MAX_DEPARTURE_WINDOW_DAYS} days."
                )
                result["instruction"] = (
                    f"Ask the user to narrow the departure window (max {MAX_DEPARTURE_WINDOW_DAYS} days)."
                )
                return result

            # Clip start to today if partially in the past
            if ws_date < today_date <= we_date:
                logger.info(
                    "Departure window start %s in past — clipping to today %s",
                    ws,
                    today,
                )
                ws = today
                ws_date = today_date
                result["departure_window_start"] = today

            # Reject if entire window is in the past
            if we_date < today_date:
                result["departure_window_start"] = None
                result["departure_window_end"] = None
                result["is_departure_window"] = False
                result["error"] = (
                    f"The departure window {ws} to {we} is entirely in the past "
                    f"(today is {today}). Please provide future dates."
                )
                result["instruction"] = (
                    "Ask the user for a valid future departure window."
                )
                return result

            # Build instruction with first chunk of dates
            chunks = _split_into_chunks(ws, we, chunk_size=6)
            first_chunk = chunks[0]
            has_more = len(chunks) > 1

            chunk_dates_str = ", ".join(f"'{d}'" for d in first_chunk)
            instruction = (
                f"Departure window detected ({ws} to {we}, "
                f"{(we_date - ws_date).days + 1} days). "
                f"This is a flexible date range — the user is open to any date "
                f"within this window. "
                f"The agent prompt determines trip type — do NOT ask "
                f"for return dates or trip type here. Pass departure_dates "
                f"to the search tool and let the agent prompt rules decide.\n"
                f"Available departure dates for search: [{chunk_dates_str}]\n"
                f"Window end: '{we}'"
            )
            if has_more:
                instruction += (
                    "\nNote: window has more dates beyond this chunk. "
                    "The search tool will indicate has_more=True with next chunk info."
                )
            result["instruction"] = instruction

        except ValueError:
            pass  # Can't parse — let downstream handle it

    return result


__all__ = ["DateInput", "DateParsingResult", "_split_into_chunks", "parse_dates"]
