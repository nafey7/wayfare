# Intent Recognizer Test Prompts

**Purpose**: Validate that the intent recognizer correctly classifies user messages into BOOK_FLIGHT, BOOK_HOTEL, and CREATE_ITINERARY intents.
**Source**: Curated from intent recognition QA (2026-01-26), adapted for Chat CLI automation.

**Usage with Chat CLI**:
```bash
# Test a single intent prompt
python3 tools/chat/voya_chat.py --env staging -m "Book flights to Barcelona next week" --json
# Check the "intent" field in JSON output

# Run sticky session scenarios
python3 tools/chat/voya_chat.py --env staging --scenario sticky_session_flight
python3 tools/chat/voya_chat.py --env staging --scenario sticky_session_hotel
```

---

## 1. BOOK_FLIGHT Test Prompts (20)

**Expected**: All should return `BOOK_FLIGHT` intent with 0.70-0.95 confidence

| # | Prompt | Expected | Confidence |
|---|--------|----------|-----------|
| 1 | Book flights to Barcelona next week | BOOK_FLIGHT | 0.95 |
| 2 | I need a flight to Tokyo tomorrow | BOOK_FLIGHT | 0.95 |
| 3 | Search flights from London to Paris | BOOK_FLIGHT | 0.95 |
| 4 | Find me flights to Rome leaving on March 20 | BOOK_FLIGHT | 0.95 |
| 5 | Book me a flight to New York on January 15 | BOOK_FLIGHT | 0.95 |
| 6 | I want to fly to Barcelona | BOOK_FLIGHT | 0.70-0.95 |
| 7 | Flight from NYC to LA next Monday | BOOK_FLIGHT | 0.70-0.95 |
| 8 | Need a one way ticket to Amsterdam | BOOK_FLIGHT | 0.70-0.95 |
| 9 | Book a return flight to Paris in February | BOOK_FLIGHT | 0.95 |
| 10 | Search for flights to Barcelona on the 25th | BOOK_FLIGHT | 0.95 |
| 11 | I need to fly to Tokyo on December 10 | BOOK_FLIGHT | 0.70-0.95 |
| 12 | Find flights from Amsterdam to Barcelona tomorrow | BOOK_FLIGHT | 0.95 |
| 13 | Book round trip flights to London next week | BOOK_FLIGHT | 0.95 |
| 14 | I want to book a flight to Paris for next month | BOOK_FLIGHT | 0.95 |
| 15 | Search for one-way flights to Rome | BOOK_FLIGHT | 0.95 |
| 16 | Need flights to Barcelona leaving January 5 | BOOK_FLIGHT | 0.70-0.95 |
| 17 | Book me a plane ticket to Tokyo | BOOK_FLIGHT | 0.95 |
| 18 | I need to travel to London on March 15 | BOOK_FLIGHT | 0.70 |
| 19 | Find me a flight to Paris next Tuesday | BOOK_FLIGHT | 0.95 |
| 20 | Book flights from Barcelona to Amsterdam on the 20th | BOOK_FLIGHT | 0.95 |

---

## 2. BOOK_HOTEL Test Prompts (20)

**Expected**: All should return `BOOK_HOTEL` intent with 0.70-0.95 confidence

| # | Prompt | Expected | Confidence |
|---|--------|----------|-----------|
| 1 | Book a hotel in Barcelona | BOOK_HOTEL | 0.95 |
| 2 | I need accommodation in Paris | BOOK_HOTEL | 0.70-0.95 |
| 3 | Find me a hotel in Tokyo for next week | BOOK_HOTEL | 0.95 |
| 4 | Book a hotel in London for 3 nights | BOOK_HOTEL | 0.95 |
| 5 | I need a place to stay in Amsterdam | BOOK_HOTEL | 0.70-0.95 |
| 6 | Find accommodation in Rome | BOOK_HOTEL | 0.70-0.95 |
| 7 | Book hotel in Barcelona for January 15 | BOOK_HOTEL | 0.95 |
| 8 | I need a room in Paris next month | BOOK_HOTEL | 0.70-0.95 |
| 9 | Find me a hotel near the airport in Tokyo | BOOK_HOTEL | 0.95 |
| 10 | Book accommodation in London for 5 nights | BOOK_HOTEL | 0.95 |
| 11 | I need to book a hotel in Barcelona | BOOK_HOTEL | 0.95 |
| 12 | Find hotels in Paris for next week | BOOK_HOTEL | 0.95 |
| 13 | I want to stay in Amsterdam from March 10-15 | BOOK_HOTEL | 0.70-0.95 |
| 14 | Book a room in Rome for the weekend | BOOK_HOTEL | 0.95 |
| 15 | Need a hotel in Barcelona city center | BOOK_HOTEL | 0.70-0.95 |
| 16 | Find me accommodation in London | BOOK_HOTEL | 0.70-0.95 |
| 17 | Book hotel in Paris near Eiffel Tower | BOOK_HOTEL | 0.95 |
| 18 | I need a place to stay in Tokyo | BOOK_HOTEL | 0.70-0.95 |
| 19 | Find hotels in Barcelona for 2 nights | BOOK_HOTEL | 0.95 |
| 20 | Book a hotel room in Amsterdam for next Tuesday | BOOK_HOTEL | 0.95 |

---

## 3. CREATE_ITINERARY Test Prompts (20)

**Expected**: All should return `CREATE_ITINERARY` intent with 0.95 confidence

| # | Prompt | Expected | Confidence |
|---|--------|----------|-----------|
| 1 | Plan a trip to Barcelona for 5 days | CREATE_ITINERARY | 0.95 |
| 2 | I'm planning a vacation to Paris | CREATE_ITINERARY | 0.95 |
| 3 | Help me plan a 7-day trip to Tokyo | CREATE_ITINERARY | 0.95 |
| 4 | Create an itinerary for London | CREATE_ITINERARY | 0.95 |
| 5 | I want to visit Rome for a week | CREATE_ITINERARY | 0.95 |
| 6 | Planning a trip to Amsterdam in March | CREATE_ITINERARY | 0.95 |
| 7 | Plan my travel to Barcelona for 10 days | CREATE_ITINERARY | 0.95 |
| 8 | I'm planning to visit Paris for 3 days | CREATE_ITINERARY | 0.95 |
| 9 | Help me organize a trip to Tokyo | CREATE_ITINERARY | 0.95 |
| 10 | Create a 5-day itinerary for London | CREATE_ITINERARY | 0.95 |
| 11 | I want to plan a vacation to Barcelona | CREATE_ITINERARY | 0.95 |
| 12 | Planning a 2-week trip to Paris | CREATE_ITINERARY | 0.95 |
| 13 | Help me plan my visit to Tokyo for a week | CREATE_ITINERARY | 0.95 |
| 14 | I want to organize a trip to Rome | CREATE_ITINERARY | 0.95 |
| 15 | Plan a 4-day trip to Amsterdam | CREATE_ITINERARY | 0.95 |
| 16 | I'm planning a holiday to Barcelona | CREATE_ITINERARY | 0.95 |
| 17 | Create a travel plan for Paris for 6 days | CREATE_ITINERARY | 0.95 |
| 18 | Help me plan a trip to Tokyo for 2 weeks | CREATE_ITINERARY | 0.95 |
| 19 | I want to visit London for 5 days | CREATE_ITINERARY | 0.95 |
| 20 | Planning my vacation to Barcelona next month | CREATE_ITINERARY | 0.95 |

---

## 4. Edge Cases and Sticky Session Tests

### 4.1 Ambiguous Flight Prompts (Should be BOOK_FLIGHT, not CREATE_ITINERARY)

| # | Prompt | Expected | Confidence | Notes |
|---|--------|----------|-----------|-------|
| 1 | Fly to Barcelona next week | BOOK_FLIGHT | 0.70-0.95 | Has "fly" keyword |
| 2 | I want to go to Paris on March 15 | BOOK_FLIGHT | 0.70 | Specific date suggests booking |
| 3 | Take me to Tokyo tomorrow | BOOK_FLIGHT | 0.70 | Date suggests booking |
| 4 | Need to get to London on the 20th | BOOK_FLIGHT | 0.70 | Specific date |

### 4.2 Sticky Session: Flight Booking Flow

**Test scenario**: User starts flight booking, provides additional details.
**Automated scenario**: `python3 tools/chat/voya_chat.py --scenario sticky_session_flight`

| Step | User Message | Expected Intent | Expected Confidence | Notes |
|------|-------------|----------------|-------------------|-------|
| 1 | Book flights to Barcelona | BOOK_FLIGHT | 0.95 | Initial booking request |
| 2 | Paris | BOOK_FLIGHT | 0.90 (sticky) | Origin city (ambiguous but sticky) |
| 3 | one way | BOOK_FLIGHT | 0.90 (sticky) | Flight type |
| 4 | tomorrow | BOOK_FLIGHT | 0.90 (sticky) | Date |
| 5 | 2 passengers | BOOK_FLIGHT | 0.90 (sticky) | Passenger count |

**Critical**: Messages 2-5 should maintain BOOK_FLIGHT due to sticky session logic, even though Gemini might misclassify them in isolation.

### 4.3 Sticky Session: Hotel Booking Flow

**Test scenario**: User starts hotel booking, provides additional details.
**Automated scenario**: `python3 tools/chat/voya_chat.py --scenario sticky_session_hotel`

| Step | User Message | Expected Intent | Expected Confidence | Notes |
|------|-------------|----------------|-------------------|-------|
| 1 | Book a hotel in Barcelona | BOOK_HOTEL | 0.95 | Initial booking request |
| 2 | for 3 nights | BOOK_HOTEL | 0.90 (sticky) | Duration |
| 3 | next week | BOOK_HOTEL | 0.90 (sticky) | Check-in date |
| 4 | 2 rooms | BOOK_HOTEL | 0.90 (sticky) | Room count |
| 5 | near beach | BOOK_HOTEL | 0.90 (sticky) | Location preference |

### 4.4 Intent Switching (High Confidence Overrides)

**Test scenario**: User switches between different intents.

| # | Previous Intent | User Message | Expected New Intent | Confidence | Notes |
|---|----------------|-------------|-------------------|-----------|-------|
| 1 | BOOK_FLIGHT | Book hotel in Barcelona | BOOK_HOTEL | 0.95 | Explicit switch |
| 2 | BOOK_HOTEL | Book flight to Paris | BOOK_FLIGHT | 0.95 | Explicit switch |
| 3 | BOOK_FLIGHT | Plan a trip to Tokyo for 5 days | CREATE_ITINERARY | 0.95 | Explicit planning |
| 4 | CREATE_ITINERARY | Book flights to London | BOOK_FLIGHT | 0.95 | Switch to booking |

**Critical**: These should override sticky sessions because of explicit high-confidence keywords.

### 4.5 Negative Test Cases (Common Misclassifications)

| # | User Message | WRONG Intent | Expected Intent | Confidence | Notes |
|---|-------------|-------------|----------------|-----------|-------|
| 1 | Paris | BOOK_HOTEL | GENERAL_QUERY | 0.30 | Just a city name (no context) |
| 2 | one way | BOOK_HOTEL | GENERAL_QUERY | 0.30 | Just flight type (no context) |
| 3 | tomorrow | CREATE_ITINERARY | GENERAL_QUERY | 0.30 | Just a date (no context) |
| 4 | 2 passengers | BOOK_HOTEL | GENERAL_QUERY | 0.30 | Just passenger count (no context) |

**Critical**: Without sticky session context, these ambiguous messages should default to GENERAL_QUERY with low confidence.

---

## Test Summary

| Category | Count | Target Pass Rate |
|----------|-------|-----------------|
| BOOK_FLIGHT | 20 | 90%+ |
| BOOK_HOTEL | 20 | 90%+ |
| CREATE_ITINERARY | 20 | 90%+ |
| Ambiguous flight | 4 | 75%+ |
| Sticky session (flight) | 5 | 100% |
| Sticky session (hotel) | 5 | 100% |
| Intent switching | 4 | 100% |
| Negative cases | 4 | 75%+ |
| **Total** | **82** | **80%+ (66/82)** |

---

## Correlation with Observability

When running these tests, correlate results with:

- **Langfuse traces**: Check `intent-recognition` tagged traces for actual confidence scores and model decisions
- **Sentry**: Look for intent misclassification errors or fallback behavior
- **Response type in JSON output**: The `intent` field in Chat CLI `--json` output shows the classified intent

For sticky session tests, pay attention to whether the intent changes unexpectedly mid-flow, which would indicate the sticky intent system is not holding correctly.
