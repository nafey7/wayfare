# CREATE_ITINERARY Agent - Complete Implementation Guide

**Document Version**: 1.0
**Date**: November 2025
**Status**: Production Ready - Intent Persistence Implemented


---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement & Solution](#problem-statement--solution)
3. [System Architecture](#system-architecture)
4. [Workflow Stages Deep Dive](#workflow-stages-deep-dive)
5. [MongoDB Schema & Setup](#mongodb-schema--setup)
6. [Backend Integration](#backend-integration)
7. [Intent Persistence System](#intent-persistence-system)
8. [APIs & External Services](#apis--external-services)
9. [Production Deployment](#production-deployment)
10. [Future Integrations](#future-integrations)
11. [Testing & Monitoring](#testing--monitoring)

---

## Executive Summary

The **CREATE_ITINERARY Agent** is an AI-powered itinerary planning system built with n8n, integrated with the Voya Travel Platform backend. It guides users through a multi-stage conversation to plan complete trips, from destination selection to flight booking.

**Key Features:**
- ✅ Multi-stage conversation flow (5 stages)
- ✅ Session persistence in MongoDB
- ✅ Intent persistence across messages
- ✅ Flight availability check (FlightLogic API)
- ✅ Budget estimation
- ✅ Booking handoff with passenger data collection
- ✅ Context-aware AI responses (Gemini 2.0)

**Technology Stack:**
- **n8n**: Workflow automation (local: http://localhost:5678, cloud: https://voya-itinerary.app.n8n.cloud)
- **MongoDB**: Session & conversation storage (database: `n8n_voya_dev`)
- **Gemini AI**: Natural language understanding
- **FlightLogic API**: Flight search & booking
- **Voya Backend**: FastAPI Python application

---

## Problem Statement & Solution

### The Problem

**Before Implementation:**
```
User: "I want to plan a trip to Japan"
Bot: "Great! When do you want to travel?"  [Intent: CREATE_ITINERARY ✅]

User: "In March"
Bot: "I can help you search for hotels..."  [Intent: GENERAL_QUERY ❌ - Lost!]
```

**Root Causes:**
1. n8n wasn't returning the `intent` field in responses
2. Backend ran Intent Recognizer on every message (unreliable for short inputs)
3. No mechanism to maintain intent across conversation turns
4. Pattern matching returned confidence 0.6, but sticky intent required 0.9+

### The Solution

**Three-Part Fix:**

#### 1. n8n Workflow Modification
```json
// BEFORE (Response Generator node)
{
  "respondWith": "json",
  "responseBody": "={{ { \"message\": $json.message } }}"
}

// AFTER
{
  "respondWith": "firstEntryJson"  // Returns full object with intent, stage, session_id
}
```

#### 2. Backend Intent Capture
```python
# Capture intent from n8n response
response_intent = n8n_response.get("intent", "CREATE_ITINERARY")

# Store it in MongoDB
await repository.create_message(
    content={"text": response["message"]},
    intent_name=response_intent.lower(),  # Use n8n's intent
    ...
)
```

#### 3. Last Message Intent Check
```python
# Check last message before running Intent Recognizer
last_messages = await repository.get_chat_messages(chat_id, limit=1)

if last_messages and last_messages[0].intent_name == "create_itinerary":
    if last_stage != "completed":
        # SKIP Intent Recognizer, route directly to n8n ✅
        response = await self._route_to_itinerary_agent(...)
```

**Result:**
```
User: "I want to plan a trip to Japan"
Bot: "Great! When do you want to travel?"  [Intent: CREATE_ITINERARY ✅]

User: "In March"
Bot: "Perfect! March is beautiful in Japan..."  [Intent: CREATE_ITINERARY ✅ Maintained!]
```

---

## System Architecture

### Component Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                          VOYA TRAVEL PLATFORM                          │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌────────────┐
│   Frontend  │ HTTP │   Backend   │ HTTP │     n8n     │ HTTP │  Gemini AI │
│   (React)   │─────▶│  (FastAPI)  │─────▶│  Workflow   │─────▶│    API     │
│  :3000      │      │   :8000     │      │   :5678     │      │            │
└─────────────┘      └─────────────┘      └─────────────┘      └────────────┘
       │                    │                     │
       │                    │                     │
       │                    ▼                     ▼
       │            ┌─────────────┐      ┌─────────────┐
       │            │ FlightLogic │      │   MongoDB   │
       │            │     API     │      │   :27017    │
       │            │   :8002     │      │             │
       │            └─────────────┘      └─────────────┘
       │                                         │
       └─────────────────────────────────────────┘
           (Authentication & Chat History)


┌─────────────────────────────────────────────────────────────────────┐
│                       DATA FLOW - Message Lifecycle                  │
└─────────────────────────────────────────────────────────────────────┘

1. User sends message via Frontend
   ↓
2. Backend: Check last message intent (MongoDB)
   ├─ If last = "create_itinerary" & stage != "completed"
   │  └─ SKIP Intent Recognizer, go to step 3
   └─ Else: Run Intent Recognizer
   ↓
3. Backend → n8n webhook: POST /webhook/itinerary-agent
   Payload: {user_id, chat_id, message, session_id}
   ↓
4. n8n Workflow:
   a. Load session from MongoDB (itinerary_sessions collection)
   b. Extract data from message (dates, destination, etc.)
   c. Check stage requirements & advance if ready
   d. [Stage-specific processing: flights, hotels, budget]
   e. Build context-aware prompt with conversation history
   f. Call Gemini AI API
   g. Process AI response
   h. Update session in MongoDB
   i. Prepare response with intent & stage
   ↓
5. n8n → Backend response:
   {
     "message": "...",
     "intent": "CREATE_ITINERARY",
     "stage": "initial_vision",
     "session_id": "session_xxx",
     "type": "itinerary_response"
   }
   ↓
6. Backend: Store bot message in MongoDB with intent from n8n
   ↓
7. Backend → Frontend: Display message to user
```

### Services & Ports

| Service | Local URL | Cloud URL (Production) | Purpose |
|---------|-----------|----------------------|---------|
| **Frontend** | http://localhost:3000 | https://app.voya.com | User interface |
| **Backend** | http://localhost:8000 | https://api.voya.com | REST API |
| **n8n Webhook** | http://localhost:5678/webhook/itinerary-agent | https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent | Workflow automation |
| **MongoDB** | mongodb://localhost:27017 | mongodb+srv://cluster.mongodb.net | Database |
| **FlightLogic** | http://localhost:8002 (mock) | https://api.flightlogic.com | Flight data |
| **Gemini AI** | - | https://generativelanguage.googleapis.com | Natural language AI |

---

## Workflow Stages Deep Dive

The CREATE_ITINERARY agent follows a **5-stage progressive conversation flow**. Each stage has specific requirements and objectives.

### Stage 1: Initial Vision
**Goal**: Gather destination and origin

**Required Fields**:
- `destination` (where user wants to go)
- `origin` (where user departs from)

**Optional Fields**:
- `departure_date`
- `adults` (number of travelers)

**What Happens**:
1. User expresses desire to plan a trip
2. Gemini asks clarifying questions about destination and origin
3. Data extraction identifies cities/airports mentioned
4. Stores in `collected_data.destination` and `collected_data.origin`

**Example Conversation**:
```
User: "I want to plan a trip to Japan"
Bot: "Japan sounds amazing! Where will you be departing from?"

User: "From New York"
Bot: "Perfect! When are you planning to travel to Japan?"
```

**MongoDB After Stage 1**:
```json
{
  "session_id": "session_user123_1234567890",
  "stage": "initial_vision",
  "collected_data": {
    "destination": "Tokyo, Japan",
    "origin": "New York, USA"
  },
  "conversation_history": [
    {"role": "user", "content": "I want to plan a trip to Japan", "timestamp": "..."},
    {"role": "assistant", "content": "Japan sounds amazing...", "timestamp": "..."}
  ]
}
```

**Advancement Condition**: Has `destination` AND `origin` → Advance to **route_refinement**

---

### Stage 2: Route Refinement
**Goal**: Confirm travel dates and refine itinerary details

**Required Fields**:
- `departure_date` (YYYY-MM-DD format)

**Optional Fields**:
- `return_date`
- `interests` (array of activities/themes)

**What Happens**:
1. Confirms departure date if not yet captured
2. Asks about return date (if round trip)
3. Discusses interests (temples, food, nature, etc.)
4. Refines destination specifics (cities, regions)

**Example Conversation**:
```
User: "In March, for about 2 weeks"
Bot: "March is perfect! Spring season in Japan. Are you interested in temples, food experiences, or nature?"

User: "Temples and authentic food"
Bot: "Excellent! I'll plan temple visits and local cuisine experiences. Let me check flight availability..."
```

**MongoDB After Stage 2**:
```json
{
  "stage": "route_refinement",
  "collected_data": {
    "destination": "Tokyo, Japan",
    "origin": "New York, USA",
    "departure_date": "2026-03-15",
    "return_date": "2026-03-29",
    "interests": ["temples", "authentic food"],
    "adults": 1
  }
}
```

**Advancement Condition**: Has `departure_date` → Advance to **availability_check**

---

### Stage 3: Availability Check
**Goal**: Search for flights, hotels, and weather data

**Required Fields**:
- `destination`
- `origin`
- `departure_date`
- `return_date`

**External API Calls**:
1. **FlightLogic Flight Search** → `flight_availability`
2. **FlightLogic Hotel Search** → `hotel_availability` (if implemented)
3. **Weather API** → `weather_data` (if implemented)

**What Happens**:
1. Calls FlightLogic API with route and dates
2. Receives 3 curated flight options:
   - Lowest Price 💵
   - Fastest ⚡
   - Best Value ⭐
3. Presents options to user with prices, airlines, stops
4. Stores availability data in session

**Example Conversation**:
```
Bot: "Great news! I found 3 flight options for New York → Tokyo (March 15 - March 29):

💵 Lowest Price: United Airlines - $650 (1 stop, 16h 30m)
⚡ Fastest: ANA Direct - $1,200 (nonstop, 14h 0m)
⭐ Best Value: Delta/JAL - $850 (1 stop, 15h 15m)

The weather in Tokyo will be around 15°C (59°F), mostly sunny with occasional rain.

Would you like to proceed with one of these options?"
```

**MongoDB After Stage 3**:
```json
{
  "stage": "availability_check",
  "flight_availability": {
    "status": "available",
    "route": {
      "origin": "JFK",
      "destination": "NRT",
      "departure_date": "2026-03-15",
      "return_date": "2026-03-29"
    },
    "flights": [
      {
        "label": "Lowest Price 💵",
        "airline": "United Airlines",
        "price": {"total": 650, "currency": "USD"},
        "stops": 1,
        "duration_minutes": 990,
        "departure_time": "2026-03-15T08:00:00Z",
        "arrival_time": "2026-03-16T16:30:00+09:00",
        "fare_source_code": "UA_ECONOMY_123"
      },
      // ... 2 more options
    ]
  },
  "weather_data": {
    "forecast": {
      "temperature_avg": 15,
      "temperature_unit": "C",
      "conditions": "mostly sunny",
      "precipitation_chance": 20
    }
  }
}
```

**Advancement Condition**: Has flight availability data → Advance to **budget_estimation**

---

### Stage 4: Budget Estimation
**Goal**: Calculate total trip cost and validate against user budget

**Required Fields**:
- `budget_max` (user's maximum budget)

**Optional Fields**:
- `budget_min`
- `budget_currency`

**What Happens**:
1. Calculates costs:
   - **Flights**: From selected option
   - **Hotels**: Estimated (nights × avg rate)
   - **Daily expenses**: Based on destination ($50-$150/day)
2. Compares total vs user budget
3. Provides breakdown and suggestions if over budget

**Example Conversation**:
```
User: "My budget is around $3000"
Bot: "Let me calculate the total cost for your 14-day trip:

💰 Cost Breakdown:
- Flights (Best Value option): $850
- Hotels (14 nights, mid-range): $1,400 ($100/night)
- Daily expenses (meals, transport, activities): $700 ($50/day)

✅ Total Estimated Cost: $2,950 USD
Your budget: $3,000 USD

Great news! Your trip fits within budget with $50 to spare. Would you like to proceed with booking?"
```

**MongoDB After Stage 4**:
```json
{
  "stage": "budget_estimation",
  "collected_data": {
    // ... previous data ...
    "budget_max": 3000,
    "budget_currency": "USD"
  },
  "budget_data": {
    "flights": {"total": 850, "currency": "USD"},
    "hotels": {"total": 1400, "nights": 14, "rate_per_night": 100, "currency": "USD"},
    "daily_expenses": {"total": 700, "days": 14, "rate_per_day": 50, "currency": "USD"},
    "summary": {
      "total_trip_cost": 2950,
      "user_budget_max": 3000,
      "currency": "USD",
      "status": "within_budget",
      "remaining": 50,
      "message": "Your trip fits within budget!"
    }
  },
  "budget_suggestions": {
    "suggestions": [
      {
        "title": "Cheaper Flight Option",
        "description": "Choose United Airlines ($650) instead",
        "potential_savings": 200
      }
    ]
  }
}
```

**Advancement Condition**: Has budget data and user confirms → Advance to **booking_handoff**

---

### Stage 5: Booking Handoff
**Goal**: Collect passenger details and create booking

**Required Fields**:
- User confirms booking intent ("book option 1", "yes, book it")

**Passenger Data Required** (per traveler):
- `first_name`
- `last_name`
- `email`
- `phone` (with country code)

**What Happens**:
1. User expresses intent to book
2. Gemini asks for passenger information
3. Extracts passenger data from response
4. Calls FlightLogic Booking API
5. Returns booking confirmation with reference number

**Example Conversation**:
```
User: "Yes, book option 2 for me"
Bot: "Great! I'll book the ANA Direct flight ($1,200).

To complete your booking, I need:
- First Name:
- Last Name:
- Email Address:
- Phone Number (e.g., +1 234 567 8900):"

User: "John Doe, john.doe@email.com, +1-555-123-4567"
Bot: "✅ Booking Confirmed!

Your booking reference: VOYA-JD-20250315-ABC123
FlightLogic Booking ID: FL987654321

Flight Details:
- ANA Direct: New York (JFK) → Tokyo (NRT)
- Departure: March 15, 2026 at 08:00 AM
- Arrival: March 16, 2026 at 04:00 PM (+1 day)
- Passenger: John Doe
- Total: $1,200 USD

⚠️ Important: Complete payment within 24 hours to secure this fare.
Ticket issuance deadline: March 15, 2026 at 12:00 PM EST

Confirmation email sent to john.doe@email.com"
```

**MongoDB After Stage 5 (Completed)**:
```json
{
  "stage": "completed",
  "selected_flight_details": {
    "option_number": 2,
    "label": "Fastest ⚡",
    "airline": "ANA",
    "price": {"total": 1200, "currency": "USD"},
    "fare_source_code": "ANA_DIRECT_456"
  },
  "passenger_data": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@email.com",
      "phone": "+1-555-123-4567"
    }
  ],
  "booking_confirmation": {
    "voya_booking_reference": "VOYA-JD-20250315-ABC123",
    "flightlogic_unique_id": "FL987654321",
    "booking_status": "confirmed",
    "payment_status": "pending",
    "ticket_deadline": "2026-03-15T12:00:00Z",
    "booked_flight": {
      "airline": "ANA",
      "departure": "2026-03-15T08:00:00Z",
      "arrival": "2026-03-16T16:00:00+09:00",
      "price_total": 1200
    },
    "confirmation_sent_to": "john.doe@email.com",
    "booking_timestamp": "2026-02-20T10:30:00Z"
  }
}
```

**Stage Exit**: `stage = "completed"` → User can start new conversation

---

### Stage Progression Logic

```javascript
// Defined in "Validate Stage Progression" node

const stageRequirements = {
  'initial_vision': {
    required: ['destination', 'origin'],
    nextStage: 'route_refinement'
  },
  'route_refinement': {
    required: ['departure_date'],
    nextStage: 'availability_check'
  },
  'availability_check': {
    required: ['departure_date', 'return_date'],
    nextStage: 'budget_estimation'
  },
  'budget_estimation': {
    required: ['budget_max'],
    nextStage: 'booking_handoff'
  },
  'booking_handoff': {
    required: [],
    nextStage: 'completed'
  }
};
```

---

## MongoDB Schema & Setup

### Database: `n8n_voya_dev`

Two collections are used:

#### 1. `itinerary_sessions` Collection
Stores complete itinerary planning sessions with all conversation data.

**Schema**:
```javascript
{
  "_id": ObjectId("..."),                  // Auto-generated
  "session_id": String,                    // Unique session identifier
  "user_id": String,                       // Voya user ID
  "chat_id": String,                       // Chat conversation ID
  "stage": String,                         // Current stage (initial_vision, route_refinement, etc.)

  // Conversation history (last 20 messages)
  "conversation_history": [
    {
      "role": String,                      // "user" or "assistant"
      "content": String,                   // Message text
      "timestamp": ISODate                 // When message was sent
    }
  ],

  // Collected travel data
  "collected_data": {
    "destination": String,                 // e.g., "Tokyo, Japan"
    "origin": String,                      // e.g., "New York, USA"
    "departure_date": String,              // YYYY-MM-DD
    "return_date": String,                 // YYYY-MM-DD
    "adults": Number,                      // Number of adult travelers
    "children": Number,                    // Number of children
    "interests": [String],                 // e.g., ["temples", "food"]
    "budget_min": Number,
    "budget_max": Number,
    "budget_currency": String              // e.g., "USD"
  },

  // Flight availability data (from FlightLogic)
  "flight_availability": {
    "status": String,                      // "available" | "unavailable"
    "route": {
      "origin": String,                    // IATA code (e.g., "JFK")
      "destination": String,               // IATA code (e.g., "NRT")
      "departure_date": String,
      "return_date": String
    },
    "flights": [
      {
        "label": String,                   // "Lowest Price 💵"
        "airline": String,
        "price": {
          "total": Number,
          "currency": String
        },
        "stops": Number,
        "duration_minutes": Number,
        "departure_time": ISODate,
        "arrival_time": ISODate,
        "fare_source_code": String         // For booking
      }
    ]
  },

  // Hotel availability (future)
  "hotel_availability": {
    "status": String,
    "hotels_found": Number,
    "price_range": {
      "min": Number,
      "max": Number,
      "currency": String
    }
  },

  // Weather forecast (future)
  "weather_data": {
    "forecast": {
      "temperature_avg": Number,
      "temperature_unit": String,          // "C" or "F"
      "conditions": String,
      "precipitation_chance": Number       // 0-100
    }
  },

  // Budget calculation
  "budget_data": {
    "flights": {"total": Number, "currency": String},
    "hotels": {"total": Number, "nights": Number, "rate_per_night": Number, "currency": String},
    "daily_expenses": {"total": Number, "days": Number, "rate_per_day": Number, "currency": String},
    "summary": {
      "total_trip_cost": Number,
      "user_budget_max": Number,
      "currency": String,
      "status": String,                    // "within_budget" | "over_budget"
      "remaining": Number,
      "message": String
    }
  },

  "budget_suggestions": {
    "suggestions": [
      {
        "title": String,
        "description": String,
        "potential_savings": Number
      }
    ]
  },

  // Stage validation (internal)
  "stage_validation": {
    "current_stage": String,
    "next_stage": String,
    "can_advance": Boolean,
    "missing_fields": [String],
    "collected_fields": [String],
    "required_fields": [String]
  },

  // Selected flight for booking
  "selected_flight_details": {
    "option_number": Number,               // 1, 2, or 3
    "label": String,
    "airline": String,
    "price": Object,
    "fare_source_code": String
  },

  // Passenger information
  "passenger_data": [
    {
      "first_name": String,
      "last_name": String,
      "email": String,
      "phone": String
    }
  ],

  // Booking confirmation
  "booking_confirmation": {
    "voya_booking_reference": String,      // e.g., "VOYA-JD-20250315-ABC123"
    "flightlogic_unique_id": String,       // e.g., "FL987654321"
    "booking_status": String,              // "confirmed" | "pending" | "failed"
    "payment_status": String,              // "pending" | "completed"
    "ticket_deadline": ISODate,
    "booked_flight": Object,
    "confirmation_sent_to": String,        // Email address
    "booking_timestamp": ISODate
  },

  // Timestamps
  "created_at": ISODate,
  "updated_at": ISODate
}
```

#### 2. `n8n_integration_logs` Collection
Stores request/response logs for debugging and monitoring.

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "timestamp": ISODate,
  "direction": String,                     // "incoming" | "outgoing"
  "session_id": String,
  "user_id": String,
  "chat_id": String,
  "message": String,                       // User message or bot response
  "stage": String,
  "intent": String,
  "payload_size": Number,                  // Bytes
  "full_payload": Object                   // Complete request/response data
}
```

---

### MongoDB Setup Scripts

#### **Create Collections & Indexes**

Run this in MongoDB shell (`mongosh n8n_voya_dev`) or Mongo Express:

```javascript
// 1. Create itinerary_sessions collection with unique index on session_id
db.createCollection("itinerary_sessions");
db.itinerary_sessions.createIndex(
  { "session_id": 1 },
  { unique: true, name: "session_id_unique" }
);

// 2. Create additional indexes for queries
db.itinerary_sessions.createIndex(
  { "user_id": 1, "updated_at": -1 },
  { name: "user_sessions_recent" }
);

db.itinerary_sessions.createIndex(
  { "chat_id": 1 },
  { name: "chat_sessions" }
);

db.itinerary_sessions.createIndex(
  { "stage": 1, "updated_at": -1 },
  { name: "stage_tracking" }
);

// 3. Create n8n_integration_logs collection
db.createCollection("n8n_integration_logs");
db.n8n_integration_logs.createIndex(
  { "timestamp": -1 },
  { name: "timestamp_desc" }
);

db.n8n_integration_logs.createIndex(
  { "session_id": 1, "timestamp": -1 },
  { name: "session_logs" }
);

// 4. Verify indexes
db.itinerary_sessions.getIndexes();
db.n8n_integration_logs.getIndexes();
```

#### **PowerShell Script for Production** (Needs to be ckecked)

```powershell
# setup_mongodb_collections.ps1
# Run this to set up MongoDB collections for CREATE_ITINERARY agent

$MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net"
$DATABASE = "n8n_voya_production"

Write-Host "Setting up MongoDB collections for CREATE_ITINERARY agent..." -ForegroundColor Cyan

# Create setup.js file
$setupScript = @"
// Switch to database
use $DATABASE;

// 1. Create itinerary_sessions collection
db.createCollection("itinerary_sessions");
print("✓ Created itinerary_sessions collection");

// 2. Create unique index on session_id (CRITICAL - prevents duplicates)
db.itinerary_sessions.createIndex(
  { "session_id": 1 },
  { unique: true, name: "session_id_unique" }
);
print("✓ Created unique index on session_id");

// 3. Create query indexes
db.itinerary_sessions.createIndex(
  { "user_id": 1, "updated_at": -1 },
  { name: "user_sessions_recent" }
);
print("✓ Created user_sessions_recent index");

db.itinerary_sessions.createIndex(
  { "chat_id": 1 },
  { name: "chat_sessions" }
);
print("✓ Created chat_sessions index");

db.itinerary_sessions.createIndex(
  { "stage": 1, "updated_at": -1 },
  { name: "stage_tracking" }
);
print("✓ Created stage_tracking index");

// 4. Create n8n_integration_logs collection
db.createCollection("n8n_integration_logs");
print("✓ Created n8n_integration_logs collection");

db.n8n_integration_logs.createIndex(
  { "timestamp": -1 },
  { name: "timestamp_desc", expireAfterSeconds: 2592000 }  // 30 days TTL
);
print("✓ Created timestamp_desc index with 30-day TTL");

db.n8n_integration_logs.createIndex(
  { "session_id": 1, "timestamp": -1 },
  { name: "session_logs" }
);
print("✓ Created session_logs index");

// 5. Show created indexes
print("\nIndexes for itinerary_sessions:");
printjson(db.itinerary_sessions.getIndexes());

print("\nIndexes for n8n_integration_logs:");
printjson(db.n8n_integration_logs.getIndexes());

print("\n✅ MongoDB setup complete!");
"@

$setupScript | Out-File -FilePath "setup_mongodb.js" -Encoding UTF8

# Execute setup script
Write-Host "Executing MongoDB setup script..." -ForegroundColor Yellow
mongosh "$MONGO_URI/$DATABASE" --file setup_mongodb.js

# Clean up
Remove-Item "setup_mongodb.js"

Write-Host "`n✅ MongoDB collections and indexes created successfully!" -ForegroundColor Green
Write-Host "Database: $DATABASE" -ForegroundColor Gray
```

**Usage**:
```powershell
# Local development
.\setup_mongodb_collections.ps1

# Production (modify MONGO_URI in script first)
.\setup_mongodb_collections.ps1
```

---

## Backend Integration

### How Voya Backend Communicates with n8n

The Voya FastAPI backend integrates with the CREATE_ITINERARY agent through a webhook endpoint.

#### Backend Files Modified

**1. `backend_python/app/domains/chat/service.py`**

**Key Methods:**

##### `_route_to_itinerary_agent()` - Webhook Call
```python
async def _route_to_itinerary_agent(
    self,
    user_id: str,
    message: str,
    chat_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Route CREATE_ITINERARY intents to n8n webhook

    Returns:
        Response dict with message and metadata including:
        - message: AI response text
        - intent: "CREATE_ITINERARY"
        - stage: Current conversation stage
        - session_id: Session identifier
    """
    n8n_webhook_url = settings.N8N_ITINERARY_WEBHOOK_URL

    payload = {
        "user_id": user_id,
        "chat_id": chat_id,
        "message": message,
        "intent": "CREATE_ITINERARY",
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(n8n_webhook_url, json=payload)
        response.raise_for_status()
        n8n_response = response.json()

    response_intent = n8n_response.get("intent", "CREATE_ITINERARY")
    response_stage = n8n_response.get("stage")

    return {
        "message": n8n_response.get("message", "I'm here to help plan your trip!"),
        "intent": response_intent,  # ✅ Captured from n8n
        "stage": response_stage,
        "session_id": n8n_response.get("session_id"),
        "type": "itinerary_response",
        "itinerary_session": {
            "session_id": n8n_response.get("session_id"),
            "stage": response_stage,
            "type": "itinerary_session",
        },
    }
```

##### `process_message()` - Intent Persistence Logic
```python
async def process_message(
    self, message: str, user: UserPublic, chat_id: str | None = None
) -> ChatResponse:
    """
    Process user message with intent persistence

    Priority order:
    1. Check active itinerary session (from action_data)
    2. Check last message intent (simple fallback) ✅ NEW
    3. Run Intent Recognizer (if no active session)
    """

    # PRIORITY 2.5: Check last message intent
    last_messages = await repository.get_chat_messages(chat_id, limit=1)

    if last_messages and last_messages[0].intent_name == "create_itinerary":
        last_action_data = last_messages[0].action_data or {}
        last_stage = last_action_data.get("stage")

        if last_stage != "completed":
            # ✅ SKIP Intent Recognizer, route directly to n8n
            logger.info(
                f"Last message was create_itinerary (stage: {last_stage}) - "
                "continuing in itinerary flow without Intent Recognizer"
            )

            # Store user message
            await repository.create_message(
                content={"text": message},
                user_id=user_id,
                chat_id=chat_id,
                sender=MessageSender.USER,
                intent_name="create_itinerary",
                action_data={
                    "confidence": 1.0,
                    "source": "last_message_intent",
                },
            )

            # Route to n8n
            response = await self._route_to_itinerary_agent(
                user_id=user_id,
                message=message,
                chat_id=chat_id,
                session_id=chat_id,
            )

            # Store bot response with intent from n8n
            response_intent = response.get("intent", "CREATE_ITINERARY").lower()

            await repository.create_message(
                content={"text": response["message"]},
                user_id=user_id,
                chat_id=chat_id,
                sender=MessageSender.BOT,
                intent_name=response_intent,  # ✅ Use n8n's intent
                action_data=response.get("itinerary_session"),
            )

            return ChatResponse(
                message=response["message"],
                chat_id=chat_id,
                intent_name=response_intent,
                confidence=1.0,
                type=response.get("type", "itinerary_response"),
            )

    # PRIORITY 3: Run Intent Recognizer (no active session)
    intent, confidence = await self.intent_recognizer.recognize(
        message, context=context, user_id=str(user.id)
    )
    # ...
```

**2. `backend_python/app/core/config.py`**

Add n8n webhook URL configuration:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # n8n Integration
    N8N_ITINERARY_WEBHOOK_URL: str = Field(
        default="http://localhost:5678/webhook/itinerary-agent",
        description="n8n webhook URL for itinerary agent"
    )
```

**3. Environment Variables (`.env`)**

```env
# n8n Webhook Configuration
# Development
N8N_ITINERARY_WEBHOOK_URL=http://localhost:5678/webhook/itinerary-agent

# Production
# N8N_ITINERARY_WEBHOOK_URL=https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent
```

---

### Request/Response Flow

#### Request to n8n
```json
POST http://localhost:5678/webhook/itinerary-agent
Content-Type: application/json

{
  "user_id": "user_67890",
  "chat_id": "chat_12345",
  "message": "I want to visit Tokyo in April",
  "intent": "CREATE_ITINERARY",
  "session_id": "session_user_67890_1762187640",
  "timestamp": "2026-02-20T10:30:00.000Z"
}
```

#### Response from n8n
```json
{
  "message": "Tokyo in April is wonderful! Where will you be departing from?",
  "intent": "CREATE_ITINERARY",
  "stage": "initial_vision",
  "session_id": "session_user_67890_1762187640",
  "chat_id": "chat_12345",
  "type": "itinerary_response"
}
```

#### Backend Logs
```
INFO - Last message was create_itinerary (stage: initial_vision) - continuing in itinerary flow without Intent Recognizer
INFO - Routing to n8n itinerary agent - URL: http://localhost:5678/webhook/itinerary-agent
INFO - n8n response received - session: session_user_67890_1762187640, stage: initial_vision, intent: CREATE_ITINERARY
```

---

## Intent Persistence System

### Overview

The Intent Persistence System ensures that once a user starts creating an itinerary, the conversation maintains the `CREATE_ITINERARY` intent across all subsequent messages until completion.

**Before Fix:**
- Message 1: "plan a trip" → CREATE_ITINERARY ✅
- Message 2: "Paris" → GENERAL_QUERY ❌ (intent lost)
- Message 3+: Intent changed, context broken

**After Fix:**
- All messages maintain CREATE_ITINERARY intent until `stage = "completed"`
- Intent Recognizer bypassed for subsequent messages
- Simple "read last message" approach

**Key Documentation:** See `docs/Overview_Create_Itinerary_Intent_Persistence_System.md` for complete technical details.

---

### Technical Implementation

#### Part 1: n8n Workflow Modification

**Node**: "Response Generator"

**Change**: Modified `respondWith` parameter from manual JSON to `firstEntryJson`

**Before:**
```json
{
  "respondWith": "json",
  "responseBody": "={{ { \"message\": $json.message } }}"
}
```

**After:**
```json
{
  "respondWith": "firstEntryJson"
}
```

**Result**: n8n now returns complete object including `intent`, `stage`, `session_id`, `chat_id`, `type`, `message`

---

#### Part 2: Backend Integration Changes

**File**: `backend_python/app/domains/chat/service.py`

**Change 2.1: Capture Intent from n8n Response**

Location: `_route_to_itinerary_agent()` method (lines 122-145)

```python
# NEW: Capture intent field
response_intent = n8n_response.get("intent", "CREATE_ITINERARY")

# NEW: Include in return dict
return {
    "message": n8n_response.get("message", "..."),
    "intent": response_intent,  # ← Capture intent from n8n
    "session_id": response_session_id,
    "stage": response_stage,
    ...
}
```

**Change 2.2: Check Last Message Intent (PRIORITY 2.5)**

Location: `process_message()` method (lines 261-314)

```python
# NEW: Check last message intent before running Intent Recognizer
last_messages = await repository.get_chat_messages(chat_id, limit=1)

if last_messages and last_messages[0].intent_name == "create_itinerary":
    last_action_data = last_messages[0].action_data or {}
    last_stage = last_action_data.get("stage")

    if last_stage != "completed":
        # SKIP Intent Recognizer, route directly to n8n
        logger.info(
            f"Last message was create_itinerary (stage: {last_stage}) - "
            "continuing in itinerary flow without Intent Recognizer"
        )
```

**Change 2.3: Use n8n Intent When Saving Messages**

Location: `process_message()` method (lines 412-430)

```python
# Determine which intent to store
# If n8n returned an intent, use that (it controls the flow)
bot_intent_name = (
    response.get("intent", "CREATE_ITINERARY").lower()
    if response.get("intent")
    else intent_name
)

await repository.create_message(
    ...
    intent_name=bot_intent_name,  # ← Use n8n's intent
    ...
)
```

---

### Message Flow Example

**Message 1: "I want to plan a trip to Japan"**
1. Backend: Check last message → None (first message)
2. Backend: Run Intent Recognizer → CREATE_ITINERARY (0.9)
3. Backend: Route to n8n
4. n8n: Return `{intent: "CREATE_ITINERARY", stage: "initial_vision"}`
5. Backend: Save bot message with `intent_name = "create_itinerary"`

**Message 2: "In March"**
1. Backend: Check last message → intent="create_itinerary", stage="initial_vision"
2. Backend: Stage != "completed" → **SKIP Intent Recognizer** ✅
3. Backend: Route directly to n8n
4. n8n: Has context (Japan + March) → responds appropriately
5. Backend: Save with `intent_name = "create_itinerary"`

**Message 3+: Continues until stage="completed"**

---

### Testing & Verification

**Backend Logs:**
```
[Message 1] Detected intent: create_itinerary (confidence: 0.9)
[Message 1] n8n response - intent: CREATE_ITINERARY, stage: initial_vision

[Message 2] Last message was create_itinerary - continuing without Intent Recognizer
[Message 2] n8n response - intent: CREATE_ITINERARY, stage: initial_vision

[Message N] n8n response - intent: CREATE_ITINERARY, stage: completed
[Message N+1] Stage completed - running Intent Recognizer normally
```

**MongoDB Documents:**
```json
[
  {"sender": "user", "intent_name": "create_itinerary", "content": "plan trip Japan"},
  {"sender": "bot", "intent_name": "create_itinerary", "stage": "initial_vision"},
  {"sender": "user", "intent_name": "create_itinerary", "content": "In March"},
  {"sender": "bot", "intent_name": "create_itinerary", "stage": "initial_vision"},
  ...
  {"sender": "bot", "intent_name": "create_itinerary", "stage": "completed"}
]
```

---

### Key Benefits

1. **Simple & Robust**: Read last message from MongoDB - no complex caching
2. **No Confidence Thresholds**: If last intent was create_itinerary, continue
3. **Single Source of Truth**: n8n controls intent during itinerary flow
4. **Clean Exit**: Resumes normal intent detection when `stage = "completed"`
5. **Zero Schema Changes**: Uses existing message history

**For complete technical documentation, see**: `docs/Overview_Create_Itinerary_Intent_Persistence_System.md`

---

## APIs & External Services

### 1. Gemini AI API

**Purpose**: Natural language understanding and response generation

**Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`

**Configuration in n8n**:
- **Node**: "Call Gemini API" (HTTP Request node)
- **Authentication**: Query parameter `key=YOUR_API_KEY`
- **Model**: `gemini-2.0-flash`
- **Temperature**: 0.7
- **Max Tokens**: 2000

**Local Development**:
```javascript
// In n8n HTTP Request node
URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_GEMINI_API_KEY
```

**Production**:
1. Get production API key from Google Cloud Console
2. Store in n8n credentials or environment variable
3. Update HTTP Request node to use credential

**Environment Variable Approach**:
```javascript
// In n8n HTTP Request node
URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={{$env.GEMINI_API_KEY}}
```

**Docker Compose for n8n**:
```yaml
services:
  n8n:
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

---

### 2. FlightLogic API

**Purpose**: Flight search and booking

**Base URL**:
- Development: `http://localhost:8002` (mock server)
- Production: `https://api.flightlogic.com`

**Endpoints Used**:

#### Flight Availability Search
```
POST /aeroVE5/FlightAvailabilitySearchV5

Request:
{
  "CabinClass": "Y",
  "Currency": "USD",
  "Adults": 1,
  "Children": 0,
  "Infants": 0,
  "IsNonStopFlight": false,
  "JourneyType": "1",  // 1 = Round trip, 2 = One way
  "Segments": [
    {
      "Origin": "JFK",
      "Destination": "NRT",
      "DepartureDateTime": "2026-03-15"
    },
    {
      "Origin": "NRT",
      "Destination": "JFK",
      "DepartureDateTime": "2026-03-29"
    }
  ]
}

Response:
{
  "Response": {
    "Results": [
      [
        {
          "FareSourceCode": "string",
          "Segments": [...],
          "Fare": {
            "Total": 650.00,
            "Currency": "USD"
          }
        }
      ]
    ]
  }
}
```

#### Flight Booking
```
POST /aeroVE5/BookingV5

Request:
{
  "FareSourceCode": "UA_ECONOMY_123",
  "Passengers": [
    {
      "Title": "Mr",
      "FirstName": "John",
      "LastName": "Doe",
      "Gender": "M",
      "DateOfBirth": "1990-01-01",
      "Email": "john.doe@email.com",
      "PhoneNumber": "+1-555-123-4567",
      "PassengerType": "1"  // 1 = Adult
    }
  ]
}

Response:
{
  "Response": {
    "UniqueID": "FL987654321",
    "BookingStatus": "Confirmed",
    "PNR": "ABC123",
    "IssueTicketBy": "2026-03-15T12:00:00Z"
  }
}
```

**Configuration in n8n**:

**Development (Mock Server)**:
```javascript
// In "Check Flight Availability" HTTP Request node
URL: http://flightlogic-mock:8002/aeroVE5/FlightAvailabilitySearchV5
```

**Production**:
```javascript
// In "Check Flight Availability" HTTP Request node
URL: https://api.flightlogic.com/aeroVE5/FlightAvailabilitySearchV5

// Authentication
Headers: {
  "Authorization": "Bearer {{$credentials.flightlogic_api.token}}",
  "X-API-Key": "{{$env.FLIGHTLOGIC_API_KEY}}"
}
```

**n8n Credential Setup (Production)**:
1. Go to n8n → Settings → Credentials
2. Create "HTTP Header Auth" credential named "FlightLogic API"
3. Add header: `Authorization: Bearer YOUR_TOKEN_HERE`
4. Use credential in HTTP Request nodes

---

### 3. MongoDB

**Purpose**: Session storage and conversation history

**Connection String**:
- Development: `mongodb://mongodb:27017`
- Production: `mongodb+srv://username:password@cluster.mongodb.net`

**Database**:
- Development: `n8n_voya_dev`
- Production: `n8n_voya_production`

**Configuration in n8n**:
1. Go to n8n → Settings → Credentials
2. Edit "MongoDB account" credential
3. Update:
   - **Connection String**: Production MongoDB URI
   - **Database**: `n8n_voya_production`
   - **Username**: Production username
   - **Password**: Production password

**Environment Variables**:
```env
# In n8n docker-compose or cloud config
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net
MONGODB_DATABASE=n8n_voya_production
```

---

## Production Deployment

### Files to Modify for Production

#### 1. **Backend `.env` File**
```env
# ===== PRODUCTION CONFIGURATION =====

# n8n Webhook URL
N8N_ITINERARY_WEBHOOK_URL=https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent

# MongoDB (if different from development)
MONGODB_URI=mongodb+srv://prod_user:password@cluster.mongodb.net/n8n_voya_production?retryWrites=true&w=majority

# Gemini AI API Key (Production)
GOOGLE_GENERATIVE_AI_API_KEY=AIzaSy...ProductionKey...xyz

# FlightLogic API (Production)
FLIGHTLOGIC_API_KEY=your_production_flightlogic_key
FLIGHTLOGIC_BASE_URL=https://api.flightlogic.com
```

#### 2. **n8n Cloud Workflow**

**Steps to Deploy to n8n Cloud**:

1. **Export Workflow from Local n8n**:
   - Open local n8n: http://localhost:5678
   - Open "Itinerary Agent MVP - v7" workflow
   - Click "..." → "Download"
   - Saves as JSON file

2. **Import to n8n Cloud**:
   - Go to https://voya-itinerary.app.n8n.cloud
   - Click "Add Workflow" → "Import from File"
   - Select downloaded JSON
   - Click "Import"

3. **Update Credentials in Cloud**:
   - **MongoDB**: Click any MongoDB node → Credentials → "Create New"
     - Name: "MongoDB Production"
     - Connection String: `mongodb+srv://...`
     - Database: `n8n_voya_production`
   - **FlightLogic API**: Create HTTP Header Auth credential
     - Name: "FlightLogic Production"
     - Header: `Authorization`
     - Value: `Bearer YOUR_PRODUCTION_TOKEN`

4. **Update Environment Variables** (if using):
   - Go to n8n Cloud → Settings → Environment Variables
   - Add:
     - `GEMINI_API_KEY`: Production Gemini key
     - `FLIGHTLOGIC_API_KEY`: Production FlightLogic key
     - `MONGODB_URI`: Production MongoDB URI

5. **Update HTTP Request Nodes**:
   - **"Check Flight Availability"** node:
     ```javascript
     // Change URL from
     http://flightlogic-mock:8002/aeroVE5/FlightAvailabilitySearchV5

     // To
     https://api.flightlogic.com/aeroVE5/FlightAvailabilitySearchV5
     ```
   - **"Call FlightLogic Booking API"** node:
     ```javascript
     // Change URL from
     http://flightlogic-mock:8002/aeroVE5/BookingV5

     // To
     https://api.flightlogic.com/aeroVE5/BookingV5
     ```

6. **Activate Workflow**:
   - Toggle "Active" switch in top-right corner
   - Verify webhook URL: `https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent`

#### 3. **Backend Deployment**

Update backend configuration to point to production n8n:

```python
# backend_python/app/core/config.py
class Settings(BaseSettings):
    # Production n8n webhook
    N8N_ITINERARY_WEBHOOK_URL: str = Field(
        default="https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent"
    )
```

Or via environment variable:
```bash
export N8N_ITINERARY_WEBHOOK_URL=https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent
```

---

### Production Checklist

#### Before Deployment:

- [ ] **MongoDB**:
  - [ ] Create `n8n_voya_production` database
  - [ ] Run setup script to create collections and indexes
  - [ ] Verify unique index on `session_id` exists
  - [ ] Set up MongoDB Atlas firewall rules (whitelist n8n Cloud IPs)

- [ ] **n8n Cloud**:
  - [ ] Import workflow to cloud instance
  - [ ] Update all credentials (MongoDB, FlightLogic, Gemini)
  - [ ] Change FlightLogic URLs from mock to production API
  - [ ] Test webhook endpoint is accessible
  - [ ] Activate workflow

- [ ] **Backend**:
  - [ ] Update `.env` with production n8n webhook URL
  - [ ] Update `.env` with production MongoDB URI
  - [ ] Update `.env` with production API keys
  - [ ] Deploy backend to production environment

- [ ] **FlightLogic API**:
  - [ ] Obtain production API credentials
  - [ ] Test availability search endpoint
  - [ ] Test booking endpoint
  - [ ] Verify rate limits and quotas

- [ ] **Gemini AI**:
  - [ ] Create production API key in Google Cloud Console
  - [ ] Set up billing and quotas
  - [ ] Test API connectivity

#### After Deployment:

- [ ] **Test End-to-End Flow**:
  - [ ] Message 1: Plan a trip (intent detection)
  - [ ] Message 2-3: Provide details (intent persistence)
  - [ ] Message 4: Check flights (FlightLogic API)
  - [ ] Message 5: Confirm budget (budget calculation)
  - [ ] Message 6: Book flight (FlightLogic booking)
  - [ ] Verify booking confirmation received

- [ ] **Monitor Logs**:
  - [ ] Backend logs show successful n8n calls
  - [ ] n8n execution history shows successful runs
  - [ ] MongoDB shows sessions being created/updated
  - [ ] No errors in FlightLogic API responses

- [ ] **Performance Testing**:
  - [ ] Verify response times < 3 seconds
  - [ ] Test concurrent users (10+ simultaneous conversations)
  - [ ] Check MongoDB query performance
  - [ ] Monitor n8n execution queue

---

## Future Integrations

### 1. Stripe Payment Integration

**Where to Integrate**: After booking confirmation, before ticket issuance

**Implementation Location**:
- **n8n Workflow**: Add new stage after "booking_handoff" called "payment_processing"
- **Backend**: New endpoint `/api/payments/create-session`

**Flow**:
```
Booking Confirmed (stage = completed)
  ↓
Create Stripe Checkout Session
  ↓
Send payment link to user
  ↓
User completes payment
  ↓
Stripe webhook → n8n → Update booking status
  ↓
Issue ticket via FlightLogic
```

**n8n Nodes to Add**:
1. **"Create Stripe Checkout Session"** (HTTP Request)
2. **"Stripe Webhook"** (Webhook trigger)
3. **"Update Booking Payment Status"** (MongoDB Update)
4. **"Issue Ticket"** (FlightLogic API call)

**Stripe API Endpoints**:
```javascript
// 1. Create Checkout Session
POST https://api.stripe.com/v1/checkout/sessions
Headers: {
  Authorization: "Bearer sk_live_...",
  Content-Type: "application/x-www-form-urlencoded"
}
Body: {
  payment_method_types: ["card"],
  line_items: [{
    price_data: {
      currency: "usd",
      product_data: {
        name: "Flight: New York → Tokyo",
        description: "ANA Direct - March 15, 2026"
      },
      unit_amount: 120000  // $1,200.00 in cents
    },
    quantity: 1
  }],
  mode: "payment",
  success_url: "https://app.voya.com/booking/success?session_id={CHECKOUT_SESSION_ID}",
  cancel_url: "https://app.voya.com/booking/cancel",
  metadata: {
    voya_booking_reference: "VOYA-JD-20250315-ABC123",
    flightlogic_unique_id: "FL987654321"
  }
}

Response: {
  id: "cs_test_...",
  url: "https://checkout.stripe.com/c/pay/cs_test_..."  // Send this to user
}

// 2. Stripe Webhook (listen for payment completion)
POST https://your-n8n-cloud.app.n8n.cloud/webhook/stripe-payment
Body: {
  type: "checkout.session.completed",
  data: {
    object: {
      id: "cs_test_...",
      payment_status: "paid",
      metadata: {
        voya_booking_reference: "VOYA-JD-20250315-ABC123"
      }
    }
  }
}
```

**Code Changes Required**:
```python
# backend_python/app/api/payments.py (NEW FILE)

import stripe
from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-checkout-session")
async def create_checkout_session(booking_reference: str):
    # Get booking details from MongoDB
    booking = await get_booking(booking_reference)

    # Create Stripe session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": booking["currency"],
                "product_data": {
                    "name": f"Flight: {booking['route']}",
                },
                "unit_amount": int(booking["total_price"] * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"https://app.voya.com/booking/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url="https://app.voya.com/booking/cancel",
        metadata={"voya_booking_reference": booking_reference}
    )

    return {"checkout_url": checkout_session.url}
```

---

### 2. Email Confirmation

**Where to Send Emails**:
1. After booking confirmation (with payment link)
2. After payment completion (with ticket details)
3. 24 hours before departure (reminder)

**Email Service**: SendGrid or AWS SES

**Implementation Location**:
- **n8n Workflow**: Add "Send Email" node after booking confirmation
- **Backend**: Optional - Send via backend email service

**n8n SendGrid Integration**:
```javascript
// "Send Booking Confirmation Email" node (HTTP Request)
POST https://api.sendgrid.com/v3/mail/send
Headers: {
  Authorization: "Bearer SG.YOUR_API_KEY",
  Content-Type: "application/json"
}
Body: {
  personalizations: [{
    to: [{ email: "john.doe@email.com", name: "John Doe" }],
    subject: "✈️ Your Flight to Tokyo - Booking Confirmed!"
  }],
  from: {
    email: "bookings@voya.com",
    name: "Voya Travel"
  },
  content: [{
    type: "text/html",
    value: `
      <h1>Booking Confirmed!</h1>
      <p>Dear John Doe,</p>
      <p>Your flight has been booked successfully.</p>

      <h2>Flight Details</h2>
      <ul>
        <li>Booking Reference: <strong>VOYA-JD-20250315-ABC123</strong></li>
        <li>Route: New York (JFK) → Tokyo (NRT)</li>
        <li>Departure: March 15, 2026 at 08:00 AM</li>
        <li>Airline: ANA Direct</li>
        <li>Total: $1,200 USD</li>
      </ul>

      <h2>Next Steps</h2>
      <p>Complete payment within 24 hours: <a href="https://checkout.stripe.com/...">Pay Now</a></p>

      <p>Questions? Reply to this email or visit our help center.</p>

      <p>Happy travels!<br>The Voya Team</p>
    `
  }]
}
```

**Environment Variables**:
```env
SENDGRID_API_KEY=SG.your_production_key
SENDGRID_FROM_EMAIL=bookings@voya.com
SENDGRID_FROM_NAME=Voya Travel
```

---

### 3. Hotel Booking Integration

**API**: FlightLogic Hotel API or Booking.com API

**Workflow Stage**: Add after `availability_check` stage

**n8n Nodes to Add**:
1. **"Check Hotel Availability"** (HTTP Request)
2. **"Parse Hotel Results"** (Code node)
3. **"Book Hotel"** (HTTP Request) - in booking_handoff stage

**FlightLogic Hotel API**:
```javascript
// Hotel Search
POST /aeroVE5/HotelAvailabilitySearchV5
Body: {
  "CheckIn": "2026-03-15",
  "CheckOut": "2026-03-29",
  "City": "Tokyo",
  "CountryCode": "JP",
  "Rooms": 1,
  "Adults": 1,
  "Children": 0
}

Response: {
  "Response": {
    "Hotels": [
      {
        "HotelCode": "TOKYO_HTL_123",
        "HotelName": "Tokyo Plaza Hotel",
        "PricePerNight": 100,
        "TotalPrice": 1400,
        "Currency": "USD",
        "Rating": 4.5
      }
    ]
  }
}
```

---

### 4. Multi-City Itineraries

**Current Limitation**: Workflow supports single destination (origin → destination)

**Future Enhancement**: Support multi-city trips (New York → Tokyo → Kyoto → New York)

**Changes Required**:
- **MongoDB Schema**: Change `destination` to `destinations` array
- **FlightLogic API**: Use multi-segment booking
- **n8n Workflow**: Update stage logic to handle multiple destinations

---

## Testing & Monitoring

### Testing Checklist

#### Unit Testing (Backend)
```bash
# Test intent persistence logic
cd backend_python
pytest tests/unit_tests/test_chat_service.py::test_intent_persistence -v

# Test n8n webhook integration
pytest tests/unit_tests/test_chat_service.py::test_route_to_itinerary_agent -v
```

#### Integration Testing (E2E)
```powershell
# Test complete flow (5 stages)
.\scripts\test_phase5_booking_endtoend.sh

# Test intent persistence
.\test_backend_intent.ps1
```

#### Manual Testing Scenarios

**Scenario 1: Happy Path (Booking Success)**
```
1. "I want to plan a trip to Tokyo"
   Expected: "Great! When do you want to travel?" (stage: initial_vision)

2. "In March, for 2 weeks"
   Expected: "Where will you depart from?" (stage: route_refinement)

3. "From New York"
   Expected: "Checking flights..." (stage: availability_check)
   Expected: Shows 3 flight options

4. "My budget is around $3000"
   Expected: Budget breakdown (stage: budget_estimation)

5. "Book option 2 please"
   Expected: Asks for passenger details (stage: booking_handoff)

6. "John Doe, john@email.com, +1-555-123-4567"
   Expected: Booking confirmation (stage: completed)
```

**Scenario 2: Intent Persistence**
```
1. "plan a trip" → CREATE_ITINERARY detected
2. "Paris" → Intent maintained (not GENERAL_QUERY)
3. "March" → Intent maintained
4. "2 weeks" → Intent maintained
```

**Scenario 3: Over Budget**
```
1-3. [Same as Scenario 1]
4. "My budget is $500"
   Expected: "Your trip costs $2,950, which exceeds your budget by $2,450. Here are some options:
             1. Choose cheaper flight ($650 instead of $1,200)
             2. Shorter trip (7 days instead of 14)
             3. Budget hotels ($50/night instead of $100/night)"
```

**Scenario 4: No Flights Available**
```
1-3. [Same as Scenario 1, but with unavailable dates]
   Expected: "I couldn't find any direct flights for those dates. Would you like to:
             1. Try different dates
             2. Consider flights with layovers
             3. Try a different departure city"
```

---

### Monitoring

#### Backend Logs
```bash
# Follow backend logs
docker compose logs backend --follow --tail=50

# Search for intent persistence logs
docker compose logs backend | grep "Last message was create_itinerary"

# Search for n8n routing logs
docker compose logs backend | grep "n8n response received"
```

**Key Log Messages**:
```
INFO - Last message was create_itinerary (stage: initial_vision) - continuing in itinerary flow without Intent Recognizer
INFO - Routing to n8n itinerary agent - URL: https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent
INFO - n8n response received - session: session_xxx, stage: initial_vision, intent: CREATE_ITINERARY
```

#### n8n Execution History
1. Go to n8n Cloud → Executions
2. Filter by workflow: "Itinerary Agent MVP"
3. Check for:
   - ✅ Successful executions (green)
   - ⚠️ Warnings (yellow)
   - ❌ Errors (red)

**Common Errors**:
- **MongoDB connection timeout**: Check MongoDB Atlas firewall rules
- **FlightLogic API 401**: Check API credentials
- **Gemini API 403**: Check API key and billing

#### MongoDB Queries

```javascript
// Check recent sessions
db.itinerary_sessions.find().sort({updated_at: -1}).limit(10);

// Count sessions by stage
db.itinerary_sessions.aggregate([
  {$group: {_id: "$stage", count: {$sum: 1}}}
]);

// Find stuck sessions (not updated in 24 hours)
db.itinerary_sessions.find({
  stage: {$ne: "completed"},
  updated_at: {$lt: new Date(Date.now() - 24*60*60*1000)}
});

// Check booking success rate
db.itinerary_sessions.aggregate([
  {$match: {stage: "completed"}},
  {$group: {
    _id: "$booking_confirmation.booking_status",
    count: {$sum: 1}
  }}
]);
```

#### Metrics to Track

| Metric | Query | Target |
|--------|-------|--------|
| **Session Completion Rate** | `completed / total sessions` | > 60% |
| **Average Time to Booking** | Time from first message to booking_handoff | < 10 minutes |
| **Intent Persistence Success** | Messages that skip Intent Recognizer | > 90% |
| **FlightLogic API Success Rate** | Successful flight searches / total attempts | > 95% |
| **Booking Success Rate** | Successful bookings / booking attempts | > 90% |

---

## Troubleshooting

### Common Issues

#### 1. Intent Lost on Second Message

**Symptoms**:
```
Message 1: "plan a trip" → CREATE_ITINERARY ✅
Message 2: "Paris" → GENERAL_QUERY ❌
```

**Diagnosis**:
```bash
# Check backend logs
docker compose logs backend | grep "Last message was create_itinerary"

# Should see: "continuing in itinerary flow without Intent Recognizer"
# If not, intent persistence is not working
```

**Fixes**:
- Verify backend has latest code (commit e98116e or later)
- Check n8n returns `intent` field in response
- Verify MongoDB stores `intent_name` in messages

---

#### 2. n8n Not Returning Intent Field

**Symptoms**:
```json
// Response missing intent field
{
  "message": "Where do you want to go?",
  "session_id": "session_xxx"
  // Missing: "intent": "CREATE_ITINERARY"
}
```

**Diagnosis**:
```bash
# Test n8n webhook directly
curl -X POST http://localhost:5678/webhook/itinerary-agent \
  -H "Content-Type: application/json" \
  -d '{"message":"test","user_id":"test","chat_id":"test"}' | jq
```

**Fixes**:
- Check "Response Generator" node uses `respondWith: "firstEntryJson"`
- Check "Prepare Response" node includes `intent` field
- Verify n8n workflow is activated (green toggle)

---

#### 3. MongoDB Connection Errors

**Symptoms**:
```
MongoNetworkError: connect ECONNREFUSED
```

**Fixes**:
- Development: `docker compose up -d mongodb`
- Production: Check MongoDB Atlas firewall rules (whitelist n8n Cloud IPs)
- Verify connection string format: `mongodb+srv://user:pass@cluster.mongodb.net/db`

---

#### 4. FlightLogic API Errors

**Symptoms**:
```
HTTP 401 Unauthorized
HTTP 404 Not Found
```

**Fixes**:
- Check API credentials in n8n
- Verify base URL (development: localhost:8002, production: api.flightlogic.com)
- Test API directly with Postman/cURL
- Check rate limits and quotas

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| **n8n** | Low-code workflow automation tool for building integrations |
| **Webhook** | HTTP endpoint that receives POST requests from external systems |
| **Intent** | User's goal detected by Intent Recognizer (e.g., CREATE_ITINERARY) |
| **Session** | Complete conversation context stored in MongoDB |
| **Stage** | Current step in the itinerary planning process |
| **Sticky Intent** | Mechanism to maintain intent across multiple messages |
| **FlightLogic** | Travel API for flight search and booking |
| **Gemini AI** | Google's large language model for natural language understanding |

---



**Last Updated**: November 2025
**Document Version**: 1.0
