# GTM Tracking Plan - Voya

> **GTM Container**: `GTM-WPWMQB9B`
> **Environments**: Production (`*.myvoya.ai`) and Staging only
> **Last Updated**: 2026-05-02

## Overview

This document defines the `dataLayer` events to track across the Voya platform: **User lifecycle** (auth, chat engagement) and two **booking funnels** (Flights, Hotels). The booking funnels start in the **Chatbot** and continue in standalone **Booker** pages inside the React app (`frontend-v2`).

### Pages with GTM

| Surface | URL pattern | Files (post-frontend-v2 cutover) |
|---|---|---|
| Landing / Auth | `/`, `/home` | `frontend-v2/src/features/landing/`, `frontend-v2/src/features/auth/` |
| Chat | `/chat`, `/public/chat` | `frontend-v2/src/features/chat/` |
| Flight booking flow | `/flights/search`, `/flights/recommendations`, `/flights/details/:id`, `/flights/passenger-info`, `/flights/review`, `/flights/payment/:ref`, `/flights/confirmation`, `/flights/bookings/:ref` | `frontend-v2/src/features/flights/pages/` |
| Hotel booking flow | `/hotels/search`, `/hotels/recommendations`, `/hotels/details/:id`, `/hotels/review`, `/hotels/payment/:ref`, `/hotels/confirmation` | `frontend-v2/src/features/hotels/pages/` |
| Legacy dev booker (internal) | `/dev/flight-booker/`, `/dev/hotel-booker/` | `backend_python/dev_ui/flight-booker/index.html`, `backend_python/dev_ui/hotel-booker/index.html` |

> **Note**: the `backend_python/dev_ui/*` pages are **internal developer consoles**, not the user-facing booking flow. A few events in this doc still reference them — see [Drift notes](#drift-notes) at the bottom for which events fire where today.

---

## Event Naming Convention

```
{domain}_{action}
```

- Domain: `user`, `chat`, `flight`, `hotel`
- Action: verb describing what happened

All events include a common context block (see [Common Properties](#common-properties)).

---

## Common Properties

Included with **every** event:

| Property | Type | Description |
|----------|------|-------------|
| `event` | string | Event name |

Booking funnel events additionally include:

| Property | Type | Description |
|----------|------|-------------|
| `source` | string | `"chat"` or `"booker"` |
| `search_session_id` | string | Search session ID (links chat to booker) |

---

## User Lifecycle Events

### 1. `user_login`

**Trigger**: Successful login (email/password or Google OAuth)
**Files**: `frontend-v2/src/features/auth/components/AuthModal.tsx`, `GoogleAuthButton.tsx`

| Property | Type | Example |
|----------|------|---------|
| `method` | string | `"email"` or `"google"` |
| `email` | string | `"user@example.com"` (for AC Site Tracking identification) |

---

### 2. `user_login_failed`

**Trigger**: Login attempt fails (wrong password, account not found)
**Files**: `frontend-v2/src/features/auth/components/AuthModal.tsx`, `GoogleAuthButton.tsx`

| Property | Type | Example |
|----------|------|---------|
| `method` | string | `"email"` or `"google"` |
| `error` | string | `"Invalid credentials"` |
| `email` | string | `"user@example.com"` (email method only; for AC Site Tracking identification) |

---

### 3. `user_registered`

**Trigger**: Registration succeeded. For email: form submitted and verification email sent. For google: OAuth signup completed.
**Files**: `frontend-v2/src/features/auth/components/AuthModal.tsx`, `GoogleAuthButton.tsx`

| Property | Type | Example |
|----------|------|---------|
| `method` | string | `"email"` or `"google"` |
| `email` | string | `"user@example.com"` (for AC Site Tracking identification) |

---

### 4. `user_registration_completed`

**Trigger**: Registration fully completed. For email: user clicks activation link and sets password. For google: OAuth signup completed (fires immediately after `user_registered` in the same tick).
**Files**: `frontend-v2/src/features/auth/components/CompleteRegistrationPage.tsx`, `GoogleAuthButton.tsx`

| Property | Type | Example |
|----------|------|---------|
| `method` | string | `"email"` or `"google"` |
| `email` | string | `"user@example.com"` (for AC Site Tracking identification) |

---

### 5. `user_password_reset_requested`

**Trigger**: User submits forgot-password form
**File**: `frontend-v2/src/features/auth/components/ForgotPasswordPage.tsx`

*(No additional properties)*

---

## Chat Engagement Events

### 1. `chat_opened`

**Trigger**: User opens the chat widget
**File**: `frontend-v2/src/features/chat/context/ChatContext.tsx`

| Property | Type | Example |
|----------|------|---------|
| `is_authenticated` | boolean | `true` |

---

### 2. `chat_message_sent`

**Trigger**: User sends a message in chat
**File**: `frontend-v2/src/features/chat/utils/applySuccessfulChatResponse.ts`

| Property | Type | Example |
|----------|------|---------|
| `chat_id` | string\|null | `"abc123"` (null for first message) |
| `is_authenticated` | boolean | `true` |
| `message_length` | number | `42` |
| `user_message_index` | number | `3` (1-based ordinal of user messages in this chat session) |

---

### 3. `chat_bot_response_received`

**Trigger**: Bot response rendered (after each user message)
**File**: `frontend-v2/src/features/chat/utils/applySuccessfulChatResponse.ts`

| Property | Type | Example |
|----------|------|---------|
| `chat_id` | string | `"abc123"` |
| `intent_name` | string | `"BOOK_FLIGHT"`, `"BOOK_HOTEL"`, `"PLAN_TRIP"`, etc. |
| `message_type` | string | `"message"`, `"flight_search_results"`, `"hotel_search_results"` |
| `response_length` | number | `256` |

---

### 4. `chat_suggestion_clicked`

**Trigger**: User clicks a suggested action chip in the chat
**Files**: `frontend-v2/src/features/chat/components/ChatBot.tsx`, `ChatPanel.tsx`

| Property | Type | Example |
|----------|------|---------|
| `suggestion_title` | string | `"Book a Flight"` |
| `chat_id` | string | `"abc123"` |

---

### 5. `chat_feedback_submitted`

**Trigger**: User gives thumbs up/down on a bot response
**File**: `frontend-v2/src/features/chat/components/flights/FeedbackButtons.tsx`

| Property | Type | Example |
|----------|------|---------|
| `feedback_type` | string | `"thumbs_up"` or `"thumbs_down"` |
| `chat_id` | string | `"abc123"` |
| `message_id` | string | `"msg_456"` |

---

### 6. `chat_see_full_results_clicked`

**Trigger**: User clicks "See Full Results" button on flight or hotel results in chat
**Files**: `frontend-v2/src/features/flights/components/FlightSearchResultsPanel.tsx`, `MulticityRecommendationsPanel.tsx`, `frontend-v2/src/features/hotels/components/HotelSearchResultsPanel.tsx`

| Property | Type | Example |
|----------|------|---------|
| `result_type` | string | `"flight"` or `"hotel"` |
| `search_session_id` | string | `"fl_session_xyz"` |

---

## Flight Funnel

### 1. `flight_search_results_shown`

**Trigger**: Flight results rendered (chat panel or dedicated recommendations route)
**Source**: `chat`
**Files**: `frontend-v2/src/features/flights/components/FlightSearchResultsPanel.tsx`, `frontend-v2/src/features/flights/components/MulticityRecommendationsPanel.tsx`

| Property | Type | Source | Example |
|----------|------|--------|---------|
| `origin` | string | `search_params.origin` | `"AMS"` |
| `origin_city` | string | `search_params.origin_city` | `"Amsterdam"` |
| `destination` | string | `search_params.destination` | `"BOS"` |
| `destination_city` | string | `search_params.destination_city` | `"Boston"` |
| `departure_date` | string | `search_params.departure_date` | `"2026-03-15"` |
| `return_date` | string\|null | `search_params.return_date` | `"2026-03-22"` |
| `journey_type` | string | `search_params.journey_type` | `"Return"` |
| `adults` | number | `search_params.passengers.adults` | `2` |
| `children` | number | `search_params.passengers.children` | `0` |
| `infants` | number | `search_params.passengers.infants` | `0` |
| `cabin_class` | string | `search_params.cabin_class` | `"Economy"` |
| `total_results` | number | `data.summary.total_flights` | `42` |
| `direct_count` | number | `data.summary.direct_count` | `8` |
| `price_min` | number | `data.summary.price_range.min` | `289.00` |
| `price_max` | number | `data.summary.price_range.max` | `1420.00` |
| `currency` | string | `data.summary.price_range.currency` | `"EUR"` |

---

### 2. `flight_search_initiated`

**Trigger**: User clicks "Search" on the flight booker page
**Source**: `booker`
**File**: `backend_python/dev_ui/flight-booker/index.html` *(legacy dev console only — not yet ported to frontend-v2; see [Drift notes](#drift-notes))*

| Property | Type | Example |
|----------|------|---------|
| `origin` | string | `"AMS"` |
| `destination` | string | `"BOS"` |
| `departure_date` | string | `"2026-03-15"` |
| `return_date` | string\|null | `"2026-03-22"` |
| `adults` | number | `1` |
| `children` | number | `0` |
| `infants` | number | `0` |
| `cabin` | string | `"ECONOMY"` |

---

### 3. `flight_results_displayed`

**Trigger**: Search results loaded and rendered on flight booker page (step: `select`)
**Source**: `booker`
**File**: `backend_python/dev_ui/flight-booker/index.html` *(legacy dev console only — see [Drift notes](#drift-notes))*

| Property | Type | Example |
|----------|------|---------|
| `origin` | string | `"AMS"` |
| `destination` | string | `"BOS"` |
| `total_results` | number | `42` |
| `has_direct` | boolean | `true` |
| `price_min` | number | `289.00` |
| `currency` | string | `"EUR"` |

---

### 4. `flight_selected`

**Trigger**: Mounts on the flight details / fare-rules step (one-way / round-trip and per-leg multicity)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/FlightDetailsPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `fare_source_code` | string | `"ABC123XYZ"` |
| `price` | number | `345.00` |
| `currency` | string | `"EUR"` |
| `stops` | number | `0` |
| `airline` | string | `"KLM"` |
| `duration_minutes` | number | `630` |
| `journey_type` | string | `"Return"` |

---

### 5. `flight_fare_validated`

**Trigger**: Fare validation API returns (step: `rules`)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/FlightDetailsPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `validated` | boolean | `true` |
| `price_changed` | boolean | `false` |
| `updated_price` | number | `345.00` |
| `currency` | string | `"EUR"` |
| `requires_passport` | boolean | `true` |

---

### 6. `flight_fare_rules_accepted`

**Trigger**: User clicks "Accept & Continue" after reviewing fare rules
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/FlightDetailsPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `fare_source_code` | string | `"ABC123XYZ"` |
| `requires_passport` | boolean | `true` |

---

### 7. `flight_passenger_details_completed`

**Trigger**: User completes passenger form and clicks "Continue to Booking" (step: `passenger` -> `review`)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/PassengerInfoPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `passenger_count` | number | `2` |
| `adults` | number | `2` |
| `children` | number | `0` |
| `infants` | number | `0` |
| `has_passport` | boolean | `true` |

---

### 8. `flight_booking_review_shown`

**Trigger**: Review step rendered (step: `review`)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/ReviewBookingPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `total_price` | number | `690.00` |
| `currency` | string | `"EUR"` |
| `passenger_count` | number | `2` |
| `journey_type` | string | `"Return"` |

---

### 9. `flight_payment_initiated`

**Trigger**: Revolut order created (step: `payment`) — historically Stripe, now Revolut
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/PaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `amount` | number | `690.00` |
| `currency` | string | `"EUR"` |

---

### 10. `flight_payment_completed`

**Trigger**: Revolut payment confirms (was `stripe.confirmCardPayment()` historically)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/PaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `payment_intent_id` | string | `"pi_xxxxx"` |
| `amount` | number | `690.00` |
| `currency` | string | `"EUR"` |

---

### 11. `flight_payment_failed`

**Trigger**: Revolut payment fails (was `stripe.confirmCardPayment()` historically)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/PaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `error_code` | string | `"card_declined"` |
| `error_message` | string | `"Your card was declined."` |

---

### 12. `flight_booking_confirmed`

**Trigger**: Booking API returns success, confirmation screen shown (step: `confirmation`)
**Source**: `booker`
**File**: `frontend-v2/src/features/flights/pages/PaymentPage.tsx` *(fires after the payment-completed event in the same handler chain)*

| Property | Type | Example |
|----------|------|---------|
| `voya_booking_reference` | string | `"VOYA-2026-001234"` |
| `booking_type` | string | `"GDS"` or `"LCC"` |
| `total_price` | number | `690.00` |
| `currency` | string | `"EUR"` |
| `passenger_count` | number | `2` |
| `journey_type` | string | `"Return"` |

---

## Hotel Funnel

### 1. `hotel_search_results_shown`

**Trigger**: Hotel results rendered (chat panel `HotelResultMessage` or recommendations route panel)
**Source**: `chat`
**Files**: `frontend-v2/src/features/chat/components/hotels/HotelResultMessage.tsx`, `frontend-v2/src/features/hotels/components/HotelSearchResultsPanel.tsx`

| Property | Type | Source | Example |
|----------|------|--------|---------|
| `destination_city` | string | `search_params.destination_city` | `"Barcelona"` |
| `country` | string\|null | `search_params.country` | `"Spain"` |
| `check_in_date` | string | `search_params.check_in_date` | `"2026-03-15"` |
| `check_out_date` | string | `search_params.check_out_date` | `"2026-03-18"` |
| `rooms` | number | `search_params.rooms` | `1` |
| `adults` | number | `search_params.adults` | `2` |
| `children` | number | `search_params.children` | `0` |

---

### 2. `hotel_search_initiated`

**Trigger**: User clicks "Search Hotels" on hotel booker page
**Source**: `booker`
**File**: `backend_python/dev_ui/hotel-booker/index.html` *(legacy dev console only — not yet ported to frontend-v2; see [Drift notes](#drift-notes))*

| Property | Type | Example |
|----------|------|---------|
| `destination_city` | string | `"Barcelona"` |
| `country` | string | `"Spain"` |
| `check_in_date` | string | `"2026-03-15"` |
| `check_out_date` | string | `"2026-03-18"` |
| `rooms` | number | `1` |
| `adults` | number | `2` |
| `children` | number | `0` |

---

### 3. `hotel_results_displayed`

**Trigger**: Search results loaded and rendered on hotel booker page (step: `results`)
**Source**: `booker`
**File**: `backend_python/dev_ui/hotel-booker/index.html` *(legacy dev console only — see [Drift notes](#drift-notes))*

| Property | Type | Example |
|----------|------|---------|
| `destination_city` | string | `"Barcelona"` |
| `total_results` | number | `35` |
| `price_min` | number | `89.00` |
| `currency` | string | `"EUR"` |

---

### 4. `hotel_selected`

**Trigger**: User clicks on a hotel card, triggering room rates fetch
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelDetailPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `hotel_name` | string | `"Hotel Barcelona"` |
| `hotel_rating` | number | `4.5` |
| `property_type` | string | `"Hotel"` |
| `price` | number | `150.00` |
| `currency` | string | `"EUR"` |

---

### 5. `hotel_room_selected`

**Trigger**: User selects a room and rate-rules validation succeeds (step: `rooms` -> `guest`)
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelDetailPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `hotel_name` | string | `"Hotel Barcelona"` |
| `room_type` | string | `"Deluxe Room"` |
| `total_price` | number | `450.00` |
| `price_per_night` | number | `150.00` |
| `currency` | string | `"EUR"` |
| `is_refundable` | boolean | `true` |

---

### 6. `hotel_guest_details_completed`

**Trigger**: User completes guest details form and clicks "Continue to Review"
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelReviewBookingPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `guest_count` | number | `2` |
| `has_children` | boolean | `false` |
| `has_special_requests` | boolean | `true` |

---

### 7. `hotel_booking_review_shown`

**Trigger**: Review step rendered (step: `review`)
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelReviewBookingPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `hotel_name` | string | `"Hotel Barcelona"` |
| `total_price` | number | `472.50` |
| `platform_fee` | number | `47.25` |
| `currency` | string | `"EUR"` |
| `nights` | number | `3` |
| `rooms` | number | `1` |

---

### 8. `hotel_payment_initiated`

**Trigger**: Revolut order created (step: `payment`) — historically Stripe, now Revolut
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelPaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `amount` | number | `472.50` |
| `currency` | string | `"EUR"` |

---

### 9. `hotel_payment_completed`

**Trigger**: Revolut payment confirms (was `stripe.confirmCardPayment()` historically)
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelPaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `payment_intent_id` | string | `"pi_xxxxx"` |
| `amount` | number | `472.50` |
| `currency` | string | `"EUR"` |

---

### 10. `hotel_payment_failed`

**Trigger**: Revolut payment fails (was `stripe.confirmCardPayment()` historically)
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelPaymentPage.tsx`

| Property | Type | Example |
|----------|------|---------|
| `error_code` | string | `"card_declined"` |
| `error_message` | string | `"Your card was declined."` |

---

### 11. `hotel_booking_confirmed`

**Trigger**: Booking API returns success, confirmation screen shown (step: `confirmation`)
**Source**: `booker`
**File**: `frontend-v2/src/features/hotels/pages/HotelPaymentPage.tsx` *(fires after the payment-completed event in the same handler chain)*

| Property | Type | Example |
|----------|------|---------|
| `voya_booking_reference` | string | `"VOYA-HOTEL-20260215..."` |
| `supplier_confirmation` | string | `"FL-CONFIRM-123"` |
| `hotel_name` | string | `"Hotel Barcelona"` |
| `total_price` | number | `472.50` |
| `currency` | string | `"EUR"` |
| `nights` | number | `3` |
| `rooms` | number | `1` |

---

### 12. `hotel_booking_cancelled`

**Trigger**: User completes cancellation flow (step: `cancellation`)
**Source**: `booker`
**File**: `backend_python/dev_ui/hotel-booker/index.html` *(legacy dev console only — no cancellation route in frontend-v2 yet; see [Drift notes](#drift-notes))*

| Property | Type | Example |
|----------|------|---------|
| `voya_booking_reference` | string | `"VOYA-HOTEL-20260215..."` |

---

## Funnel Visualisation

### Full User Journey

```
LANDING                        CHAT                           BOOKER
(homepage)                     (widget)                       (standalone page)

user_login  (returning users; also fires on new Google signups)
user_registered  (new users only)
  user_registration_completed  (new users only)
        |
        NOTE: Email signup splits across two moments:
          - user_registered fires on form submit (verification email sent)
          - user_registration_completed fires when user clicks activation link
        Google signup fires user_login + user_registered + user_registration_completed
          all in the same tick (no verification step).
        |
   chat_opened
        |
   chat_message_sent ───> chat_bot_response_received
        |                         |
   chat_suggestion_clicked        |  (intent: BOOK_FLIGHT or BOOK_HOTEL)
        |                         |
   chat_feedback_submitted        v
                           flight/hotel_search_results_shown
                                  |
                           chat_see_full_results_clicked
                                  |
                                  +──────────────────────> FLIGHT or HOTEL BOOKER
```

### Flight Booking Funnel

```
CHAT                           FLIGHT BOOKER

1. flight_search_results_shown
        |
        |  "See Full Results"
        v
                         2.  flight_search_initiated (if new search)
                         3.  flight_results_displayed
                               |
                         4.  flight_selected
                               |
                         5.  flight_fare_validated
                               |
                         6.  flight_fare_rules_accepted
                               |
                         7.  flight_passenger_details_completed
                               |
                         8.  flight_booking_review_shown
                               |
                         9.  flight_payment_initiated
                               |
                        10.  flight_payment_completed  /  11. flight_payment_failed
                               |
                        12.  flight_booking_confirmed
```

### Hotel Booking Funnel

```
CHAT                           HOTEL BOOKER

1. hotel_search_results_shown
        |
        |  "See Full Results"
        v
                         2.  hotel_search_initiated (if new search)
                         3.  hotel_results_displayed
                               |
                         4.  hotel_selected
                               |
                         5.  hotel_room_selected
                               |
                         6.  hotel_guest_details_completed
                               |
                         7.  hotel_booking_review_shown
                               |
                         8.  hotel_payment_initiated
                               |
                         9.  hotel_payment_completed  /  10. hotel_payment_failed
                               |
                        11.  hotel_booking_confirmed
                               |
                        12.  hotel_booking_cancelled (optional)
```

---

## Implementation Notes

### GTM Guard

GTM only loads on `*.myvoya.ai`. All `dataLayer.push()` calls should be guarded:

```javascript
if (window.dataLayer) {
  window.dataLayer.push({ event: '...', ... });
}
```

### Session Linking

The `search_session_id` is the key to link chat events to booker events. For flights it's the FlightLogic session ID; for hotels it's an internal Voya UUID. It's stored in `localStorage`/`sessionStorage` when the user clicks "See Full Results" and reused by the booker.

### Implementation Locations

| Event Category | Files |
|----------------|-------|
| Login / Register | `frontend-v2/src/features/auth/components/AuthModal.tsx`, `GoogleAuthButton.tsx`, `CompleteRegistrationPage.tsx` |
| Password reset | `frontend-v2/src/features/auth/components/ForgotPasswordPage.tsx` |
| Chat open | `frontend-v2/src/features/chat/context/ChatContext.tsx` |
| Chat messages | `frontend-v2/src/features/chat/utils/applySuccessfulChatResponse.ts` |
| Chat suggestions | `frontend-v2/src/features/chat/components/ChatBot.tsx`, `ChatPanel.tsx` |
| Chat feedback | `frontend-v2/src/features/chat/components/flights/FeedbackButtons.tsx` |
| Chat → flight handoff (`see_full_results`) | `frontend-v2/src/features/flights/components/FlightSearchResultsPanel.tsx`, `MulticityRecommendationsPanel.tsx` |
| Chat → hotel handoff (`see_full_results`) | `frontend-v2/src/features/hotels/components/HotelSearchResultsPanel.tsx` |
| Flight booker (selected → confirmed) | `frontend-v2/src/features/flights/pages/FlightDetailsPage.tsx`, `PassengerInfoPage.tsx`, `ReviewBookingPage.tsx`, `PaymentPage.tsx` |
| Hotel booker (selected → confirmed) | `frontend-v2/src/features/hotels/pages/HotelDetailPage.tsx`, `HotelReviewBookingPage.tsx`, `HotelPaymentPage.tsx` |
| Legacy dev consoles (still wired) | `backend_python/dev_ui/flight-booker/index.html`, `backend_python/dev_ui/hotel-booker/index.html` |

### Sensitive Data

Do **not** push to `dataLayer`:
- Passenger names, phone numbers
- Passport numbers
- Card details (handled entirely by the payment provider)
- User IDs or auth tokens

**Exception (added 2026-04-08):** `email` may be pushed on `user_login`, `user_registered`, `user_registration_completed`, and `user_login_failed` events ONLY. This is required for ActiveCampaign Site Tracking to identify visitors via `vgo('setEmail', ...)`. Tags consuming the `DLV - email` variable must be explicitly audited; no third-party destination (Meta Pixel, Reddit Pixel, GA4) should be configured to ingest dataLayer fields automatically.

### Testing

- On localhost, `window.dataLayer` won't exist (GTM not loaded)
- For local testing, add `window.dataLayer = window.dataLayer || [];` before GTM snippet
- Use GTM Preview mode on staging to verify events fire correctly

---

## Drift notes

The booking funnel originally lived in the `backend_python/dev_ui/*-booker` HTML pages. Most of it has since moved to the React `frontend-v2/src/features/*/pages/` flow. As of 2026-05-02 the spec and implementation have drifted in two directions (5 missing + 8 unlisted):

### Documented but not firing in `frontend-v2`

These events are listed in this doc but are **not currently emitted** by the user-facing React app. They still fire in the legacy `dev_ui` consoles (kept for internal/dev use):

| Event | Where it would fire in frontend-v2 (if added) |
|---|---|
| `flight_search_initiated` | `FlightSearchPage.tsx` on submit |
| `flight_results_displayed` | `FlightResults.tsx` / `FlightSearchResultsPanel.tsx` mount with results |
| `hotel_search_initiated` | `HotelSearchPage.tsx` on submit |
| `hotel_results_displayed` | `HotelSearchResultsPanel.tsx` mount with results |
| `hotel_booking_cancelled` | no cancellation flow in v2 yet |

### Firing in `frontend-v2` but not (yet) documented

These events ARE pushed to `dataLayer` from the React app but are not specified in this doc. They should either be added to this spec or audited and removed.

| Event | Where it fires |
|---|---|
| `chat_view_flights_clicked` | `frontend-v2/src/features/chat/` (chat → flight CTA) |
| `chat_view_hotels_clicked` | `frontend-v2/src/features/chat/` (chat → hotel CTA) |
| `chat_view_itinerary_clicked` | `frontend-v2/src/features/chat/` (chat → itinerary CTA) |
| `chat_rich_result_auto_navigate` | `frontend-v2/src/features/chat/` (auto-redirect after a chat result) |
| `itinerary_results_shown` | `frontend-v2/src/features/chat/` (ItineraryResultMessage / itinerary panel) |
| `multicity_booking_partial_after_payment` | `frontend-v2/src/features/flights/pages/PaymentPage.tsx` (multicity edge case) |
| `public_chat_itinerary_auto_saved` | public-chat post-auth conversion path |
| `public_chat_post_auth_conversion` | public-chat post-auth conversion path |

### Action items

1. Decide which "documented but not firing" events should be added to `frontend-v2` (or removed from this spec).
2. For the "firing but undocumented" set, either add a section per event with property contracts, or remove the calls.
3. After resolving (1) and (2), update the funnel diagrams above so they reflect the actual user journey on `*.myvoya.ai`.
