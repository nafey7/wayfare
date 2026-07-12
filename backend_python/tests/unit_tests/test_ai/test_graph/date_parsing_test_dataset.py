"""Comprehensive date parsing test dataset.

This dataset covers all categories of date expressions users might type
in a travel booking chatbot. Used to test and benchmark parse_dates tool.

Each entry: (input_text, destination, expected_fields)
- expected_fields is a dict of fields to verify in the parse result.
- Use None for "should be set but value depends on current date".
- Use "__ERROR__" for departure_date when parsing should fail.

Reference date for all static expectations: 2026-04-20 (a Monday).
"""

# ============================================================================
# CATEGORY 1: STANDARD DATE FORMATS
# ============================================================================
STANDARD_FORMATS = [
    # ISO format
    ("2026-05-15", None, {"departure_date": "2026-05-15"}),
    ("2026-12-25", None, {"departure_date": "2026-12-25"}),
    # Slash formats
    ("05/15/2026", None, {"departure_date": "2026-05-15"}),
    ("15/05/2026", None, {"departure_date": "2026-05-15"}),
    # Dot format
    ("15.05.2026", None, {"departure_date": "2026-05-15"}),
    # Written out
    ("May 15, 2026", None, {"departure_date": "2026-05-15"}),
    ("15 May 2026", None, {"departure_date": "2026-05-15"}),
    ("May 15th, 2026", None, {"departure_date": "2026-05-15"}),
    ("May 15th 2026", None, {"departure_date": "2026-05-15"}),
    # Without year (should default to 2026 or 2027 based on whether date is past)
    ("May 15", None, {"departure_date": "2026-05-15"}),
    ("May 15th", None, {"departure_date": "2026-05-15"}),
    ("15th May", None, {"departure_date": "2026-05-15"}),
    ("December 25", None, {"departure_date": "2026-12-25"}),
    # Ordinals
    ("the 5th of June", None, {"departure_date": "2026-06-05"}),
    ("June 1st", None, {"departure_date": "2026-06-01"}),
    ("22nd of July", None, {"departure_date": "2026-07-22"}),
    ("3rd August", None, {"departure_date": "2026-08-03"}),
    # Abbreviated months
    ("Jan 10", None, {"departure_date": "2027-01-10"}),
    ("10 Feb 2027", None, {"departure_date": "2027-02-10"}),
    ("Mar 1st, 2027", None, {"departure_date": "2027-03-01"}),
]

# ============================================================================
# CATEGORY 2: RELATIVE DATES
# ============================================================================
RELATIVE_DATES = [
    # Simple relative
    ("today", None, {"departure_date": "2026-04-20"}),
    ("tomorrow", None, {"departure_date": "2026-04-21"}),
    ("tonight", None, {"departure_date": "2026-04-20"}),
    ("day after tomorrow", None, {"departure_date": "2026-04-22"}),
    # Weekdays
    ("next Friday", None, {"departure_date": "2026-04-24"}),
    ("this Saturday", None, {"departure_date": "2026-04-25"}),
    ("next Monday", None, {"departure_date": "2026-04-27"}),
    ("coming Wednesday", None, {"departure_date": "2026-04-22"}),
    # In X days/weeks
    ("in 3 days", None, {"departure_date": "2026-04-23"}),
    ("in a week", None, {"departure_date": "2026-04-27"}),
    ("in 2 weeks", None, {"departure_date": "2026-05-04"}),
    ("in a month", None, {"departure_date": "2026-05-20"}),
    ("in 10 days", None, {"departure_date": "2026-04-30"}),
    # After X days (with departure_date context)
    # These use departure_date="2026-05-01" as reference
    ("after 5 days", None, {"departure_date": "2026-04-25"}),
    # Next week/month
    ("next week", None, {"departure_date": "2026-04-27"}),
    ("next month", None, {"departure_date": "2026-05-01"}),  # first day of next month
]

# ============================================================================
# CATEGORY 3: DATE RANGES
# ============================================================================
DATE_RANGES = [
    # Explicit ranges with "to"
    (
        "May 1 to May 5",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
    (
        "June 10 to June 17",
        None,
        {
            "departure_date": "2026-06-10",
            "return_date": "2026-06-17",
            "is_range": True,
        },
    ),
    # With "through"
    (
        "April 24 through the 26th",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
    (
        "May 1 through May 7",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-07",
            "is_range": True,
        },
    ),
    # With dash
    (
        "May 10-15",
        None,
        {
            "departure_date": "2026-05-10",
            "return_date": "2026-05-15",
            "is_range": True,
        },
    ),
    (
        "Dec 20-27",
        None,
        {
            "departure_date": "2026-12-20",
            "return_date": "2026-12-27",
            "is_range": True,
        },
    ),
    (
        "June 5-12, 2026",
        None,
        {
            "departure_date": "2026-06-05",
            "return_date": "2026-06-12",
            "is_range": True,
        },
    ),
    # Abbreviated range (same month, only day for end)
    (
        "from May 20 to 25",
        None,
        {
            "departure_date": "2026-05-20",
            "return_date": "2026-05-25",
            "is_range": True,
        },
    ),
    # Cross-month
    (
        "April 28 to May 3",
        None,
        {
            "departure_date": "2026-04-28",
            "return_date": "2026-05-03",
            "is_range": True,
        },
    ),
    # Full date range with year
    (
        "December 20, 2026 to January 3, 2027",
        None,
        {
            "departure_date": "2026-12-20",
            "return_date": "2027-01-03",
            "is_range": True,
        },
    ),
    # Natural phrasing
    (
        "from the 5th to the 12th of July",
        None,
        {
            "departure_date": "2026-07-05",
            "return_date": "2026-07-12",
            "is_range": True,
        },
    ),
    (
        "between June 1 and June 10",
        None,
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-06-10",
            "is_range": True,
        },
    ),
    # The production bug case
    (
        "4-24 through the 26th",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 4: DURATION-BASED
# ============================================================================
DURATION_BASED = [
    # Duration convention (#1105): trip_duration_days = calendar days inclusive
    # of departure and return. "N nights" = N+1 calendar days. "N days" = N
    # calendar days. See dates.py "Critical Rules" section 4.
    (
        "May 1 for 3 nights",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-04",  # 3 nights stay → checkout May 4
            "is_range": True,
            "trip_duration_days": 4,  # 4 calendar days inclusive
        },
    ),
    (
        "June 15 for a week",
        None,
        {
            "departure_date": "2026-06-15",
            "return_date": "2026-06-21",  # 7 days inclusive (Jun 15..21)
            "is_range": True,
            "trip_duration_days": 7,
        },
    ),
    (
        "tomorrow for 5 days",
        None,
        {
            "departure_date": "2026-04-21",
            "return_date": "2026-04-25",  # 5 days inclusive (21,22,23,24,25)
            "is_range": True,
            "trip_duration_days": 5,
        },
    ),
    (
        "next Friday for 2 weeks",
        None,
        {
            "departure_date": "2026-04-24",
            "is_range": True,
            "trip_duration_days": 14,
        },
    ),
    (
        "July 1 for a fortnight",
        None,
        {
            "departure_date": "2026-07-01",
            "is_range": True,
            "trip_duration_days": 14,
        },
    ),
    (
        "May 10 for a long weekend",
        None,
        {
            "departure_date": "2026-05-10",
            "is_range": True,
            "trip_duration_days": 3,
        },
    ),
    (
        "August 1 for a couple of days",
        None,
        {
            "departure_date": "2026-08-01",
            "is_range": True,
            "trip_duration_days": 2,
        },
    ),
    (
        "September 15 for a few days",
        None,
        {
            "departure_date": "2026-09-15",
            "is_range": True,
            "trip_duration_days": 3,
        },
    ),
    (
        "October 1 for a month",
        None,
        {
            "departure_date": "2026-10-01",
            "is_range": True,
            "trip_duration_days": 30,
        },
    ),
]

# ============================================================================
# CATEGORY 5: WEEKEND REFERENCES
# ============================================================================
WEEKEND_REFERENCES = [
    # Reference date: Monday 2026-04-20
    (
        "this weekend",
        None,
        {
            "departure_date": "2026-04-25",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
    (
        "next weekend",
        None,
        {
            "is_range": True,
        },
    ),
    (
        "long weekend",
        None,
        {
            "is_range": True,
        },
    ),
    (
        "last weekend of May",
        None,
        {
            "departure_date": "2026-05-30",
            "return_date": "2026-05-31",
            "is_range": True,
        },
    ),
    (
        "first weekend of June",
        None,
        {
            "departure_date": "2026-06-06",
            "return_date": "2026-06-07",
            "is_range": True,
        },
    ),
    (
        "Memorial Day weekend",
        None,
        {
            # Memorial Day 2026 = May 25 (last Monday of May)
            "departure_date": "2026-05-23",
            "return_date": "2026-05-25",
            "is_range": True,
        },
    ),
    (
        "Labor Day weekend",
        None,
        {
            # Labor Day 2026 = Sep 7 (first Monday of September)
            "departure_date": "2026-09-05",
            "return_date": "2026-09-07",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 6: VAGUE / FLEXIBLE DATES
# ============================================================================
FLEXIBLE_DATES = [
    ("early May", None, {"departure_date": "2026-05-03"}),
    ("mid June", None, {"departure_date": "2026-06-15"}),
    ("late July", None, {"departure_date": "2026-07-25"}),
    ("end of August", None, {"departure_date": "2026-08-25"}),
    ("beginning of September", None, {"departure_date": "2026-09-03"}),
    # Flexible / window expressions
    ("anytime in May", None, {"is_departure_window": True}),
    ("sometime in June", None, {"is_departure_window": True}),
    ("flexible dates in July", None, {"is_departure_window": True}),
    (
        "first week of May",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-05-01",
            "departure_window_end": "2026-05-07",
        },
    ),
    (
        "last week of June",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-06-24",
            "departure_window_end": "2026-06-30",
        },
    ),
    (
        "second week of August",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-08-08",
            "departure_window_end": "2026-08-14",
        },
    ),
    # Any weekend in X
    ("any weekend in May", None, {"is_departure_window": True}),
    # Open-ended
    (
        "May 15 or after",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-05-15",
        },
    ),
    (
        "from June 1 onwards",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-06-01",
        },
    ),
]

# ============================================================================
# CATEGORY 7: SEASONS
# ============================================================================
SEASONS = [
    # Northern hemisphere (default) — deterministic parser returns ranges
    (
        "this summer",
        None,
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    (
        "next winter",
        None,
        {
            "departure_date": "2026-12-01",
            "return_date": "2027-02-28",
            "is_range": True,
        },
    ),
    (
        "this spring",
        None,
        {
            "departure_date": "2026-04-20",  # mid-season, start clipped to today
        },
    ),
    (
        "autumn",
        None,
        {
            "departure_date": "2026-09-01",
            "return_date": "2026-11-30",
            "is_range": True,
        },
    ),
    (
        "fall",
        None,
        {
            "departure_date": "2026-09-01",
            "return_date": "2026-11-30",
            "is_range": True,
        },
    ),
    # Destination-aware seasons
    (
        "cherry blossom season",
        "Tokyo",
        {
            "departure_date": "2027-03-25",
            "return_date": "2027-04-10",
            "is_range": True,
        },
    ),
    (
        "cherry blossom season",
        "Washington DC",
        {
            "departure_date": "2027-03-20",
            "return_date": "2027-04-12",
            "is_range": True,
        },
    ),
    (
        "autumn foliage season",
        "Tokyo",
        {
            "departure_date": "2026-10-25",
            "return_date": "2026-12-05",
            "is_range": True,
        },
    ),
    (
        "autumn foliage season",
        "New England",
        {
            "departure_date": "2026-09-15",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "fall foliage",
        "Vermont",
        {
            "departure_date": "2026-09-15",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "monsoon season",
        "India",
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-09-30",
            "is_range": True,
        },
    ),
    (
        "monsoon season",
        "Thailand",
        {
            "departure_date": "2026-05-15",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "dry season",
        "Bali",
        {
            "departure_date": "2026-04-20",  # mid-season, clipped to today
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "wet season",
        "Costa Rica",
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-11-30",
            "is_range": True,
        },
    ),
    # Southern hemisphere
    (
        "summer",
        "Sydney",
        {
            "departure_date": "2026-12-01",
            "return_date": "2027-02-28",
            "is_range": True,
        },
    ),
    (
        "winter",
        "New Zealand",
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    # Ski season
    (
        "ski season",
        "Alps",
        {
            "departure_date": "2026-11-15",
            "return_date": "2027-04-15",
            "is_range": True,
        },
    ),
    (
        "ski season",
        "Japan",
        {
            "departure_date": "2026-12-01",
            "return_date": "2027-03-31",
            "is_range": True,
        },
    ),
    (
        "ski season",
        "Colorado",
        {
            "departure_date": "2026-11-15",
            "return_date": "2027-04-15",
            "is_range": True,
        },
    ),
    # Southern hemisphere ski
    (
        "ski season",
        "New Zealand",
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-09-30",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 8: HOLIDAYS & FESTIVALS
# ============================================================================
HOLIDAYS = [
    # Fixed-date holidays
    ("Christmas", None, {"departure_date": "2026-12-25"}),
    (
        "Christmas week",
        None,
        {
            "is_range": True,
        },
    ),
    ("Christmas Eve", None, {"departure_date": "2026-12-24"}),
    ("New Year's Eve", None, {"departure_date": "2026-12-31"}),
    ("New Year's Day", None, {"departure_date": "2027-01-01"}),
    ("New Year's", None, {"departure_date": "2026-12-31"}),
    ("Valentine's Day", None, {"departure_date": "2027-02-14"}),
    ("St Patrick's Day", None, {"departure_date": "2027-03-17"}),
    ("Halloween", None, {"departure_date": "2026-10-31"}),
    ("Boxing Day", None, {"departure_date": "2026-12-26"}),
    ("Fourth of July", None, {"departure_date": "2026-07-04"}),
    ("Independence Day", None, {"departure_date": "2026-07-04"}),
    ("Bastille Day", "Paris", {"departure_date": "2026-07-14"}),
    # Movable holidays (next future occurrence from 2026-04-20)
    ("Easter", None, {"departure_date": "2027-03-28"}),
    (
        "Easter week",
        None,
        {
            "departure_date": "2027-03-28",
            "return_date": "2027-04-04",
            "is_range": True,
        },
    ),
    ("Good Friday", None, {"departure_date": "2027-03-26"}),
    ("Thanksgiving", None, {"departure_date": "2026-11-26"}),
    (
        "Thanksgiving week",
        None,
        {
            "departure_date": "2026-11-23",
            "return_date": "2026-11-29",
            "is_range": True,
        },
    ),
    ("Canadian Thanksgiving", None, {"departure_date": "2026-10-12"}),
    # Asian holidays
    ("Chinese New Year", None, {"departure_date": "2027-02-06"}),
    ("Lunar New Year", None, {"departure_date": "2027-02-06"}),
    (
        "Golden Week",
        "Tokyo",
        {
            "departure_date": "2026-04-29",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
    ("Songkran", "Bangkok", {"departure_date": "2027-04-13"}),
    ("Diwali", None, {"departure_date": "2026-11-08"}),
    ("Holi", "India", {"departure_date": "2027-03-03"}),
    # Islamic holidays (approximate — lunar calendar, next future from 2026-04-20)
    (
        "Ramadan",
        None,
        {
            "departure_date": "2027-02-08",
            "return_date": "2027-03-09",
            "is_range": True,
        },
    ),
    (
        "Eid al-Fitr",
        None,
        {
            "departure_date": "2027-03-10",
            "return_date": "2027-03-12",
            "is_range": True,
        },
    ),
    (
        "Eid al-Adha",
        None,
        {
            "departure_date": "2026-05-27",
            "return_date": "2026-05-30",
            "is_range": True,
        },
    ),
    # Cultural events/festivals
    (
        "Oktoberfest",
        "Munich",
        {
            "departure_date": "2026-09-19",
            "return_date": "2026-10-04",
            "is_range": True,
        },
    ),
    (
        "Carnival",
        "Rio de Janeiro",
        {
            "departure_date": "2027-02-05",
            "return_date": "2027-02-09",
            "is_range": True,
        },
    ),
    ("Mardi Gras", "New Orleans", {"departure_date": "2027-02-09"}),
    (
        "Day of the Dead",
        "Mexico City",
        {
            "departure_date": "2026-11-01",
            "return_date": "2026-11-02",
            "is_range": True,
        },
    ),
    ("Nowruz", "Iran", {"departure_date": "2027-03-21"}),
    ("Anzac Day", "Sydney", {"departure_date": "2026-04-25"}),
    # ---- US PUBLIC HOLIDAYS (federal) ----
    (
        "MLK Day",
        None,
        {
            # Third Monday of January 2027
            "departure_date": "2027-01-19",
        },
    ),
    (
        "Martin Luther King Day",
        None,
        {
            "departure_date": "2027-01-19",
        },
    ),
    (
        "MLK weekend",
        None,
        {
            # Sat Jan 17 - Mon Jan 19 (2027)
            "departure_date": "2027-01-17",
            "return_date": "2027-01-19",
            "is_range": True,
        },
    ),
    (
        "Presidents' Day",
        None,
        {
            # Third Monday of February 2027
            "departure_date": "2027-02-15",
        },
    ),
    (
        "Presidents' Day weekend",
        None,
        {
            "departure_date": "2027-02-14",
            "return_date": "2027-02-16",
            "is_range": True,
        },
    ),
    (
        "Juneteenth",
        None,
        {
            "departure_date": "2026-06-19",
        },
    ),
    (
        "Columbus Day",
        None,
        {
            # Second Monday of October 2026
            "departure_date": "2026-10-12",
        },
    ),
    (
        "Indigenous Peoples' Day",
        None,
        {
            # Same date as Columbus Day
            "departure_date": "2026-10-12",
        },
    ),
    (
        "Veterans Day",
        None,
        {
            "departure_date": "2026-11-11",
        },
    ),
    (
        "Veterans Day weekend",
        None,
        {
            # Nov 11, 2026 is a Wednesday — weekend around it (before or after)
            "is_range": True,
        },
    ),
    (
        "Black Friday",
        None,
        {
            # Day after Thanksgiving 2026 (Nov 26) = Nov 27
            "departure_date": "2026-11-27",
        },
    ),
    (
        "Cyber Monday",
        None,
        {
            # Monday after Thanksgiving 2026 = Nov 30
            "departure_date": "2026-11-30",
        },
    ),
    # ---- UK PUBLIC HOLIDAYS (bank holidays) ----
    (
        "New Year bank holiday",
        None,
        {
            # Jan 1 2027 — LLM may return the day or interpret as holiday period
        },
    ),
    (
        "May bank holiday",
        None,
        {
            # UK has two May bank holidays (early May + late May) — accept either
            "departure_date": "2026-05-25",
        },
    ),
    (
        "Spring bank holiday",
        None,
        {
            # UK late May bank holiday = last Monday of May 2026
            "departure_date": "2026-05-25",
        },
    ),
    (
        "August bank holiday",
        None,
        {
            # UK = last Monday of August 2026
            "departure_date": "2026-08-31",
        },
    ),
    (
        "Easter Monday",
        None,
        {
            # Easter 2027 = Mar 28, so Easter Monday = Mar 29
            "departure_date": "2027-03-29",
        },
    ),
    (
        "Easter bank holiday weekend",
        None,
        {
            # Good Friday Mar 26 to Easter Monday Mar 29 (2027)
            "departure_date": "2027-03-26",
            "return_date": "2027-03-29",
            "is_range": True,
        },
    ),
    (
        "Guy Fawkes Night",
        None,
        {
            "departure_date": "2026-11-05",
        },
    ),
    (
        "Bonfire Night",
        None,
        {
            "departure_date": "2026-11-05",
        },
    ),
    (
        "Remembrance Sunday",
        None,
        {
            # Second Sunday of November 2026 = Nov 8
            "departure_date": "2026-11-08",
        },
    ),
    (
        "King's Birthday",
        None,
        {
            # Second Monday of June 2026 = Jun 8
            "departure_date": "2026-06-08",
        },
    ),
    (
        "King's Coronation",
        None,
        {
            # One-off event (2023) — LLM may return null or May 6
            "error": True,
        },
    ),
    (
        "Boxing Day bank holiday",
        None,
        {
            # Dec 26 2026 is Saturday → bank holiday Mon Dec 28
            "departure_date": "2026-12-28",
        },
    ),
    (
        "Christmas bank holiday",
        None,
        {
            # Dec 25 2026 is Friday → bank holiday on the day
            "departure_date": "2026-12-25",
        },
    ),
    # ---- US EVENTS / CULTURAL ----
    (
        "NYC Marathon",
        "New York",
        {
            # First Sunday of November 2026 = Nov 1
            "departure_date": "2026-11-01",
        },
    ),
    (
        "Boston Marathon",
        "Boston",
        {
            # Third Monday of April (Patriots' Day) 2026 = Apr 20
            "departure_date": "2026-04-20",
        },
    ),
    (
        "Thanksgiving parade",
        "New York",
        {
            # Macy's parade = Thanksgiving Day
            "departure_date": "2026-11-26",
        },
    ),
    (
        "Black Friday weekend",
        None,
        {
            # Fri Nov 27 - Sun Nov 29 (2026)
            "departure_date": "2026-11-27",
            "return_date": "2026-11-29",
            "is_range": True,
        },
    ),
    (
        "March Madness",
        None,
        {
            # NCAA tournament: mid-March to early April
            "departure_date": "2027-03-15",
        },
    ),
    (
        "Super Bowl weekend",
        None,
        {
            # Super Bowl LXI 2027: Feb 14 (Sunday)
            "departure_date": "2027-02-13",
            "return_date": "2027-02-15",
            "is_range": True,
        },
    ),
    (
        "MLB Opening Day",
        None,
        {
            # Niche sporting event — LLM may or may not resolve it
        },
    ),
    (
        "4th of July weekend",
        None,
        {
            # July 4 2026 is Saturday — Sat-Sun weekend
            "departure_date": "2026-07-03",
            "return_date": "2026-07-05",
            "is_range": True,
        },
    ),
    (
        "July 4th long weekend",
        None,
        {
            "departure_date": "2026-07-03",
            "return_date": "2026-07-05",
            "is_range": True,
        },
    ),
    # ---- UK EVENTS / CULTURAL ----
    (
        "Glastonbury",
        None,
        {
            # Glastonbury 2026 is a fallow year — next is 2027: Jun 23-27
            "departure_date": "2027-06-23",
            "return_date": "2027-06-27",
            "is_range": True,
        },
    ),
    (
        "Notting Hill Carnival",
        "London",
        {
            # Last weekend of August (Sat-Mon bank holiday)
            "departure_date": "2026-08-29",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    (
        "London Marathon",
        "London",
        {
            # Last Sunday of April 2026 = Apr 26
            "departure_date": "2026-04-26",
        },
    ),
    (
        "Royal Ascot",
        None,
        {
            # Third week of June (Tue-Sat)
            "departure_date": "2026-06-16",
            "return_date": "2026-06-20",
            "is_range": True,
        },
    ),
    (
        "Henley Regatta",
        None,
        {
            # Late June - early July (5 days)
            "departure_date": "2026-07-01",
            "return_date": "2026-07-05",
            "is_range": True,
        },
    ),
    (
        "Chelsea Flower Show",
        "London",
        {
            # Late May (Tue-Sat)
            "departure_date": "2026-05-19",
            "return_date": "2026-05-23",
            "is_range": True,
        },
    ),
    (
        "The Open Championship",
        None,
        {
            # British Open golf — LLM may or may not resolve it
        },
    ),
    (
        "Bonfire Night weekend",
        None,
        {
            # Nov 5 2026 is Thursday — nearest weekend
            "departure_date": "2026-11-07",
            "return_date": "2026-11-08",
            "is_range": True,
        },
    ),
    (
        "Burns Night",
        None,
        {
            # Jan 25 — Scottish celebration
            "departure_date": "2027-01-25",
        },
    ),
    (
        "St Andrew's Day",
        None,
        {
            # Nov 30 — Scottish national day
            "departure_date": "2026-11-30",
        },
    ),
]

# ============================================================================
# CATEGORY 9: SCHOOL / TRAVEL BREAKS
# ============================================================================
SCHOOL_BREAKS = [
    (
        "spring break",
        None,
        {
            # Typically mid-March to mid-April (deterministic: Mar 15-29)
            "is_range": True,
        },
    ),
    (
        "spring break 2027",
        None,
        {
            "is_range": True,
        },
    ),
    (
        "summer vacation",
        None,
        {
            # LLM interprets as Jun 1 start (reasonable)
            "departure_date": "2026-06-01",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    (
        "summer holidays",
        None,
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    (
        "winter break",
        None,
        {
            # Dec 20 - Jan 3
            "departure_date": "2026-12-20",
            "return_date": "2027-01-03",
            "is_range": True,
        },
    ),
    (
        "half term",
        None,
        {
            # UK school half-term — too region-specific; LLM response varies
        },
    ),
    (
        "reading week",
        None,
        {
            # University mid-term break — too region-specific without context
            "error": True,
        },
    ),
]

# ============================================================================
# CATEGORY 10: COLLOQUIAL / INFORMAL
# ============================================================================
COLLOQUIAL = [
    ("a couple of days from now", None, {"departure_date": "2026-04-22"}),
    ("a few weeks from now", None, {"departure_date": "2026-05-11"}),
    ("in about a month", None, {"departure_date": "2026-05-20"}),
    ("sometime next week", None, {"is_departure_window": True}),
    ("ASAP", None, {"departure_date": "2026-04-20"}),
    ("as soon as possible", None, {"departure_date": "2026-04-20"}),
    ("whenever is cheapest", None, {"is_departure_window": True}),
    ("no specific date yet", None, {"error": True}),
    ("haven't decided yet", None, {"error": True}),
    ("not sure about dates", None, {"error": True}),
]

# ============================================================================
# CATEGORY 11: AMBIGUOUS / TRICKY FORMATS
# ============================================================================
AMBIGUOUS = [
    # The production bug case — compressed date
    (
        "2462027",
        None,
        {
            # Could be 24/6/2027 (June 24, 2027)
            "departure_date": "2027-06-24",
        },
    ),
    # European vs American date ambiguity
    (
        "03/04/2026",
        None,
        {
            # US format default → March 4, 2026 — but past ref date → auto-rolled to 2027
            "departure_date": "2027-03-04",
        },
    ),
    # Two-digit year
    ("May 15 '27", None, {"departure_date": "2027-05-15"}),
    ("15/6/27", None, {"departure_date": "2027-06-15"}),
    # Typos
    ("Janury 15", None, {"departure_date": "2027-01-15"}),
    ("Febuary 10", None, {"departure_date": "2027-02-10"}),
    ("Wendsday next week", None, {"departure_date": "2026-04-29"}),
    # Mixed info
    (
        "next Friday for 5 days, 2 adults",
        None,
        {
            "departure_date": "2026-04-24",
            "trip_duration_days": 5,
        },
    ),
    (
        "May 10 to May 15, round trip",
        None,
        {
            "departure_date": "2026-05-10",
            "return_date": "2026-05-15",
            "is_range": True,
        },
    ),
    # Edge: invalid dates
    ("February 30", None, {"error": True}),
    ("April 31", None, {"error": True}),
    # Past dates — validator auto-rolls forward until future
    ("January 5, 2025", None, {"departure_date": "2027-01-05"}),
    (
        "last week",
        None,
        {
            # Past reference — should ideally error, but validator may auto-roll
            "error": True,
        },
    ),
]

# ============================================================================
# CATEGORY 12: HOTEL-SPECIFIC PATTERNS
# ============================================================================
HOTEL_PATTERNS = [
    (
        "check in May 1, check out May 5",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
    (
        "checkin April 24 checkout April 26",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
    (
        "3 nights starting May 10",
        None,
        {
            "departure_date": "2026-05-10",
            "return_date": "2026-05-13",
            "is_range": True,
            "trip_duration_days": 3,
        },
    ),
    (
        "2 nights from tomorrow",
        None,
        {
            "departure_date": "2026-04-21",
            "return_date": "2026-04-23",
            "is_range": True,
            "trip_duration_days": 2,
        },
    ),
    (
        "staying for a week from June 1",
        None,
        {
            "departure_date": "2026-06-01",
            "return_date": "2026-06-08",
            "is_range": True,
            "trip_duration_days": 7,
        },
    ),
    # The production bug case — hotel user saying dates
    (
        "Lexington Kentucky 4-24 through the 26th",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
    ("26th of April", None, {"departure_date": "2026-04-26"}),
    ("April 26th", None, {"departure_date": "2026-04-26"}),
]

# ============================================================================
# CATEGORY 13: MAJOR EVENTS & FESTIVALS (destination-specific)
# ============================================================================
EVENTS = [
    (
        "during the Olympics",
        "Paris",
        {
            # 2024 already passed, next summer 2028 Los Angeles
            # For Paris context, should recognize no upcoming Paris Olympics
        },
    ),
    (
        "during Wimbledon",
        "London",
        {
            # Wimbledon 2026: late June - mid July
            "departure_date": "2026-06-29",
        },
    ),
    (
        "during the Monaco Grand Prix",
        "Monaco",
        {
            # Monaco GP 2026: late May
            "departure_date": "2026-05-24",
        },
    ),
    (
        "during Edinburgh Festival",
        "Edinburgh",
        {
            # Edinburgh Fringe: August
            "departure_date": "2026-08-07",
        },
    ),
    (
        "during La Tomatina",
        "Valencia",
        {
            # Last Wednesday of August
            "departure_date": "2026-08-26",
        },
    ),
    (
        "during the Running of the Bulls",
        "Pamplona",
        {
            # San Fermin: July 6-14
            "departure_date": "2026-07-06",
            "return_date": "2026-07-14",
            "is_range": True,
        },
    ),
    (
        "during Coachella",
        None,
        {
            # Coachella 2026 is past ref date (Apr 20); next is 2027: Apr 9-18
            "departure_date": "2027-04-09",
        },
    ),
    (
        "during the Super Bowl",
        None,
        {
            # Super Bowl LXI 2027: Feb 14
            "departure_date": "2027-02-14",
        },
    ),
    (
        "during the World Cup",
        None,
        {
            # 2026 World Cup: June-July in US/Mexico/Canada
            "departure_date": "2026-06-11",
        },
    ),
    (
        "during the Tour de France",
        "France",
        {
            # July — LLM should know this from training data
            "departure_date": "2026-07-04",
        },
    ),
    (
        "during Hajj",
        "Mecca",
        {
            # Around Eid al-Adha, 2026: late May
            "departure_date": "2026-05-25",
        },
    ),
]

# ============================================================================
# CATEGORY 14: REGIONAL / DESTINATION-SPECIFIC SEASONS
# ============================================================================
REGIONAL_SEASONS = [
    (
        "peak season",
        "Maldives",
        {
            # Nov-Apr
            "departure_date": "2026-11-01",
            "return_date": "2027-04-30",
            "is_range": True,
        },
    ),
    (
        "peak season",
        "Bali",
        {
            # Dry season Apr-Oct; mid-season, validator clips departure to today
            "departure_date": "2026-04-20",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "peak season",
        "Caribbean",
        {
            # Dec-Apr
            "departure_date": "2026-12-15",
            "return_date": "2027-04-15",
            "is_range": True,
        },
    ),
    (
        "off season",
        "Thailand",
        {
            # Rainy season May-Oct (off-peak). LLM interpretation varies.
        },
    ),
    (
        "shoulder season",
        "Europe",
        {
            # Apr-May (clipped to today)
            "departure_date": "2026-04-20",
            "return_date": "2026-05-31",
            "is_range": True,
        },
    ),
    (
        "rainy season",
        "Southeast Asia",
        {
            "departure_date": "2026-05-15",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "hurricane season",
        "Caribbean",
        {
            # June 1 - Nov 30
            "departure_date": "2026-06-01",
        },
    ),
    (
        "whale watching season",
        "Iceland",
        {
            # June-August
            "departure_date": "2026-06-15",
            "return_date": "2026-08-31",
            "is_range": True,
        },
    ),
    (
        "northern lights season",
        "Iceland",
        {
            # Sep-Mar
            "departure_date": "2026-09-15",
            "return_date": "2027-03-15",
            "is_range": True,
        },
    ),
    (
        "northern lights season",
        "Norway",
        {
            # Sep-Mar
            "departure_date": "2026-09-15",
            "return_date": "2027-03-15",
            "is_range": True,
        },
    ),
    (
        "midnight sun",
        "Norway",
        {
            # Late May - late July (LLM may start at Jun 1)
            "departure_date": "2026-06-01",
        },
    ),
    (
        "tulip season",
        "Amsterdam",
        {
            # Mid-March to mid-May, peak April (mid-season, clipped to today)
            "departure_date": "2026-04-20",
            "return_date": "2026-05-15",
            "is_range": True,
        },
    ),
    (
        "lavender season",
        "Provence",
        {
            # Mid-June to mid-August
            "departure_date": "2026-06-15",
            "return_date": "2026-08-15",
            "is_range": True,
        },
    ),
    (
        "grape harvest",
        "Bordeaux",
        {
            # September-October — LLM response varies
        },
    ),
    (
        "safari season",
        "Kenya",
        {
            # Great migration: July-October
            "departure_date": "2026-07-01",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
    (
        "safari season",
        "Tanzania",
        {
            # Great migration: June-September (Serengeti)
            "departure_date": "2026-06-01",
            "return_date": "2026-09-30",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 15: BUSINESS TRAVEL PATTERNS
# ============================================================================
BUSINESS_TRAVEL = [
    # Weekday trips — ref date is Monday Apr 20
    (
        "Monday to Friday",
        None,
        {
            # "Monday to Friday" = this week (today is Monday)
            "departure_date": "2026-04-20",
            "return_date": "2026-04-24",
            "is_range": True,
        },
    ),
    (
        "weekday trip next week",
        None,
        {
            "departure_date": "2026-04-27",
        },
    ),
    (
        "3-day business trip starting Monday",
        None,
        {
            # "starting Monday" = this Monday (today)
            "departure_date": "2026-04-20",
            "return_date": "2026-04-23",
            "is_range": True,
            "trip_duration_days": 3,
        },
    ),
    (
        "midweek, 2 nights",
        None,
        {
            # Vague — LLM may return null or Wed
            "departure_date": "2026-04-22",  # Wednesday
            "return_date": "2026-04-24",
            "is_range": True,
            "trip_duration_days": 2,
        },
    ),
    (
        "overnight trip Tuesday",
        None,
        {
            "departure_date": "2026-04-21",
            "return_date": "2026-04-22",
            "is_range": True,
            "trip_duration_days": 1,
        },
    ),
    (
        "day trip next Thursday",
        None,
        {
            "departure_date": "2026-04-23",
        },
    ),
    (
        "red-eye Friday",
        None,
        {
            "departure_date": "2026-04-24",
        },
    ),
    (
        "fly out Sunday evening, return Friday",
        None,
        {
            "departure_date": "2026-04-26",
            "return_date": "2026-05-01",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 16: NUMERIC SHORTHAND / SLASH RANGES
# ============================================================================
NUMERIC_SHORTHAND = [
    # US-style slash ranges (MM/DD)
    (
        "5/1-5/5",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
    (
        "4/24-26",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
    (
        "12/20-1/3",
        None,
        {
            "departure_date": "2026-12-20",
            "return_date": "2027-01-03",
            "is_range": True,
        },
    ),
    (
        "6/15-6/22",
        None,
        {
            "departure_date": "2026-06-15",
            "return_date": "2026-06-22",
            "is_range": True,
        },
    ),
    # Compact no-separator (production bug style)
    (
        "5152026",
        None,
        {
            # Could be 5/15/2026
            "departure_date": "2026-05-15",
        },
    ),
    (
        "12252026",
        None,
        {
            # Could be 12/25/2026
            "departure_date": "2026-12-25",
        },
    ),
    # Dash-separated short form
    (
        "5-1 to 5-5",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
    # DD/MM style range
    (
        "24/4 to 26/4",
        None,
        {
            "departure_date": "2026-04-24",
            "return_date": "2026-04-26",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 17: RELATIVE TO ANOTHER DATE
# ============================================================================
RELATIVE_TO_DATE = [
    # Relative to holidays
    (
        "a week before Christmas",
        None,
        {
            "departure_date": "2026-12-18",
        },
    ),
    (
        "2 days after Thanksgiving",
        None,
        {
            # Thanksgiving 2026 = Nov 26, so Nov 28
            "departure_date": "2026-11-28",
        },
    ),
    (
        "the weekend before Easter",
        None,
        {
            # Easter 2027 = Mar 28; weekend before is approximate
            "is_range": True,
        },
    ),
    (
        "day after New Year's",
        None,
        {
            "departure_date": "2027-01-02",
        },
    ),
    (
        "a week after my arrival",
        None,
        {
            # No context — requires prior arrival date
            "error": True,
        },
    ),
    (
        "the night before departure",
        None,
        {
            # Ambiguous without context — should signal error or ask
            "error": True,
        },
    ),
    (
        "3 days before the wedding",
        None,
        {
            # No date context — should ask
            "error": True,
        },
    ),
    (
        "around Thanksgiving",
        None,
        {
            # "around" = approximate — Thanksgiving 2026 = Nov 26
            "departure_date": "2026-11-26",
        },
    ),
    (
        "right after Christmas",
        None,
        {
            "departure_date": "2026-12-26",
        },
    ),
    (
        "just before New Year's",
        None,
        {
            "departure_date": "2026-12-30",
        },
    ),
]

# ============================================================================
# CATEGORY 18: NIGHT-COUNT WITHOUT START DATE
# ============================================================================
NIGHT_COUNT_NO_START = [
    (
        "just 2 nights",
        None,
        {
            # No start date — should ask for check-in date
            "trip_duration_days": 2,
        },
    ),
    (
        "a 5-night stay",
        None,
        {
            "trip_duration_days": 5,
        },
    ),
    (
        "7-day trip",
        None,
        {
            "trip_duration_days": 7,
        },
    ),
    (
        "looking for a 3-night getaway",
        None,
        {
            "trip_duration_days": 3,
        },
    ),
    (
        "10-day vacation",
        None,
        {
            "trip_duration_days": 10,
        },
    ),
    (
        "a 2-week holiday",
        None,
        {
            "trip_duration_days": 14,
        },
    ),
    (
        "quick 1-night stay",
        None,
        {
            # "1-night" should extract duration
            "trip_duration_days": 1,
        },
    ),
    (
        "long stay, about a month",
        None,
        {
            "trip_duration_days": 30,
        },
    ),
]

# ============================================================================
# CATEGORY 19: RETURN-FOCUSED EXPRESSIONS
# ============================================================================
RETURN_FOCUSED = [
    (
        "back by Sunday",
        None,
        {
            "return_date": "2026-04-26",
        },
    ),
    (
        "return May 5th",
        None,
        {
            "return_date": "2026-05-05",
        },
    ),
    (
        "need to be home by the 10th",
        None,
        {
            # Return-only with no departure context — LLM may return null or infer
            "return_date": "2026-05-10",
        },
    ),
    (
        "flying back on Friday",
        None,
        {
            # Return-only — LLM may return null
            "return_date": "2026-04-24",
        },
    ),
    (
        "checkout on the 15th",
        None,
        {
            # Return-only — LLM may return null
            "return_date": "2026-05-15",
        },
    ),
    (
        "leave May 1, back May 8",
        None,
        {
            "departure_date": "2026-05-01",
            "return_date": "2026-05-08",
            "is_range": True,
        },
    ),
    (
        "departing June 10, returning June 17",
        None,
        {
            "departure_date": "2026-06-10",
            "return_date": "2026-06-17",
            "is_range": True,
        },
    ),
    (
        "going May 20, coming back May 27",
        None,
        {
            "departure_date": "2026-05-20",
            "return_date": "2026-05-27",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 20: NATURAL HEDGING / APPROXIMATE DATES
# ============================================================================
NATURAL_HEDGING = [
    (
        "around Christmas",
        None,
        {
            "departure_date": "2026-12-25",
        },
    ),
    (
        "roughly mid-June",
        None,
        {
            "departure_date": "2026-06-15",
        },
    ),
    (
        "give or take a few days around May 10",
        None,
        {
            # Hedging language — LLM should extract core date May 10
            "is_departure_window": True,
        },
    ),
    (
        "sometime around Easter",
        None,
        {
            # Easter 2027 = Mar 28; "sometime" may trigger departure window
            "is_departure_window": True,
        },
    ),
    (
        "about 2 weeks from now",
        None,
        {
            "departure_date": "2026-05-04",
        },
    ),
    (
        "approximately July 4th week",
        None,
        {
            # Hedging language — LLM may return range, window, or single date
        },
    ),
    (
        "more or less end of May",
        None,
        {
            "departure_date": "2026-05-25",
        },
    ),
    (
        "near the end of June",
        None,
        {
            "departure_date": "2026-06-25",
        },
    ),
    (
        "in the neighborhood of August 15",
        None,
        {
            "departure_date": "2026-08-15",
        },
    ),
    (
        "close to Valentine's Day",
        None,
        {
            "departure_date": "2027-02-14",
        },
    ),
]

# ============================================================================
# CATEGORY 21: SAME-DAY / LAST-MINUTE / URGENT
# ============================================================================
URGENT_TRAVEL = [
    (
        "last minute",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "same day",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "leaving tonight",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "need to fly out today",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "emergency trip tomorrow",
        None,
        {
            "departure_date": "2026-04-21",
        },
    ),
    (
        "earliest available",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "next available flight",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
    (
        "right away",
        None,
        {
            "departure_date": "2026-04-20",
        },
    ),
]

# ============================================================================
# CATEGORY 22: CONFERENCE / WORK EVENT PHRASING
# ============================================================================
CONFERENCE_EVENTS = [
    (
        "during CES",
        "Las Vegas",
        {
            # CES 2027: early January
            "departure_date": "2027-01-05",
        },
    ),
    (
        "SXSW dates",
        "Austin",
        {
            # SXSW 2027: mid-March (deterministic range)
            "departure_date": "2027-03-12",
            "return_date": "2027-03-21",
            "is_range": True,
        },
    ),
    (
        "during fashion week",
        "Milan",
        {
            # Milan Fashion Week: late September — not in reference table
            "departure_date": "2026-09-22",
        },
    ),
    (
        "during fashion week",
        "Paris",
        {
            # Paris Fashion Week: late September — not in reference table
            "departure_date": "2026-09-28",
        },
    ),
    (
        "during fashion week",
        "New York",
        {
            # NYFW: early September — not in reference table
            "departure_date": "2026-09-10",
            "return_date": "2026-09-17",
            "is_range": True,
        },
    ),
    (
        "during Art Basel",
        "Miami",
        {
            # Art Basel Miami: early December (deterministic range)
            "departure_date": "2026-12-03",
            "return_date": "2026-12-07",
            "is_range": True,
        },
    ),
    (
        "for the Web Summit",
        "Lisbon",
        {
            # Web Summit: early November (deterministic range)
            "departure_date": "2026-11-02",
            "return_date": "2026-11-05",
            "is_range": True,
        },
    ),
    (
        "during Comic-Con",
        "San Diego",
        {
            # SDCC: mid-late July
            "departure_date": "2026-07-23",
        },
    ),
    (
        "during Cannes Film Festival",
        "Cannes",
        {
            # Cannes: mid-May
            "departure_date": "2026-05-12",
        },
    ),
    (
        "during the Dubai Expo",
        "Dubai",
        {
            # Expo City Dubai events (deterministic range)
            "departure_date": "2026-10-01",
            "return_date": "2026-10-31",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 23: PARTIAL CONFIRMATION / CONTEXTUAL REPLIES
# ============================================================================
PARTIAL_CONFIRMATION = [
    # These simulate user replying to a bot question about dates.
    # The parser should either pass them through or signal they need context.
    (
        "yes those dates",
        None,
        {
            # No date info — should error / ask for clarification
            "error": True,
        },
    ),
    (
        "that works",
        None,
        {
            "error": True,
        },
    ),
    (
        "confirmed",
        None,
        {
            "error": True,
        },
    ),
    (
        "sounds good",
        None,
        {
            "error": True,
        },
    ),
    (
        "perfect",
        None,
        {
            "error": True,
        },
    ),
    (
        "yes",
        None,
        {
            "error": True,
        },
    ),
    (
        "no, a week later",
        None,
        {
            # Relative shift — LLM may interpret as "next week" from ref date
            "departure_date": "2026-04-27",
        },
    ),
    (
        "actually make it the 15th",
        None,
        {
            # Context-dependent correction — no prior context
            "error": True,
        },
    ),
    (
        "can we push it by 2 days",
        None,
        {
            # Relative shift — LLM may interpret as +2 days from ref date
            "departure_date": "2026-04-22",
        },
    ),
    (
        "one week earlier",
        None,
        {
            "error": True,
        },
    ),
]

# ============================================================================
# CATEGORY 24: COMBINED WITH PRICE / PREFERENCE SIGNALS
# ============================================================================
PRICE_COMBINED = [
    (
        "cheapest week in May",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-05-01",
            "departure_window_end": "2026-05-31",
        },
    ),
    (
        "most affordable time to visit Bali",
        "Bali",
        {
            # Off-season: wet season Nov-Mar (cheaper)
            "is_departure_window": True,
        },
    ),
    (
        "budget-friendly dates in December",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-12-01",
            "departure_window_end": "2026-12-31",
        },
    ),
    (
        "when is it cheapest to fly to Tokyo",
        "Tokyo",
        {
            "is_departure_window": True,
        },
    ),
    (
        "off-peak rates in August",
        None,
        {
            "is_departure_window": True,
            "departure_window_start": "2026-08-01",
            "departure_window_end": "2026-08-31",
        },
    ),
    (
        "May 10 for 3 nights, preferably under $200",
        None,
        {
            # Should extract dates, ignore price
            "departure_date": "2026-05-10",
            "return_date": "2026-05-13",
            "is_range": True,
            "trip_duration_days": 3,
        },
    ),
    (
        "3 adults, June 5-10, cheapest option",
        None,
        {
            # Should extract dates, ignore passenger count and preference
            "departure_date": "2026-06-05",
            "return_date": "2026-06-10",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 25: MULTI-LEG / STOPOVER EXPRESSIONS
# ============================================================================
MULTI_LEG = [
    (
        "3 days in Paris then 4 in Rome",
        None,
        {
            # Multi-leg: total 7 days. LLM may return just first leg duration.
            "trip_duration_days": 7,
        },
    ),
    (
        "a week split between London and Paris",
        None,
        {
            "trip_duration_days": 7,
        },
    ),
    (
        "fly into Barcelona, out of Madrid, 10 days",
        None,
        {
            "trip_duration_days": 10,
        },
    ),
    (
        "5 nights in Tokyo then 3 in Osaka starting May 1",
        None,
        {
            "departure_date": "2026-05-01",
            "trip_duration_days": 8,
        },
    ),
    (
        "2 weeks: Bangkok → Chiang Mai → Phuket",
        None,
        {
            "trip_duration_days": 14,
        },
    ),
]

# ============================================================================
# CATEGORY 26: VISA / MAX-STAY CONSTRAINTS
# ============================================================================
VISA_CONSTRAINTS = [
    (
        "the full 90 days starting June 1",
        None,
        {
            "departure_date": "2026-06-01",
            "trip_duration_days": 90,
        },
    ),
    (
        "30-day visa trip from July 15",
        None,
        {
            "departure_date": "2026-07-15",
            "trip_duration_days": 30,
        },
    ),
    (
        "maximum stay 14 days from August 1",
        None,
        {
            "departure_date": "2026-08-01",
            "trip_duration_days": 14,
        },
    ),
    (
        "6 months starting September",
        None,
        {
            # LLM may parse "6" as literal days or 6*30=180; just check departure
            "departure_date": "2026-09-01",
        },
    ),
]

# ============================================================================
# CATEGORY 27: EMOJI AND UNICODE DATE EXPRESSIONS
# ============================================================================
EMOJI_UNICODE = [
    ("✈️ May 15", None, {"departure_date": "2026-05-15"}),
    ("🏖️ summer vacation July", None, {"departure_date": "2026-07-01"}),
    ("🎄 Christmas trip", None, {"departure_date": "2026-12-25"}),
    (
        "🎃 Halloween weekend",
        None,
        {
            # Halloween 2026 is Saturday; "weekend" may start Friday Oct 30
            "departure_date": "2026-10-30",
        },
    ),
    ("🏂 ski trip January", None, {"departure_date": "2027-01-01"}),
]

# ============================================================================
# CATEGORY 28: MIXED LANGUAGES / INTERNATIONAL DATE WORDS
# ============================================================================
INTERNATIONAL = [
    # Spanish months
    ("mayo 15", None, {"departure_date": "2026-05-15"}),
    ("15 de junio", None, {"departure_date": "2026-06-15"}),
    # French
    ("15 juillet", None, {"departure_date": "2026-07-15"}),
    ("août", None, {"departure_date": "2026-08-01"}),
    # German
    ("15. Mai", None, {"departure_date": "2026-05-15"}),
    # Common transliterations
    (
        "golden week",
        "Tokyo",
        {
            "departure_date": "2026-04-29",
            "return_date": "2026-05-05",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 29: AUSTRALIAN / NZ HOLIDAYS & EVENTS
# ============================================================================
AUSTRALIA_NZ = [
    ("Australia Day", "Sydney", {"departure_date": "2027-01-26"}),
    (
        "Australia Day weekend",
        "Sydney",
        {
            # Jan 26, 2027 is Tuesday — long weekend Sat 24 - Mon 26
            "departure_date": "2027-01-24",
            "return_date": "2027-01-26",
            "is_range": True,
        },
    ),
    (
        "Waitangi Day",
        "New Zealand",
        {
            "departure_date": "2027-02-06",
        },
    ),
    (
        "Melbourne Cup",
        "Melbourne",
        {
            # First Tuesday of November 2026 = Nov 3
            "departure_date": "2026-11-03",
        },
    ),
    (
        "Melbourne Cup week",
        "Melbourne",
        {
            "departure_date": "2026-11-02",
            "return_date": "2026-11-07",
            "is_range": True,
        },
    ),
    (
        "Vivid Sydney",
        "Sydney",
        {
            # Late May - mid June light festival
            "departure_date": "2026-05-22",
            "return_date": "2026-06-13",
            "is_range": True,
        },
    ),
    (
        "Sydney New Year's Eve",
        "Sydney",
        {
            "departure_date": "2026-12-31",
        },
    ),
    (
        "Queen's Birthday",
        "Australia",
        {
            # Second Monday of June (most states) 2026 = Jun 8
            "departure_date": "2026-06-08",
        },
    ),
    (
        "Matariki",
        "New Zealand",
        {
            # Maori New Year — 2026: Jul 10 (corrected)
            "departure_date": "2026-07-10",
        },
    ),
]

# ============================================================================
# CATEGORY 30: INDIAN HOLIDAYS & FESTIVALS
# ============================================================================
INDIA_HOLIDAYS = [
    ("Republic Day", "India", {"departure_date": "2027-01-26"}),
    (
        "Republic Day weekend",
        "Delhi",
        {
            # Jan 26 2027 is Tuesday — weekend around it (varies by LLM interpretation)
            "is_range": True,
        },
    ),
    (
        "Independence Day",
        "India",
        {
            # Aug 15 — note: US "Independence Day" defaults to July 4
            "departure_date": "2026-08-15",
        },
    ),
    (
        "Ganesh Chaturthi",
        "Mumbai",
        {
            # 2026: Sep 14 (corrected)
            "departure_date": "2026-09-14",
        },
    ),
    (
        "Navratri",
        "India",
        {
            # Lunar calendar — exact dates vary. Accept range in Sep-Oct.
            "is_range": True,
        },
    ),
    (
        "Durga Puja",
        "Kolkata",
        {
            # During Navratri — lunar calendar, LLM may return range or single date
        },
    ),
    (
        "Pongal",
        "Tamil Nadu",
        {
            # Jan 14-17 — LLM may return just the start date
            "departure_date": "2027-01-14",
        },
    ),
    (
        "Onam",
        "Kerala",
        {
            # 2026: Aug 16-26 (corrected — Thiruvonam Aug 16)
            "departure_date": "2026-08-16",
            "return_date": "2026-08-26",
            "is_range": True,
        },
    ),
    (
        "Raksha Bandhan",
        "India",
        {
            # 2026: Aug 28 (corrected)
            "departure_date": "2026-08-28",
        },
    ),
    (
        "Dussehra",
        "India",
        {
            # 2026: Oct 20 (corrected — Vijayadashami)
            "departure_date": "2026-10-20",
        },
    ),
    (
        "Makar Sankranti",
        "India",
        {
            "departure_date": "2027-01-14",
        },
    ),
    (
        "Baisakhi",
        "Punjab",
        {
            # April 13 or 14
            "departure_date": "2027-04-13",
        },
    ),
]

# ============================================================================
# CATEGORY 31: MIDDLE EAST HOLIDAYS
# ============================================================================
MIDDLE_EAST = [
    (
        "UAE National Day",
        "Dubai",
        {
            "departure_date": "2026-12-02",
        },
    ),
    (
        "UAE National Day weekend",
        "Dubai",
        {
            "departure_date": "2026-12-02",
            "is_range": True,
        },
    ),
    (
        "Saudi National Day",
        "Riyadh",
        {
            "departure_date": "2026-09-23",
        },
    ),
    (
        "Qatar National Day",
        "Doha",
        {
            "departure_date": "2026-12-18",
        },
    ),
    (
        "Eid holidays",
        None,
        {
            # Generic "Eid" — could be al-Fitr or al-Adha; accept either
            "is_range": True,
        },
    ),
    (
        "during Ramadan",
        "Dubai",
        {
            # Ramadan 2026 is past, next is 2027: ~Feb 8 - Mar 9
            "departure_date": "2027-02-08",
            "return_date": "2027-03-09",
            "is_range": True,
        },
    ),
    (
        "after Ramadan",
        None,
        {
            # After Ramadan = Eid al-Fitr. LLM may return date or departure window.
        },
    ),
]

# ============================================================================
# CATEGORY 32: SOUTHEAST ASIAN HOLIDAYS
# ============================================================================
SOUTHEAST_ASIA_HOLIDAYS = [
    (
        "Vesak",
        "Thailand",
        {
            # Buddha Day — 2026: May 1 (corrected)
            "departure_date": "2026-05-01",
        },
    ),
    (
        "Loy Krathong",
        "Thailand",
        {
            # 2026: Nov 25 (corrected — full moon of 12th Thai lunar month)
            "departure_date": "2026-11-25",
        },
    ),
    (
        "Yi Peng",
        "Chiang Mai",
        {
            # 2026: Nov 25-27 (corrected — same time as Loy Krathong)
            "departure_date": "2026-11-25",
            "return_date": "2026-11-27",
            "is_range": True,
        },
    ),
    (
        "Tet",
        "Vietnam",
        {
            # Vietnamese New Year = Chinese New Year 2027
            "departure_date": "2027-02-06",
        },
    ),
    (
        "Tet holiday",
        "Hanoi",
        {
            "departure_date": "2027-02-06",
            "return_date": "2027-02-12",
            "is_range": True,
        },
    ),
    (
        "Nyepi",
        "Bali",
        {
            # Balinese Day of Silence — Saka New Year, lunar calendar (date varies)
            "departure_date": "2027-03-08",
        },
    ),
    (
        "Thaipusam",
        "Kuala Lumpur",
        {
            # January/February — Hindu festival
            "departure_date": "2027-01-27",
        },
    ),
    (
        "Water Festival",
        "Cambodia",
        {
            # Bon Om Touk — niche lunar calendar festival, LLM response varies
        },
    ),
]

# ============================================================================
# CATEGORY 33: EUROPEAN HOLIDAYS (BEYOND UK)
# ============================================================================
EUROPEAN_HOLIDAYS = [
    (
        "Epiphany",
        None,
        {
            # Jan 6
            "departure_date": "2027-01-06",
        },
    ),
    (
        "Three Kings Day",
        "Spain",
        {
            "departure_date": "2027-01-06",
        },
    ),
    (
        "Ascension Day",
        None,
        {
            # 39 days after Easter 2026 (Apr 5) = May 14
            "departure_date": "2026-05-14",
        },
    ),
    (
        "Whit Monday",
        None,
        {
            # 50 days after Easter = May 25
            "departure_date": "2026-05-25",
        },
    ),
    (
        "German Unity Day",
        "Berlin",
        {
            "departure_date": "2026-10-03",
        },
    ),
    (
        "La Mercè",
        "Barcelona",
        {
            # Sep 24
            "departure_date": "2026-09-24",
        },
    ),
    (
        "St. Nicholas Day",
        None,
        {
            "departure_date": "2026-12-06",
        },
    ),
    (
        "Fête de la Musique",
        "Paris",
        {
            # June 21 — summer solstice music festival
            "departure_date": "2026-06-21",
        },
    ),
    (
        "San Fermín",
        "Pamplona",
        {
            # July 6-14 (already in events, but as Spanish name variant)
            "departure_date": "2026-07-06",
            "return_date": "2026-07-14",
            "is_range": True,
        },
    ),
    (
        "All Saints' Day",
        None,
        {
            "departure_date": "2026-11-01",
        },
    ),
    (
        "Assumption Day",
        None,
        {
            # Aug 15 — public holiday in many European countries
            "departure_date": "2026-08-15",
        },
    ),
    (
        "King's Day",
        "Amsterdam",
        {
            # April 27
            "departure_date": "2026-04-27",
        },
    ),
    (
        "National Day",
        "Switzerland",
        {
            # Aug 1
            "departure_date": "2026-08-01",
        },
    ),
    (
        "Fallas",
        "Valencia",
        {
            # March 15-19
            "departure_date": "2027-03-15",
            "return_date": "2027-03-19",
            "is_range": True,
        },
    ),
    (
        "Semana Santa",
        "Seville",
        {
            # Easter 2026 is past ref date; Holy Week before Easter 2027 (Mar 28)
            "departure_date": "2027-03-22",
            "return_date": "2027-03-28",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 34: LATIN AMERICAN HOLIDAYS
# ============================================================================
LATIN_AMERICAN = [
    (
        "Inti Raymi",
        "Cusco",
        {
            # Festival of the Sun — June 24
            "departure_date": "2026-06-24",
        },
    ),
    (
        "Semana Santa",
        "Guatemala",
        {
            # Easter 2026 is past ref date; Holy Week before Easter 2027
            "departure_date": "2027-03-22",
            "return_date": "2027-03-28",
            "is_range": True,
        },
    ),
    (
        "Día de los Muertos",
        "Mexico City",
        {
            "departure_date": "2026-11-01",
            "return_date": "2026-11-02",
            "is_range": True,
        },
    ),
    (
        "Carnival",
        "Trinidad",
        {
            # Carnival 2027 (deterministic: Feb 5-9)
            "departure_date": "2027-02-05",
            "return_date": "2027-02-09",
            "is_range": True,
        },
    ),
    (
        "Fiesta de la Vendimia",
        "Mendoza",
        {
            # Wine harvest festival — early March
            "departure_date": "2027-03-01",
            "return_date": "2027-03-08",
            "is_range": True,
        },
    ),
    (
        "Mexican Independence Day",
        "Mexico City",
        {
            # Sep 16
            "departure_date": "2026-09-16",
        },
    ),
    (
        "Cinco de Mayo",
        "Mexico",
        {
            "departure_date": "2026-05-05",
        },
    ),
]

# ============================================================================
# CATEGORY 35: AFRICAN HOLIDAYS & EVENTS
# ============================================================================
AFRICAN_HOLIDAYS = [
    (
        "Kwanzaa",
        None,
        {
            # Dec 26 - Jan 1
            "departure_date": "2026-12-26",
            "return_date": "2027-01-01",
            "is_range": True,
        },
    ),
    (
        "Africa Day",
        None,
        {
            "departure_date": "2026-05-25",
        },
    ),
    (
        "Cape Town Jazz Festival",
        "Cape Town",
        {
            # Niche festival — LLM may or may not resolve dates
        },
    ),
    (
        "Timkat",
        "Ethiopia",
        {
            # Ethiopian Epiphany — January 19
            "departure_date": "2027-01-19",
        },
    ),
    (
        "Festival au Désert",
        "Mali",
        {
            # Obscure festival — LLM does not know exact dates
            "error": True,
        },
    ),
    (
        "Zanzibar International Film Festival",
        "Zanzibar",
        {
            # Niche event — LLM may or may not resolve dates
        },
    ),
]

# ============================================================================
# CATEGORY 36: TIME-OF-DAY EXPRESSIONS (parser should extract date, ignore time)
# ============================================================================
TIME_OF_DAY = [
    (
        "morning flight May 5",
        None,
        {
            "departure_date": "2026-05-05",
        },
    ),
    (
        "evening of the 10th",
        None,
        {
            # "the 10th" without month — LLM may infer next month or error
        },
    ),
    (
        "late night June 1",
        None,
        {
            "departure_date": "2026-06-01",
        },
    ),
    (
        "early morning tomorrow",
        None,
        {
            "departure_date": "2026-04-21",
        },
    ),
    (
        "red-eye flight May 20",
        None,
        {
            "departure_date": "2026-05-20",
        },
    ),
    (
        "afternoon departure July 3",
        None,
        {
            "departure_date": "2026-07-03",
        },
    ),
    (
        "midnight flight on New Year's Eve",
        None,
        {
            "departure_date": "2026-12-31",
        },
    ),
    (
        "sunrise flight to Bali June 15",
        "Bali",
        {
            "departure_date": "2026-06-15",
        },
    ),
]

# ============================================================================
# CATEGORY 37: YEAR-SPANNING RANGES
# ============================================================================
YEAR_SPANNING = [
    (
        "over New Year's",
        None,
        {
            # LLM may return narrow Dec 31-Jan 1 or broader holiday range
            "is_range": True,
        },
    ),
    (
        "Christmas to New Year's",
        None,
        {
            "departure_date": "2026-12-25",
            "return_date": "2027-01-01",
            "is_range": True,
        },
    ),
    (
        "Dec 28 to Jan 3",
        None,
        {
            "departure_date": "2026-12-28",
            "return_date": "2027-01-03",
            "is_range": True,
        },
    ),
    (
        "New Year's Eve to January 2",
        None,
        {
            "departure_date": "2026-12-31",
            "return_date": "2027-01-02",
            "is_range": True,
        },
    ),
    (
        "over the holidays",
        None,
        {
            # Generic holiday period — LLM may interpret as Christmas-New Year's range
            "departure_date": "2026-12-20",
            "return_date": "2027-01-02",
            "is_range": True,
        },
    ),
    (
        "holiday season",
        None,
        {
            # Vague — LLM may return departure window or concrete Dec range
            "is_range": True,
        },
    ),
    (
        "between Christmas and New Year's",
        None,
        {
            "departure_date": "2026-12-25",
            "return_date": "2027-01-01",
            "is_range": True,
        },
    ),
    (
        "New Year's week",
        None,
        {
            "departure_date": "2026-12-28",
            "return_date": "2027-01-03",
            "is_range": True,
        },
    ),
]

# ============================================================================
# CATEGORY 38: CORRECTION / AMENDMENT PATTERNS
# ============================================================================
CORRECTIONS = [
    (
        "not May, I meant June",
        None,
        {
            # Should extract June as the intended month
            "departure_date": "2026-06-01",
        },
    ),
    (
        "sorry, the 15th not the 16th",
        None,
        {
            # Context-dependent correction — no prior context available
            "error": True,
        },
    ),
    (
        "actually June 10 instead",
        None,
        {
            "departure_date": "2026-06-10",
        },
    ),
    (
        "wait, make it July not August",
        None,
        {
            "departure_date": "2026-07-01",
        },
    ),
    (
        "change to May 20",
        None,
        {
            "departure_date": "2026-05-20",
        },
    ),
    (
        "I meant the 25th",
        None,
        {
            # LLM extracts "the 25th" and infers next occurrence (Apr 25)
            "departure_date": "2026-04-25",
        },
    ),
    (
        "correction: June 5 to June 12",
        None,
        {
            "departure_date": "2026-06-05",
            "return_date": "2026-06-12",
            "is_range": True,
        },
    ),
    (
        "no wait, the week after",
        None,
        {
            # Ambiguous without prior context — error
            "error": True,
        },
    ),
]

# ============================================================================
# ALL CATEGORIES COMBINED
# ============================================================================
ALL_TEST_CASES = {
    "standard_formats": STANDARD_FORMATS,
    "relative_dates": RELATIVE_DATES,
    "date_ranges": DATE_RANGES,
    "duration_based": DURATION_BASED,
    "weekend_references": WEEKEND_REFERENCES,
    "flexible_dates": FLEXIBLE_DATES,
    "seasons": SEASONS,
    "holidays": HOLIDAYS,
    "school_breaks": SCHOOL_BREAKS,
    "colloquial": COLLOQUIAL,
    "ambiguous": AMBIGUOUS,
    "hotel_patterns": HOTEL_PATTERNS,
    "events": EVENTS,
    "regional_seasons": REGIONAL_SEASONS,
    "business_travel": BUSINESS_TRAVEL,
    "numeric_shorthand": NUMERIC_SHORTHAND,
    "relative_to_date": RELATIVE_TO_DATE,
    "night_count_no_start": NIGHT_COUNT_NO_START,
    "return_focused": RETURN_FOCUSED,
    "natural_hedging": NATURAL_HEDGING,
    "urgent_travel": URGENT_TRAVEL,
    "conference_events": CONFERENCE_EVENTS,
    "partial_confirmation": PARTIAL_CONFIRMATION,
    "price_combined": PRICE_COMBINED,
    "multi_leg": MULTI_LEG,
    "visa_constraints": VISA_CONSTRAINTS,
    "emoji_unicode": EMOJI_UNICODE,
    "international": INTERNATIONAL,
    "australia_nz": AUSTRALIA_NZ,
    "india_holidays": INDIA_HOLIDAYS,
    "middle_east": MIDDLE_EAST,
    "southeast_asia_holidays": SOUTHEAST_ASIA_HOLIDAYS,
    "european_holidays": EUROPEAN_HOLIDAYS,
    "latin_american": LATIN_AMERICAN,
    "african_holidays": AFRICAN_HOLIDAYS,
    "time_of_day": TIME_OF_DAY,
    "year_spanning": YEAR_SPANNING,
    "corrections": CORRECTIONS,
}

# Total count for tracking
TOTAL_TEST_CASES = sum(len(v) for v in ALL_TEST_CASES.values())
