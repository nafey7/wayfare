# Itinerary Test Report

Auto-generated from the latest result JSON per scenario in `tools/chat/scenario_results/`.

## Headline

- **Scenarios in scope:** 65
- **Results available:** 65
- **Passed:** 63
- **Failed:** 2
- **Pass rate (of those with results):** 97%

## Per-Folder Summary

| Folder | Scenarios | Passed | Failed | Missing | Pass rate |
|---|---:|---:|---:|---:|---:|
| `01_supervisor/` | 1 | 1 | 0 | 0 | 100% |
| `11_itinerary_basic/` | 8 | 8 | 0 | 0 | 100% |
| `12_itinerary_mods/` | 8 | 8 | 0 | 0 | 100% |
| `14_itinerary_dates/` | 5 | 5 | 0 | 0 | 100% |
| `15_itinerary_handback/` | 4 | 4 | 0 | 0 | 100% |
| `16_itinerary_destinations/` | 4 | 4 | 0 | 0 | 100% |
| `18_itinerary_context/` | 3 | 3 | 0 | 0 | 100% |
| `19_itinerary_preferences/` | 6 | 6 | 0 | 0 | 100% |
| `30_itinerary_phase0_regression/` | 12 | 11 | 1 | 0 | 92% |
| `32_itinerary_regression/` | 12 | 11 | 1 | 0 | 92% |
| `debug/` | 2 | 2 | 0 | 0 | 100% |

## Failures (quick list)

- `30_itinerary_phase0_regression/` **30.7_phase2_baseline_make_it_cooler_text_reply**
- `32_itinerary_regression/` **R5_ambiguous_europe_city_break**

## Per-Scenario Detail

### `01_supervisor/`

#### ✅ PASS — `1.4_route_to_itinerary`
_Supervisor routes trip planning request to itinerary agent_

_Total time: 9.2s · 1 turn(s)_

**Turn 1** [✓ 9.2s]
> **User:** Plan a 5-day trip to Bali
> **Bot:** Got it — a 5-day trip to Bali.

What departure date would you like?
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 9203ms <= 60000ms
> - ✅ **contains_any**: any of ['when', 'travelers', 'dates', 'departure', 'who', 'Bali', 'trip', 'itinerary', 'beach', 'day', 'thinking'] in response

---

### `11_itinerary_basic/`

#### ✅ PASS — `11.1_immediate_generation`
_P0: All required fields → generates itinerary immediately_

_Total time: 28.4s · 1 turn(s)_

**Turn 1** [✓ 28.4s]
> **User:** Plan a 5-day trip to Bali for 2 adults starting next Monday
> **Bot:** Here's your 5-day Bali itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 28422ms <= 180000ms

---

#### ✅ PASS — `11.2_partial_asks_missing`
_Partial info → asks in numbered list_

_Total time: 7.7s · 1 turn(s)_

**Turn 1** [✓ 7.7s]
> **User:** Plan a 5 day trip to Tokyo
> **Bot:** Perfect — I’ve got **Tokyo** and **5 days**.

What departure date do you want?
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 7703ms <= 60000ms
> - ✅ **contains_any**: any of ['when', 'how long', 'travelers', 'who', 'dates', 'where', 'from', 'origin', 'departing', 'itinerary', 'Tokyo', 'day', 'trip'] in response

---

#### ✅ PASS — `11.3_destination_only`
_Destination only — bot acknowledges Paris and either asks for dates/duration OR offers itinerary/flights/hotels as next steps. The supervisor sometimes routes a destination-only message to general_query for disambiguation instead of create_itinerary; both are acceptable as long as the response surfaces itinerary as a path forward._

_Total time: 6.9s · 1 turn(s)_

**Turn 1** [✓ 6.9s]
> **User:** Plan a trip to Paris
> **Bot:** Absolutely — I can plan your Paris trip.

I’ve got **Paris** as the destination. To build your itinerary, I just need:

1. **When are you going?**
   - e.g. *next Monday, June 10, July 2–6*

2. **How long is the trip?**
   - e.g. *3 days, a week, long weekend*

3. **Who’s traveling?**
   - e.g
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 6859ms <= 30000ms
> - ✅ **contains_any**: any of ['when', 'how long', 'dates', 'departure', 'how many days', 'duration', 'Plan an itinerary', 'itinerary', 'What would you like', 'next', 'Paris'] in response

---

#### ✅ PASS — `11.4_duration_derives_return`
_Duration + start date → parse_dates derives return, generates immediately_

_Total time: 26.6s · 1 turn(s)_

**Turn 1** [✓ 26.6s]
> **User:** Plan a 5-day trip to Rome starting June 20, 2026
> **Bot:** Here's your 5-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 26625ms <= 180000ms

---

#### ✅ PASS — `11.5_vague_timing_with_duration`
_'next week' + duration → parse_dates resolves and generates_

_Total time: 11.7s · 1 turn(s)_

**Turn 1** [✓ 11.7s]
> **User:** 5 day trip to Barcelona next week for 2 adults
> **Bot:** I’ve got **2026-05-25 to 2026-05-31** — that’s a **7-day** window, not 5 days. Does that work for you, or would you like me to adjust it to a true 5-day trip?
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 11734ms <= 180000ms

---

#### ✅ PASS — `11.6_default_1_adult`
_No passengers mentioned — defaults to 1 adult, does NOT ask_

_Total time: 25.5s · 1 turn(s)_

**Turn 1** [✓ 25.5s]
> **User:** Plan a 4-day trip to Amsterdam, June 20, 2026 to June 24, 2026
> **Bot:** Here's your 5-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 25531ms <= 180000ms
> - ✅ **not_contains**: 'how many' absent from response
> - ✅ **not_contains**: 'travelers' absent from response
> - ✅ **not_contains**: 'passengers' absent from response
> - ✅ **not_contains**: 'who's going' absent from response

---

#### ✅ PASS — `11.7_multi_pax_extraction`
_Multi-passenger extraction — 2 adults 2 kids generates immediately_

_Total time: 28.6s · 1 turn(s)_

**Turn 1** [✓ 28.6s]
> **User:** Family trip to Tokyo for 2 adults and 2 kids, June 20, 2026 to June 25, 2026
> **Bot:** Here's your 6-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 28578ms <= 180000ms

---

#### ✅ PASS — `11.8_interests_included`
_Interests in message — itinerary reflects food and culture focus_

_Total time: 31.6s · 1 turn(s)_

**Turn 1** [✓ 31.6s]
> **User:** Plan a food and culture trip to Barcelona, June 20, 2026 to June 25, 2026
> **Bot:** Here's your 6-day Barcelona itinerary, with a focus on food & culture! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 31641ms <= 180000ms
> - ✅ **contains_any**: any of ['food', 'restaurant', 'culinary', 'culture', 'museum', 'art', 'gastronomy', 'tapas', 'Barcelona'] in response

---

### `12_itinerary_mods/`

#### ✅ PASS — `12.1_post_generation_modification`
_P1: After itinerary, 'make it more relaxed' → regenerates with mod_

_Total time: 68.2s · 2 turn(s)_

**Turn 1** [✓ 54.0s]
> **User:** Plan a 3-day trip to Rome for 2 adults starting June 20, 2026, back June 23, 2026
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 53968ms <= 180000ms

**Turn 2** [✓ 14.3s]
> **User:** Make it more relaxed
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 14282ms <= 180000ms

---

#### ✅ PASS — `12.2_add_activity`
_After itinerary, 'add food tours' → regenerates with food focus_

_Total time: 46.9s · 2 turn(s)_

**Turn 1** [✓ 30.1s]
> **User:** Plan a 3-day trip to Rome for 2 adults, June 20, 2026 to June 23, 2026
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 30141ms <= 180000ms

**Turn 2** [✓ 16.8s]
> **User:** Add food tours to the plan
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 16797ms <= 180000ms
> - ✅ **contains_any**: any of ['food', 'culinary', 'restaurant', 'tasting', 'gastronomy', 'cuisine', 'tour', 'Rome', 'pasta', 'gelato'] in response

---

#### ✅ PASS — `12.3_change_duration`
_After itinerary, 'make it 5 days instead' → regenerates with longer plan_

_Total time: 35.6s · 2 turn(s)_

**Turn 1** [✓ 19.3s]
> **User:** Plan a 3-day trip to Barcelona, June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 19344ms <= 180000ms

**Turn 2** [✓ 16.3s]
> **User:** Make it 5 days instead
> **Bot:** Here's your 5-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 16265ms <= 180000ms
> - ✅ **contains_any**: any of ['5', 'five', 'day', 'updated', 'revised', 'extended', 'Barcelona'] in response

---

#### ✅ PASS — `12.4_text_reply_not_regen`
_After itinerary, 'looks great thanks' → text reply, NOT regeneration_

_Total time: 28.3s · 2 turn(s)_

**Turn 1** [✓ 24.9s]
> **User:** Plan a 3-day trip to Tokyo, June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 24922ms <= 180000ms

**Turn 2** [✓ 3.4s]
> **User:** Looks great, thanks!
> **Bot:** Amazing, happy to hear it worked for you ✨🌍 Tokyo is such a fantastic choice — 3 days is just enough for a delicious mix of neon energy, temples, and incredible food 🍣🏯

If you want, I can still help with:
🗺️ tweaking the itinerary
✈️ searching flights
🏨 finding hotels

Just say the word!
> _meta:_ type=`ai_response` · intent=`general_query`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=ai_response
> - ✅ **max_time**: 3406ms <= 180000ms
> - ✅ **contains_any**: any of ['glad', 'great', 'enjoy', 'happy', 'welcome', 'book', 'ready', 'anything else', 'help'] in response

---

#### ✅ PASS — `12.5_question_about_plan`
_After itinerary, question about plan → text reply, not regeneration_

_Total time: 65.8s · 2 turn(s)_

**Turn 1** [✓ 61.9s]
> **User:** Plan a 3-day trip to Paris, June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 61890ms <= 180000ms

**Turn 2** [✓ 3.9s]
> **User:** What's the best thing to do on day 2?
> **Bot:** Day 2 is all about Paris’s big icons: the Louvre, a Seine river cruise, and the Eiffel Tower. If you want the single best “can’t-miss” experience, I’d pick the Seine cruise at sunset — it gives you the most beautiful overall view of the city and ties the whole day together nicely.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **max_time**: 3938ms <= 180000ms
> - ✅ **contains_any**: any of ['day 2', 'Day 2', 'recommend', 'highlight', 'morning', 'afternoon', 'visit', 'Paris'] in response

---

#### ✅ PASS — `12.6_change_to_luxury`
_After itinerary, 'change to 5-star hotels' → regenerates with luxury focus_

_Total time: 56.9s · 2 turn(s)_

**Turn 1** [✓ 39.6s]
> **User:** Plan a 3-day trip to Dubai, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Dubai itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 39562ms <= 180000ms

**Turn 2** [✓ 17.3s]
> **User:** Change to 5-star luxury hotels
> **Bot:** Here's your 4-day Dubai itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 17297ms <= 180000ms
> - ✅ **contains_any**: any of ['5-star', 'luxury', 'premium', 'five-star', 'spa', 'suite', 'Dubai', 'updated', 'revised'] in response

---

#### ✅ PASS — `12.7_change_pace`
_After itinerary, 'make it more packed' → regenerates with more activities_

_Total time: 61.1s · 2 turn(s)_

**Turn 1** [✓ 42.1s]
> **User:** Plan a 3-day trip to London, June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 42141ms <= 180000ms

**Turn 2** [✓ 18.9s]
> **User:** Make it more packed with activities
> **Bot:** Here's your 4-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 18938ms <= 180000ms
> - ✅ **contains_any**: any of ['packed', 'activity', 'activities', 'busy', 'full', 'London', 'updated', 'revised'] in response

---

#### ✅ PASS — `12.8_add_food_interest`
_After itinerary, 'add more food experiences' → regenerates with food focus_

_Total time: 71.2s · 2 turn(s)_

**Turn 1** [✓ 49.2s]
> **User:** Plan a 3-day trip to Bangkok, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Bangkok itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 49219ms <= 180000ms

**Turn 2** [✓ 22.0s]
> **User:** Add more food experiences
> **Bot:** Here's your 4-day Bangkok itinerary, with a focus on food! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 22031ms <= 180000ms
> - ✅ **contains_any**: any of ['food', 'restaurant', 'street food', 'culinary', 'tasting', 'cuisine', 'Bangkok', 'Thai'] in response

---

### `14_itinerary_dates/`

#### ✅ PASS — `14.1_explicit_date_range`
_Explicit date range → generates immediately_

_Total time: 68.1s · 1 turn(s)_

**Turn 1** [✓ 68.1s]
> **User:** Plan a trip to Paris, June 20, 2026 to June 25, 2026, 2 adults
> **Bot:** Here's your 6-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 68140ms <= 180000ms

---

#### ✅ PASS — `14.2_relative_dates`
_Relative date + duration → parse_dates resolves, generates_

_Total time: 27.6s · 1 turn(s)_

**Turn 1** [✓ 27.6s]
> **User:** 3-day trip to Barcelona starting next Friday
> **Bot:** Here's your 3-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 27641ms <= 180000ms

---

#### ✅ PASS — `14.3_season_reference`
_Seasonal reference → parse_dates handles or asks for specifics_

_Total time: 8.8s · 1 turn(s)_

**Turn 1** [✓ 8.8s]
> **User:** Plan a trip to Tokyo during cherry blossom season
> **Bot:** Tokyo during cherry blossom season sounds amazing 🌸

I still need your travel dates to build the plan:
1. **When are you thinking of going?**
   - e.g. **late March**, **April 1–7**, or **next spring**

If you want, I can help narrow it down for cherry blossom timing in Tokyo too.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 8750ms <= 180000ms
> - ✅ **contains_any**: any of ['cherry blossom', 'spring', 'March', 'April', 'sakura', 'Tokyo', 'when', 'dates', 'itinerary', 'day'] in response

---

#### ✅ PASS — `14.4_duration_only_no_start`
_Duration but no start date → asks when to depart_

_Total time: 9.9s · 1 turn(s)_

**Turn 1** [✓ 9.9s]
> **User:** Plan a 4-day trip to Rome
> **Bot:** Great — I’ve got your **4-day trip to Rome**.

I just need one more thing:
1. **When do you want to go?**
   Examples: **next Monday**, **June 10**, **July 4–7**
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 9922ms <= 30000ms
> - ✅ **contains_any**: any of ['when', 'departure', 'date', 'start', 'depart', 'travel'] in response

---

#### ✅ PASS — `14.5_long_weekend`
_Long weekend → parse_dates resolves or asks clarification_

_Total time: 29.3s · 1 turn(s)_

**Turn 1** [✓ 29.3s]
> **User:** Plan a long weekend trip to Amsterdam starting next Friday
> **Bot:** Here's your 3-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 29328ms <= 180000ms
> - ✅ **contains_any**: any of ['Amsterdam', 'weekend', 'Friday', 'Saturday', 'Sunday', '3', 'day', 'itinerary', 'when'] in response

---

### `15_itinerary_handback/`

#### ✅ PASS — `15.1_book_everything`
_After itinerary, 'book everything' → hands back to supervisor for flight+hotel_

_Total time: 93.6s · 2 turn(s)_

**Turn 1** [✓ 60.5s]
> **User:** Plan a 3-day trip to Paris from London, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 60547ms <= 180000ms

**Turn 2** [✓ 33.0s]
> **User:** Book everything
> **Bot:** We found 2303 hotels in Paris. They’re displayed above the chat.

To complete your booking, click the **Book** button on your preferred hotel card.
> _meta:_ type=`hotel_search_results` · intent=`hotel_conversation`
>
> Assertions:
> - ✅ **type_in**: expected in ['flight_conversation', 'flight_search_results', 'hotel_conversation', 'hotel_search_results', 'ai_response', 'message', 'itinerary_conversation'] got=hotel_search_results
> - ✅ **max_time**: 33047ms <= 180000ms
> - ✅ **contains_any**: any of ['flight', 'hotel', 'book', 'search', 'London', 'Paris', 'booking'] in response

---

#### ✅ PASS — `15.2_book_flights`
_After itinerary, 'book flights' → routes to flight agent_

_Total time: 41.0s · 2 turn(s)_

**Turn 1** [✓ 25.0s]
> **User:** Plan a 3-day trip to Barcelona from Amsterdam, June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 25047ms <= 180000ms

**Turn 2** [✓ 15.9s]
> **User:** Book flights
> **Bot:** Found 50 flight options from Amsterdam to Barcelona for June 20–23, 2026. They’re displayed above the chat.

To complete your booking, click the **BOOK NOW** button on the flight you want.
> _meta:_ type=`flight_search_results` · intent=`flight_conversation`
>
> Assertions:
> - ✅ **type_in**: expected in ['flight_conversation', 'flight_search_results', 'ai_response', 'message', 'itinerary_conversation'] got=flight_search_results
> - ✅ **max_time**: 15937ms <= 180000ms
> - ✅ **contains_any**: any of ['flight', 'Amsterdam', 'Barcelona', 'search', 'booking', 'origin', 'destination'] in response

---

#### ✅ PASS — `15.3_book_hotels`
_After itinerary, 'find hotels' → routes to hotel agent_

_Total time: 56.4s · 2 turn(s)_

**Turn 1** [✓ 20.8s]
> **User:** Plan a 3-day trip to Tokyo, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 20766ms <= 180000ms

**Turn 2** [✓ 35.6s]
> **User:** Find hotels in Tokyo
> **Bot:** We found 1,184 hotels in Tokyo. They’re displayed above the chat.

To start booking, click the **Book** button on a hotel card.
> _meta:_ type=`hotel_search_results` · intent=`hotel_conversation`
>
> Assertions:
> - ✅ **type_in**: expected in ['hotel_conversation', 'hotel_search_results', 'ai_response', 'message', 'itinerary_conversation'] got=hotel_search_results
> - ✅ **max_time**: 35625ms <= 180000ms
> - ✅ **contains_any**: any of ['hotel', 'Tokyo', 'check-in', 'checkin', 'room', 'search', 'accommodation', 'dates', 'guests'] in response

---

#### ✅ PASS — `15.4_out_of_scope`
_During planning, out-of-scope question → handles as detour or answers [TEMP LOOSENED PR#1108 — new capability_check node (PR#1077) intercepts; tighten when limitations are narrowed]_

_Total time: 40.2s · 2 turn(s)_

**Turn 1** [✓ 39.9s]
> **User:** Plan a 5-day trip to Bali, June 20, 2026 to June 25, 2026, 1 adult
> **Bot:** Here's your 6-day Bali itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 39890ms <= 180000ms

**Turn 2** [✓ 0.3s]
> **User:** Do I need a visa for Bali?
> **Bot:** Voya doesn't check live visa or entry requirements — those change too often for me to keep accurate. Check the destination country's official embassy site. Want me to continue your itinerary? Visa requirements you'll need to verify on your own.
> _meta:_ type=`capability_disclosure` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation', 'capability_disclosure'] got=capability_disclosure
> - ✅ **max_time**: 344ms <= 30000ms
> - ✅ **contains_any**: any of ['visa', 'Indonesia', 'passport', 'entry', 'requirement', 'tourist', 'days', 'Bali', "can't", 'cannot', "don't have", 'live'] in response

---

### `16_itinerary_destinations/`

#### ✅ PASS — `16.1_city_abbreviation`
_City abbreviation 'NYC' → resolves to New York, generates_

_Total time: 29.3s · 1 turn(s)_

**Turn 1** [✓ 29.3s]
> **User:** Plan a 4-day trip to NYC, June 20, 2026 to June 24, 2026, 1 adult
> **Bot:** Here's your 5-day NYC itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 29281ms <= 180000ms
> - ✅ **contains_any**: any of ['New York', 'NYC', 'Manhattan', 'Brooklyn', 'Central Park', 'itinerary', 'day'] in response

---

#### ✅ PASS — `16.2_vague_destination`
_Vague destination 'beach vacation' → asks which city_

_Total time: 13.0s · 1 turn(s)_

**Turn 1** [✓ 13.0s]
> **User:** Plan a beach vacation for next month
> **Bot:** Great — I’ve got the dates for next month: **June 1, 2026 to June 30, 2026**.

What beach destination would you like? A few easy picks:
1. **Cancún**
2. **Tulum**
3. **Puerto Vallarta**

Or tell me your own destination and I’ll build your plan.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 13047ms <= 30000ms
> - ✅ **contains_any**: any of ['which', 'where', 'city', 'destination', 'beach', 'specific', 'mind', 'how long', 'trip', 'vacation', 'length', 'days', 'week', 'month', 'vibe'] in response

---

#### ✅ PASS — `16.3_country_name`
_Country name 'Japan' → picks city (Tokyo) or asks which city_

_Total time: 24.2s · 1 turn(s)_

**Turn 1** [✓ 24.2s]
> **User:** Plan a 5-day trip to Japan, June 20, 2026 to June 25, 2026
> **Bot:** Here's your 6-day Japan itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 24157ms <= 180000ms
> - ✅ **contains_any**: any of ['Tokyo', 'Kyoto', 'Osaka', 'Japan', 'city', 'which', 'itinerary', 'day'] in response

---

#### ✅ PASS — `16.4_destination_with_purpose`
_Destination + purpose → treats as trip planning, not hand-back_

_Total time: 41.6s · 1 turn(s)_

**Turn 1** [✓ 41.6s]
> **User:** Plan a trip to London for a conference, June 20, 2026 to June 24, 2026, 1 adult
> **Bot:** Here's your 5-day London itinerary, with a focus on conference! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 41593ms <= 180000ms
> - ✅ **contains_any**: any of ['London', 'conference', 'itinerary', 'day', 'business', 'meeting'] in response

---

### `18_itinerary_context/`

#### ✅ PASS — `18.1_has_origin`
_Origin provided → appears in itinerary response_

_Total time: 59.9s · 1 turn(s)_

**Turn 1** [✓ 59.9s]
> **User:** Plan a 4-day trip from Amsterdam to Paris, June 20, 2026 to June 24, 2026, 1 adult
> **Bot:** Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 59906ms <= 180000ms
> - ✅ **contains_any**: any of ['Amsterdam', 'Paris', 'fly', 'arrive', 'depart', 'itinerary', 'day'] in response

---

#### ✅ PASS — `18.2_response_has_dates`
_Full fields → response includes structured data with dates_

_Total time: 49.2s · 1 turn(s)_

**Turn 1** [✓ 49.2s]
> **User:** Plan a 3-day trip to Rome, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **has_data**: expected=True got=True
> - ✅ **max_time**: 49234ms <= 180000ms

---

#### ✅ PASS — `18.3_structured_itinerary`
_Generated itinerary includes structured_itinerary in response data_

_Total time: 29.8s · 1 turn(s)_

**Turn 1** [✓ 29.8s]
> **User:** Plan a 4-day trip to Barcelona, June 20, 2026 to June 24, 2026, 1 adult
> **Bot:** Here's your 5-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **has_data**: expected=True got=True
> - ✅ **max_time**: 29781ms <= 180000ms

---

### `19_itinerary_preferences/`

#### ✅ PASS — `19.1_food_culture`
_Food and culture interests → itinerary reflects culinary/museum focus_

_Total time: 27.1s · 1 turn(s)_

**Turn 1** [✓ 27.1s]
> **User:** Plan a food and culture trip to Barcelona, June 20, 2026 to June 25, 2026, 2 adults
> **Bot:** Here's your 6-day Barcelona itinerary, with a focus on food & culture! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 27094ms <= 180000ms
> - ✅ **contains_any**: any of ['food', 'restaurant', 'culinary', 'culture', 'museum', 'art', 'tapas', 'gastronomy', 'market', 'Sagrada', 'Barcelona', 'itinerary'] in response

---

#### ✅ PASS — `19.2_adventure`
_Adventure interests → hiking/outdoor focused itinerary_

_Total time: 24.7s · 1 turn(s)_

**Turn 1** [✓ 24.7s]
> **User:** Plan an adventure trip to Queenstown, June 20, 2026 to June 25, 2026, 2 adults
> **Bot:** Here's your 6-day Queenstown itinerary, with a focus on adventure! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 24671ms <= 180000ms
> - ✅ **contains_any**: any of ['adventure', 'hiking', 'outdoor', 'bungee', 'jet', 'rafting', 'mountain', 'thrill', 'Queenstown', 'extreme', 'skydive'] in response

---

#### ✅ PASS — `19.3_luxury`
_Luxury budget → upscale 5-star itinerary_

_Total time: 45.3s · 1 turn(s)_

**Turn 1** [✓ 45.3s]
> **User:** Plan a luxury 5-star trip to Dubai, June 20, 2026 to June 25, 2026, 2 adults
> **Bot:** Here's your 6-day Dubai itinerary, with a focus on luxury & 5-star! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 45281ms <= 180000ms
> - ✅ **contains_any**: any of ['luxury', '5-star', 'premium', 'spa', 'fine dining', 'suite', 'Dubai', 'Burj', 'exclusive', 'private'] in response

---

#### ✅ PASS — `19.4_budget_friendly`
_Budget-friendly → cost-conscious itinerary with affordable options_

_Total time: 53.0s · 1 turn(s)_

**Turn 1** [✓ 53.0s]
> **User:** Plan a budget-friendly trip to Bangkok, June 20, 2026 to June 25, 2026, 1 adult
> **Bot:** Here's your 6-day Bangkok itinerary, with a focus on budget-friendly! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 53047ms <= 180000ms
> - ✅ **contains_any**: any of ['budget', 'affordable', 'cheap', 'street food', 'free', 'hostel', 'Bangkok', 'temple', 'market', 'backpack'] in response

---

#### ✅ PASS — `19.5_family_trip`
_Family trip with kids → kid-friendly activities_

_Total time: 24.9s · 1 turn(s)_

**Turn 1** [✓ 24.9s]
> **User:** Plan a family trip to Orlando for 2 adults and 2 kids, June 20, 2026 to June 25, 2026
> **Bot:** Here's your 6-day Orlando itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 24907ms <= 180000ms
> - ✅ **contains_any**: any of ['family', 'kids', 'children', 'theme park', 'Disney', 'Universal', 'Orlando', 'fun', 'ride'] in response

---

#### ✅ PASS — `19.6_nightlife`
_Nightlife focus → evening/bar/club activities_

_Total time: 29.4s · 1 turn(s)_

**Turn 1** [✓ 29.4s]
> **User:** Plan a nightlife trip to Berlin, June 20, 2026 to June 24, 2026, 2 adults
> **Bot:** Here's your 5-day Berlin itinerary, with a focus on nightlife! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 29407ms <= 180000ms
> - ✅ **contains_any**: any of ['nightlife', 'bar', 'club', 'evening', 'night', 'Berlin', 'party', 'cocktail', 'pub', 'techno'] in response

---

### `30_itinerary_phase0_regression/`

#### ✅ PASS — `30.10_amend_make_more_relaxed_regenerates`
_P0 baseline (#1053): pace-change amend ('make it more relaxed') is in today's MODE 2 list and regenerates. Positive baseline — Phase 2 must keep this regen path._

_Total time: 50.8s · 2 turn(s)_

**Turn 1** [✓ 32.3s]
> **User:** Plan a 4-day trip to Barcelona, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 32344ms <= 90000ms
> - ✅ **min_days**: got 4 >= 4

**Turn 2** [✓ 18.5s]
> **User:** Make it more relaxed
> **Bot:** Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 18469ms <= 90000ms
> - ✅ **contains_any**: any of ['relaxed', 'slower', 'easy', 'Barcelona', 'pace', 'fewer', 'leisurely'] in response

---

#### ✅ PASS — `30.11_schema_7day_has_7_days`
_P0 baseline (#1053): schema invariant — a 7-day trip must produce 7 entries in structured_itinerary.itineraryItems. Locks the day-count match so Phase 4 (two-stage gen / caching) can't accidentally drop or duplicate days._

_Total time: 34.9s · 1 turn(s)_

**Turn 1** [✓ 34.9s]
> **User:** Plan a 7-day trip to Barcelona, June 20, 2026 to June 26, 2026, 2 adults
> **Bot:** Here's your 7-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 34875ms <= 120000ms
> - ✅ **min_days**: got 7 >= 7

---

#### ✅ PASS — `30.12_cold_turn_latency_guard`
_P0 latency guardrail (#1053): cold-turn itinerary with full input must complete under 90s today. This is a generous upper bound (#1053 §1 measures ~36-70s p50). Phase 3 (skeleton streaming + early kickoff) should drop this to <30s — at which point the threshold here should be tightened as part of that PR's docs update._

_Total time: 28.5s · 1 turn(s)_

**Turn 1** [✓ 28.5s]
> **User:** Plan a 4-day trip from Paris to Lisbon, June 20, 2026 to June 23, 2026, 2 adults
> **Bot:** Here's your 4-day Lisbon itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 28516ms <= 90000ms
> - ✅ **min_days**: got 4 >= 4

---

#### ✅ PASS — `30.1_cold_paris_5day_full_input`
_P0 baseline (#1053): cold-turn full-input itinerary. Asserts day-count + latency on main. NOTE: once #1034 (the side-search orchestrator that adds data.flights[] / data.hotels[] arrays) merges to main, this scenario must be tightened to add expect_min_flights: 1 and expect_min_hotels: 1._

_Total time: 70.9s · 1 turn(s)_

**Turn 1** [✓ 70.9s]
> **User:** Plan a 5-day trip from London to Paris, June 20, 2026 to June 24, 2026, 2 adults
> **Bot:** Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 70891ms <= 90000ms
> - ✅ **min_days**: got 5 >= 5

---

#### ✅ PASS — `30.2_cold_tokyo_3day_no_origin`
_P0 baseline (#1053): cold-turn partial-input (no origin). Asserts day-count + latency on main. NOTE: once #1034 (#1038 side-search orchestrator) merges to main, this scenario must be tightened — _FLIGHT_REQUIRED needs origin_iata so flight rail will be silently skipped (expect_max_flights: 0) while hotel rail still fires (expect_min_hotels: 1)._

_Total time: 20.0s · 1 turn(s)_

**Turn 1** [✓ 20.0s]
> **User:** Plan a 3-day trip to Tokyo, June 20, 2026 to June 22, 2026, 1 adult
> **Bot:** Here's your 3-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 20047ms <= 90000ms
> - ✅ **min_days**: got 3 >= 3

---

#### ✅ PASS — `30.3_cold_oneway_amsterdam_to_rome`
_P0 baseline (#1053): one-way trip — #1038 _HOTEL_REQUIRED needs return_date, so hotel rail is silently skipped on one-way. Locked here; itinerary follow-up may derive return from duration and flip this to also include hotels._

_Total time: 30.4s · 1 turn(s)_

**Turn 1** [✓ 30.4s]
> **User:** Plan a 4-day trip from Amsterdam to Rome, one way starting June 20, 2026, 1 adult
> **Bot:** Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 30375ms <= 90000ms
> - ✅ **min_days**: got 4 >= 4

---

#### ✅ PASS — `30.4_phase2_baseline_dateless_duration`
_P0 Phase-2 baseline (#1053): today, the hard date gate (itinerary_agent.py:188, tools/itinerary.py:528) forces a clarifying turn when the user gives a duration but no date anchor. Locked here so Phase 2 (O9 — soften the date gate via placeholder dates + chip) can be detected as an intentional change. When Phase 2 ships, this scenario must be updated with a justified loosening._

_Total time: 8.8s · 1 turn(s)_

**Turn 1** [✓ 8.8s]
> **User:** Plan a 4-day trip to Rome
> **Bot:** Got it — a 4-day trip to Rome.

1. **When would you like to go?** (e.g. next Monday, June 10, or July 3–7)
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 8828ms <= 30000ms
> - ✅ **contains_any**: any of ['when', 'dates', 'departure', 'how long', 'start', 'trip dates'] in response
> - ✅ **not_contains**: 'Here's your 4-day Rome itinerary' absent from response
> - ✅ **not_contains**: 'Here is your 4-day' absent from response

---

#### ✅ PASS — `30.5_phase2_baseline_vague_destination`
_P0 Phase-2 baseline (#1053): the prompt at itinerary_agent.py:195-199 says don't accept vague destinations, but empirically the bot today already suggests a concrete one (e.g. Cancún for 'somewhere warm') and asks for dates. This locks the observed current behavior — the bot must NOT immediately ship a full itinerary on a vague destination without first asking at least one follow-up. Phase 2 (O11 — suggest with a confirmation chip) refines this further._

_Total time: 5.8s · 1 turn(s)_

**Turn 1** [✓ 5.8s]
> **User:** Plan a trip somewhere warm
> **Bot:** Oh, amazing choice ☀️🌴 If you want somewhere warm, a few great vibes come to mind:

🇲🇽 **Cancún / Riviera Maya** — beachy, easygoing, and ideal for sun + turquoise water
🇵🇹 **Madeira** — warm, scenic, and perfect if you want beautiful hikes and ocean views
🇹🇭 **Phuket** — tropical, lively, and f
> _meta:_ type=`ai_response` · intent=`general_query`
>
> Assertions:
> - ✅ **max_time**: 5844ms <= 30000ms
> - ✅ **not_contains**: 'Here's your' absent from response
> - ✅ **not_contains**: 'Here is your' absent from response

---

#### ✅ PASS — `30.6_phase2_baseline_ambiguous_dates_confirm`
_P0 Phase-2 baseline (#1053): today, ambiguous-date expressions like 'next week' trigger a forced confirmation turn before the bot generates (itinerary_agent.py:85-97). Locked here so Phase 2 (O9 — skip confirmation when duration is given alongside) can be detected. The first turn should NOT be itinerary_results today._

_Total time: 12.8s · 1 turn(s)_

**Turn 1** [✓ 12.8s]
> **User:** Plan a 5-day trip to Paris next week, 1 adult
> **Bot:** I’ve got **May 25, 2026 to May 31, 2026** for “next week” — that’s a **7-day trip**.

You also mentioned **1 adult**, so the only thing I need to confirm is: **do you want to stick with those dates, or would you like a different 5-day window for Paris?**
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 12844ms <= 30000ms
> - ✅ **contains_any**: any of ['confirm', 'does that work', 'sound right', '2026', 'May', 'June'] in response
> - ✅ **not_contains**: 'Here's your 5-day Paris itinerary' absent from response
> - ✅ **not_contains**: 'Here is your 5-day Paris itinerary' absent from response

---

#### ❌ FAIL — `30.7_phase2_baseline_make_it_cooler_text_reply`
_P0 Phase-2 baseline (#1053): today, vague amend phrasing like 'make it cooler' falls outside the MODE 2 regen gate (itinerary_agent.py:142-147) and yields a text reply asking what to change, not a regen. Locked so Phase 2 (broaden the regen gate) is detectable._

_Total time: 70.3s · 2 turn(s)_

**Turn 1** [✓ 51.6s]
> **User:** Plan a 3-day trip to Rome, June 20, 2026 to June 22, 2026, 1 adult
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 51609ms <= 90000ms
> - ✅ **min_days**: got 3 >= 3

**Turn 2** [✗ 18.7s]
> **User:** Make it cooler
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ❌ **type_in**: expected in ['ai_response', 'itinerary_conversation', 'message'] got=itinerary_results
> - ✅ **max_time**: 18735ms <= 30000ms
> - ❌ **not_contains**: 'Here's your' absent from response
> - ✅ **not_contains**: 'Here is your' absent from response

**Why it failed:**
- Turn 2 — `type_in`: expected in ['ai_response', 'itinerary_conversation', 'message'] got=itinerary_results
- Turn 2 — `not_contains`: 'Here's your' absent from response

---

#### ✅ PASS — `30.8_phase2_baseline_regenerate_day_3`
_P0 Phase-2 baseline (#1053): today, day-targeted regen requests ('regenerate day 3') do not match the narrow MODE 2 list; the bot replies with text rather than regenerating. Locked so Phase 2 (O12 — allow day-targeted regen) is detectable. Must be loosened with justification when O12 ships._

_Total time: 41.0s · 2 turn(s)_

**Turn 1** [✓ 25.4s]
> **User:** Plan a 3-day trip to Rome, June 20, 2026 to June 22, 2026, 1 adult
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 25391ms <= 90000ms
> - ✅ **min_days**: got 3 >= 3

**Turn 2** [✓ 15.6s]
> **User:** Regenerate day 3
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'itinerary_conversation', 'message', 'itinerary_results'] got=itinerary_results
> - ✅ **max_time**: 15609ms <= 60000ms

---

#### ✅ PASS — `30.9_amend_food_focus_regenerates`
_P0 baseline (#1053): concrete amend with a named focus ('change day 2 to focus on food') is in the MODE 2 list today and triggers a regen. This is the *positive* baseline — should keep regenerating after Phase 2 ships, otherwise we broke something._

_Total time: 56.6s · 2 turn(s)_

**Turn 1** [✓ 35.3s]
> **User:** Plan a 3-day trip to Rome, June 20, 2026 to June 22, 2026, 2 adults
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 35344ms <= 90000ms
> - ✅ **min_days**: got 3 >= 3

**Turn 2** [✓ 21.3s]
> **User:** Change day 2 to focus on food
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 21297ms <= 90000ms
> - ✅ **contains_any**: any of ['food', 'culinary', 'restaurant', 'tasting', 'Rome', 'pasta', 'gelato', 'trattoria'] in response

---

### `32_itinerary_regression/`

#### ✅ PASS — `R10_partial_no_origin`
_REGRESSION (#1053 Phase 0): partial input — no origin. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Pins CURRENT behavior when flight side-search is skipped (no origin → no _FLIGHT_REQUIRED match). Phase 1 plumbing wins should not silently change this._

_Total time: 26.4s · 1 turn(s)_

**Turn 1** [✓ 26.4s]
> **User:** Plan 4 days in Madrid for 1 adult from June 20, 2026 to June 23, 2026
> **Bot:** Here's your 4-day Madrid itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 26359ms <= 180000ms

---

#### ✅ PASS — `R11_partial_no_dates`
_REGRESSION (#1053 Phase 0+2): partial input — duration without anchor date. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. PHASE 2 BASELINE UPDATE 2026-05-21: Phase 2 O9b (option B from the doc) replaced 'just ask when?' with 'offer 3 candidate date windows near/mid/later + let the user pick or give their own dates'. The block_dateless_generation tool guard stays in place as a backstop. The expect_contains_any list matches both behaviors (still asks for a date one way or another)._

_Total time: 8.8s · 1 turn(s)_

**Turn 1** [✓ 8.8s]
> **User:** Plan a 4-day trip to Vienna for 2 adults
> **Bot:** Got it — a 4-day Vienna trip for 2 adults.

1. **When do you want to leave?**
   You can say a date like **June 10** or **next Friday**.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **max_time**: 8812ms <= 30000ms
> - ✅ **contains_any**: any of ['date', 'when', 'start', 'leave', 'departure', 'depart'] in response

---

#### ✅ PASS — `R12_partial_no_destination`
_REGRESSION (#1053 Phase 0): partial input — no destination, only travel intent + dates. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Pins CURRENT behavior on destination-less inputs._

_Total time: 11.5s · 1 turn(s)_

**Turn 1** [✓ 11.5s]
> **User:** I want to plan a trip from June 20, 2026 to June 24, 2026, 2 adults
> **Bot:** Got it — I’ve saved your dates for **June 20, 2026 to June 24, 2026** for **2 adults**.

1. **Where are you going?**
   Example: Paris, Tokyo, Cancun, New York
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **max_time**: 11531ms <= 30000ms
> - ✅ **contains_any**: any of ['where', 'destination', 'city', 'country', 'going', 'place'] in response

---

#### ✅ PASS — `R1_cold_paris_5day`
_REGRESSION (#1053 Phase 0): cold-turn 5-day Paris trip. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Pins baseline behavior on the canonical cold-turn shape so Phase 2 prompt softening can be a known delta against this baseline._

_Total time: 21.0s · 1 turn(s)_

**Turn 1** [✓ 21.0s]
> **User:** Plan a 5-day trip to Paris from June 20, 2026 to June 24, 2026
> **Bot:** Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 21047ms <= 180000ms

---

#### ✅ PASS — `R2_cold_tokyo_3day`
_REGRESSION (#1053 Phase 0): cold-turn 3-day Tokyo trip. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Asia destination + shorter duration covers a different LLM call shape than R1._

_Total time: 24.4s · 1 turn(s)_

**Turn 1** [✓ 24.4s]
> **User:** Plan 3 days in Tokyo from July 5, 2026 to July 7, 2026, 2 adults
> **Bot:** Here's your 3-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 24360ms <= 180000ms

---

#### ✅ PASS — `R3_cold_rome_weekend`
_REGRESSION (#1053 Phase 0): weekend Rome trip with relative-date phrasing. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Exercises parse_dates on 'weekend' phrasing._

_Total time: 21.6s · 1 turn(s)_

**Turn 1** [✓ 21.6s]
> **User:** Plan a weekend in Rome starting June 11, 2026, 1 adult
> **Bot:** Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 21563ms <= 180000ms

---

#### ✅ PASS — `R4_ambiguous_somewhere_warm`
_REGRESSION (#1053 Phase 0+2): ambiguous destination ('somewhere warm'). NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. PHASE 2 BASELINE UPDATE 2026-05-21: Phase 2 O11 changed behavior from 'refuse + ask for a city' to 'suggest 2-3 specific cities matching the vibe + ask user to pick'. The expect_contains_any list now matches both old (refuse/ask) and new (suggest specific city names) behavior — both are graceful handling of vague input. If a future change reintroduces silent city invention (R6's old bug), this scenario must fail._

_Total time: 14.2s · 1 turn(s)_

**Turn 1** [✓ 14.2s]
> **User:** I want to go somewhere warm next month for 5 days
> **Bot:** Got it — a 5-day trip next month is set.

1. **Where to go?**
   For a warm vibe, I can help you pick a spot once you tell me the destination.

If you want, I can suggest a few warm places too.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=message
> - ✅ **max_time**: 14157ms <= 30000ms
> - ✅ **contains_any**: any of ['city', 'destination', 'where', 'specific', 'Cancún', 'Lisbon', 'Bali', 'warm', 'tropical', 'Caribbean'] in response

---

#### ❌ FAIL — `R5_ambiguous_europe_city_break`
_REGRESSION (#1053 Phase 0+2): regional vague destination ('Europe city break'). NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. PHASE 2 BASELINE UPDATE 2026-05-21: Phase 2 O11 changed behavior from 'refuse + ask for specific city' to 'suggest 2-3 specific European cities + ask user to pick'. The expect_contains_any list matches both old and new behavior._

_Total time: 25.5s · 1 turn(s)_

**Turn 1** [✗ 25.5s]
> **User:** Looking for a 4-day Europe city break in July
> **Bot:** Here's your 4-day Europe itinerary, with a focus on city break! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ❌ **type_in**: expected in ['ai_response', 'message', 'itinerary_conversation'] got=itinerary_results
> - ✅ **max_time**: 25516ms <= 30000ms
> - ✅ **contains_any**: any of ['city', 'destination', 'which', 'specific', 'Paris', 'Barcelona', 'Lisbon', 'Prague', 'Europe'] in response

**Why it failed:**
- Turn 1 — `type_in`: expected in ['ai_response', 'message', 'itinerary_conversation'] got=itinerary_results

---

#### ✅ PASS — `R6_ambiguous_chill_5_days`
_REGRESSION (#1053 Phase 0+2): vibe-only input ('somewhere chill'). NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. PHASE 2 BASELINE UPDATE 2026-05-21: Phase 2 O11 fixed the bug captured here (bot used to invent a city literally called 'Somewhere Chill'); new behavior suggests 2-3 specific chill destinations and asks user to pick. The expect_contains_any list now matches both the old buggy behavior (in case Phase 2 regresses) and the new graceful behavior. If a future change reintroduces silent invention of nonsense city names, this scenario must fail._

_Total time: 13.9s · 1 turn(s)_

**Turn 1** [✓ 13.9s]
> **User:** 5 days, somewhere chill, 1 adult, starting June 20, 2026
> **Bot:** Nice — I’ve got the timing and traveler count:

- **5 days**
- **1 adult**
- **Starting June 20, 2026**

What place are we heading to? You can name a city or vibe, for example:
1. **A specific city** — e.g. Lisbon, Bali, Cancun
2. **A chill vibe** — I can suggest a few good matches
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=message
> - ✅ **max_time**: 13907ms <= 60000ms
> - ✅ **contains_any**: any of ['chill', 'itinerary', 'city', 'destination', 'specific', '5-day', '5 days', 'relax', 'where'] in response

---

#### ✅ PASS — `R7_amend_day_2_food`
_REGRESSION (#1053 Phase 0): post-generation amend (day-targeted food focus). NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Pins CURRENT amend behavior; Phase 2 will broaden the regen triggers._

_Total time: 47.8s · 2 turn(s)_

**Turn 1** [✓ 27.2s]
> **User:** Plan a 3-day trip to Lisbon from June 20, 2026 to June 22, 2026, 1 adult
> **Bot:** Here's your 3-day Lisbon itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 27218ms <= 180000ms

**Turn 2** [✓ 20.5s]
> **User:** Change day 2 to focus on food and restaurants
> **Bot:** Here's your 3-day Lisbon itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 20547ms <= 180000ms

---

#### ✅ PASS — `R8_amend_make_cheaper`
_REGRESSION (#1053 Phase 0): post-generation budget amend. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. Pins CURRENT behavior on price-driven modification requests._

_Total time: 49.1s · 2 turn(s)_

**Turn 1** [✓ 33.2s]
> **User:** Plan a 3-day trip to Barcelona from June 20, 2026 to June 22, 2026, 2 adults
> **Bot:** Here's your 3-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 33250ms <= 180000ms

**Turn 2** [✓ 15.8s]
> **User:** Make it cheaper
> **Bot:** Here's your 3-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 15828ms <= 180000ms

---

#### ✅ PASS — `R9_amend_regenerate_day_3`
_REGRESSION (#1053 Phase 0+2): targeted-day regeneration. NEVER LOOSEN — see tools/chat/scenarios/CONTRIBUTING.md regression suite policy. PHASE 2 BASELINE UPDATE 2026-05-21: Phase 2 O12 added 'regenerate day N' to the regen trigger list; behavior now produces an updated itinerary (itinerary_results) instead of a text reply. The expect_type_in already accepts both behaviors so the scenario stays green across the transition; tighten in a follow-up once the new behavior is stable._

_Total time: 45.1s · 2 turn(s)_

**Turn 1** [✓ 25.8s]
> **User:** Plan a 4-day trip to Amsterdam from June 20, 2026 to June 23, 2026, 1 adult
> **Bot:** Here's your 4-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation'] got=itinerary_results
> - ✅ **intent**: expected=create_itinerary got=create_itinerary
> - ✅ **max_time**: 25813ms <= 180000ms

**Turn 2** [✓ 19.3s]
> **User:** Regenerate day 3
> **Bot:** Here's your 4-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'itinerary_conversation', 'ai_response', 'message'] got=itinerary_results
> - ✅ **max_time**: 19328ms <= 180000ms

---

### `debug/`

#### ✅ PASS — `b219_amend_no_itinerary`
_Session b219ab9d: User asks to amend itinerary that doesn't exist in this session. Should tell user clearly and offer to create a new one. Note: ``paste`` removed from the deny list because the bot's primary response is the helpful 'I can help you amend the itinerary, just send me the days/stops/style' path; suggesting paste as a secondary fallback no longer counts as a stall. The stronger imperative phrases ('send me your itinerary' / 'copy your itinerary') still trip the test._

_Total time: 36.1s · 3 turn(s)_

**Turn 1** [✓ 7.2s]
> **User:** Hi Voya can you help me to amend my itinerary for London, i live here and I would like to start my day at 10 am
> **Bot:** Absolutely — I can help create a fresh London plan for you, but I don’t have a previous itinerary saved in this chat.

I do have:
- **Destination:** London
- **Origin:** London
- **Preference:** start the day at **10:00 AM**

If you want, I can build a new itinerary for you right away — just send:
1
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 7187ms <= 30000ms
> - ✅ **contains_any**: any of ['help', 'create', 'plan', 'amend', 'London', 'trip', 'itinerary'] in response
> - ✅ **not_contains**: 'send me your itinerary' absent from response
> - ✅ **not_contains**: 'copy your itinerary' absent from response

**Turn 2** [✓ 10.1s]
> **User:** next week for 5 days
> **Bot:** I’ve got **2026-05-25 to 2026-05-29** for your **5-day** London trip.

You mentioned starting the day at **10 AM** too — got it. If that date range works, I can build your itinerary right away.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **max_time**: 10141ms <= 30000ms
> - ✅ **contains_any**: any of ['2026', 'does that work', 'sound right', 'confirm'] in response

**Turn 3** [✓ 18.8s]
> **User:** yes
> **Bot:** Here's your 5-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'message'] got=itinerary_results
> - ✅ **max_time**: 18750ms <= 60000ms
> - ✅ **contains_any**: any of ['itinerary', 'London', 'plan', 'generate'] in response

---

#### ✅ PASS — `b219_itinerary_start_time`
_Session b219ab9d follow-up: After generating itinerary, user asks to change start time to 11 AM. Should regenerate with modification_notes, not stall._

_Total time: 58.5s · 3 turn(s)_

**Turn 1** [✓ 16.9s]
> **User:** Plan a 5-day trip to London starting next week, I want to start my day at 10 am
> **Bot:** I’ve got **2026-05-25 to 2026-05-31** for next week, but that’s a **7-day** window — you asked for a **5-day** trip. If you want, I can adjust it to a 5-day plan and then build your itinerary.

Also noted: you want to **start your day at 10 am**.
> _meta:_ type=`message` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'message'] got=message
> - ✅ **max_time**: 16859ms <= 45000ms
> - ✅ **contains_any**: any of ['2026', 'does that work', 'sound right', 'confirm', 'London', 'itinerary', 'plan'] in response

**Turn 2** [✓ 21.3s]
> **User:** yes
> **Bot:** Here's your 5-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'message'] got=itinerary_results
> - ✅ **max_time**: 21266ms <= 60000ms
> - ✅ **contains_any**: any of ['itinerary', 'London', 'plan', 'ready', 'booking', 'change', 'Glad'] in response

**Turn 3** [✓ 20.4s]
> **User:** can you help me amend my itinerary and let me start my day at 11 am instead
> **Bot:** Here's your 5-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you're ready!
> _meta:_ type=`itinerary_results` · intent=`create_itinerary`
>
> Assertions:
> - ✅ **type_in**: expected in ['itinerary_results', 'message'] got=itinerary_results
> - ✅ **max_time**: 20406ms <= 60000ms
> - ✅ **contains_any**: any of ['11', 'updated', 'adjusted', 'itinerary', 'change', 'start', 'update'] in response

---

## Themes & Observations

_(Add after reviewing the per-scenario detail. Common patterns to look for:_
_- Search/itinerary tools fired vs not_
_- Capability disclosure intercepts that shouldn't fire_
_- Date-parsing or destination-resolution failures_
_- Re-asking for fields already in shared_context_
_- Latency outliers)_
