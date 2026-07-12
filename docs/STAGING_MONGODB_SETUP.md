# Staging MongoDB Setup - Intent Persistence Implementation

This document provides the exact MongoDB scripts required to support the intent persistence feature in staging environment.

## Overview

The intent persistence system uses two MongoDB collections:
1. **`itinerary_sessions`** - Stores complete itinerary planning data across multi-stage workflow
2. **`n8n_integration_logs`** - Logs all n8n webhook interactions for debugging

## Collection 1: itinerary_sessions

### Purpose

Stores the complete state of an itinerary planning conversation including:
- Conversation history (last 20 messages for context)
- Collected travel data (destination, dates, budget, preferences)
- Flight availability results from FlightLogic API
- Hotel and weather information
- Budget calculations and suggestions
- Selected flight details
- Passenger information
- Booking confirmation details

The `stage` field in this collection drives the intent persistence system - it determines which stage of the workflow the conversation is in.

### Schema

```javascript
{
  "_id": ObjectId,
  "session_id": String,              // Unique session ID (e.g., "session_user123_1234567890")
  "user_id": String,                 // Voya user ID
  "chat_id": String,                 // Chat conversation ID
  "stage": String,                   // Current stage: initial_vision, route_refinement, availability_check, budget_estimation, booking_handoff, completed

  // Conversation context
  "conversation_history": [
    {
      "role": String,                // "user" or "assistant"
      "content": String,             // Message text
      "timestamp": ISODate
    }
  ],

  // Collected travel data
  "collected_data": {
    "destination": String,           // e.g., "Tokyo, Japan"
    "origin": String,                // e.g., "New York, USA"
    "departure_date": String,        // YYYY-MM-DD
    "return_date": String,           // YYYY-MM-DD
    "adults": Number,
    "children": Number,
    "interests": [String],           // e.g., ["temples", "food"]
    "budget_min": Number,
    "budget_max": Number,
    "budget_currency": String
  },

  // Flight availability (from FlightLogic)
  "flight_availability": {
    "status": String,                // "available" or "unavailable"
    "route": {
      "origin": String,              // IATA code (e.g., "JFK")
      "destination": String,         // IATA code (e.g., "NRT")
      "departure_date": String,
      "return_date": String
    },
    "flights": [
      {
        "label": String,             // "Lowest Price 💵", "Fastest ⚡", "Best Value ⭐"
        "airline": String,
        "price": {
          "total": Number,
          "currency": String
        },
        "stops": Number,
        "duration_minutes": Number,
        "departure_time": ISODate,
        "arrival_time": ISODate,
        "fare_source_code": String
      }
    ]
  },

  // Hotel availability
  "hotel_availability": {
    "status": String,
    "hotels_found": Number,
    "price_range": {
      "min": Number,
      "max": Number,
      "currency": String
    }
  },

  // Weather forecast
  "weather_data": {
    "forecast": {
      "temperature_avg": Number,
      "temperature_unit": String,    // "C" or "F"
      "conditions": String,
      "precipitation_chance": Number
    }
  },

  // Budget breakdown
  "budget_data": {
    "flights": {"total": Number, "currency": String},
    "hotels": {"total": Number, "nights": Number, "rate_per_night": Number, "currency": String},
    "daily_expenses": {"total": Number, "days": Number, "rate_per_day": Number, "currency": String},
    "summary": {
      "total_trip_cost": Number,
      "user_budget_max": Number,
      "currency": String,
      "status": String,              // "within_budget" or "over_budget"
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

  // Stage validation
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
    "option_number": Number,         // 1, 2, or 3
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
    "flightlogic_unique_id": String,
    "booking_status": String,              // "confirmed", "pending", "failed"
    "payment_status": String,              // "pending", "completed"
    "ticket_deadline": ISODate,
    "booked_flight": Object,
    "confirmation_sent_to": String,        // Email
    "booking_timestamp": ISODate
  },

  // Timestamps
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### MongoDB Setup Script

Execute these commands in MongoDB staging (MongoDB Compass, Atlas shell, or mongosh):

```javascript
// 1. CREATE COLLECTION
db.createCollection("itinerary_sessions");

// 2. CREATE UNIQUE INDEX ON session_id
// WHY: Prevents duplicate sessions for the same conversation
// The backend uses session_id to retrieve the current itinerary session
db.itinerary_sessions.createIndex(
  { "session_id": 1 },
  { unique: true, name: "session_id_unique" }
);

// 3. CREATE INDEX: User sessions ordered by update time
// WHY: Retrieves all sessions for a user, ordered by most recently modified
// Used when listing user's itineraries or checking for active sessions
db.itinerary_sessions.createIndex(
  { "user_id": 1, "updated_at": -1 },
  { name: "user_sessions_recent" }
);

// 4. CREATE INDEX: Sessions by chat ID
// WHY: Quick lookup of itinerary session for a specific chat conversation
// Required by backend's _get_active_itinerary_session() method
db.itinerary_sessions.createIndex(
  { "chat_id": 1 },
  { name: "chat_sessions" }
);

// 5. CREATE INDEX: Sessions by stage for monitoring progress
// WHY: Tracks conversation progress through stages
// Allows monitoring which sessions are stuck in initial_vision, etc.
db.itinerary_sessions.createIndex(
  { "stage": 1, "updated_at": -1 },
  { name: "stage_tracking" }
);

// 6. VERIFY INDEXES CREATED
db.itinerary_sessions.getIndexes();
// Should show all 5 indexes (4 created + default _id index)
```

---

## Collection 2: n8n_integration_logs

### Purpose

Records all webhook interactions between backend and n8n for debugging and monitoring:
- Incoming requests from backend to n8n
- Outgoing responses from n8n to backend
- Session ID, stage, intent information
- Full payload for troubleshooting failures

Includes automatic cleanup: logs older than 30 days are automatically deleted.

### Schema

```javascript
{
  "_id": ObjectId,
  "timestamp": ISODate,              // When the interaction occurred
  "direction": String,               // "incoming" (backend→n8n) or "outgoing" (n8n→backend)
  "session_id": String,              // References itinerary_sessions.session_id
  "user_id": String,
  "chat_id": String,
  "message": String,                 // User message or bot response
  "stage": String,                   // Current workflow stage
  "intent": String,                  // "CREATE_ITINERARY"
  "payload_size": Number,            // Bytes (for performance monitoring)
  "full_payload": Object,            // Complete request/response JSON
  "status_code": Number,             // HTTP response code (for outgoing)
  "error": String                    // Error message if request failed
}
```

### MongoDB Setup Script

```javascript
// 1. CREATE COLLECTION
db.createCollection("n8n_integration_logs");

// 2. CREATE INDEX: Timestamp in descending order
// WHY: Logs are queried most recent first
// Enables efficient "show last 100 logs" queries
db.n8n_integration_logs.createIndex(
  { "timestamp": -1 },
  { name: "timestamp_desc" }
);

// 3. CREATE INDEX: Session logs ordered by timestamp
// WHY: Retrieves all logs for a specific session (for debugging one conversation)
// Allows seeing entire message flow between backend and n8n for that session
db.n8n_integration_logs.createIndex(
  { "session_id": 1, "timestamp": -1 },
  { name: "session_logs" }
);

// 4. CREATE TTL INDEX: Auto-delete logs after 30 days
// WHY: Reduces database size and prevents logs from growing indefinitely
// 30 days = 2,592,000 seconds (sufficient for post-incident analysis)
// Documents with expireAt timestamp automatically deleted by MongoDB background task
db.n8n_integration_logs.createIndex(
  { "timestamp": 1 },
  {
    expireAfterSeconds: 2592000,
    name: "ttl_30_days"
  }
);

// 5. VERIFY INDEXES CREATED
db.n8n_integration_logs.getIndexes();
// Should show 4 indexes (3 created + default _id index)
```

---

## Complete Setup Script (Run All At Once)

Copy and paste this entire block into MongoDB staging:

```javascript
// ============================================================================
// ITINERARY SESSIONS COLLECTION
// ============================================================================

db.createCollection("itinerary_sessions");

db.itinerary_sessions.createIndex(
  { "session_id": 1 },
  { unique: true, name: "session_id_unique" }
);

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

// ============================================================================
// N8N INTEGRATION LOGS COLLECTION
// ============================================================================

db.createCollection("n8n_integration_logs");

db.n8n_integration_logs.createIndex(
  { "timestamp": -1 },
  { name: "timestamp_desc" }
);

db.n8n_integration_logs.createIndex(
  { "session_id": 1, "timestamp": -1 },
  { name: "session_logs" }
);

db.n8n_integration_logs.createIndex(
  { "timestamp": 1 },
  {
    expireAfterSeconds: 2592000,
    name: "ttl_30_days"
  }
);

// ============================================================================
// VERIFICATION
// ============================================================================

print("=== itinerary_sessions indexes ===");
db.itinerary_sessions.getIndexes();

print("=== n8n_integration_logs indexes ===");
db.n8n_integration_logs.getIndexes();

print("=== Collections created ===");
db.getCollectionNames();
```

---

## N8N Webhook Configuration

The backend communicates with n8n through a webhook. Configure this in your staging environment:

### Environment Variable

Add/update in your staging deployment (AWS ECS Task Definition or equivalent):

```env
N8N_ITINERARY_WEBHOOK_URL=https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent
```

**Location in code**: `backend_python/app/core/config.py` (line 139)

This URL receives POST requests from the backend with the format:

```json
{
  "user_id": "user_12345",
  "chat_id": "chat_abc",
  "message": "I want to visit Tokyo in April",
  "intent": "CREATE_ITINERARY",
  "session_id": "session_user_12345_1762187640",
  "timestamp": "2025-11-04T10:30:00Z"
}
```

And returns:

```json
{
  "message": "Tokyo in April is wonderful!...",
  "intent": "CREATE_ITINERARY",
  "stage": "initial_vision",
  "session_id": "session_user_12345_1762187640",
  "chat_id": "chat_abc",
  "type": "itinerary_response"
}
```

---

## Verification Steps

After running the MongoDB setup scripts, verify everything is configured:

### 1. Check Collections Exist

```javascript
db.getCollectionNames();
// Should include: "itinerary_sessions", "n8n_integration_logs"
```

### 2. Check Indexes Created

```javascript
db.itinerary_sessions.getIndexes();
// Should show:
// - _id_ (default)
// - session_id_unique
// - user_sessions_recent
// - chat_sessions
// - stage_tracking

db.n8n_integration_logs.getIndexes();
// Should show:
// - _id_ (default)
// - timestamp_desc
// - session_logs
// - ttl_30_days
```

### 3. Test Insert (Optional)

```javascript
// Insert a test document
db.itinerary_sessions.insertOne({
  "session_id": "test_session_1",
  "user_id": "test_user_1",
  "chat_id": "test_chat_1",
  "stage": "initial_vision",
  "conversation_history": [],
  "collected_data": {},
  "created_at": new Date(),
  "updated_at": new Date()
});

// Should succeed without errors
// Try inserting same session_id again - should fail due to unique index
db.itinerary_sessions.insertOne({
  "session_id": "test_session_1",
  "user_id": "test_user_2",
  "chat_id": "test_chat_2",
  "stage": "initial_vision",
  "conversation_history": [],
  "collected_data": {},
  "created_at": new Date(),
  "updated_at": new Date()
});
// Should error: "E11000 duplicate key error"

// Clean up test data
db.itinerary_sessions.deleteMany({"user_id": /test_/});
```

---

## Index Explanation Summary

| Index Name | Fields | Type | Why |
|---|---|---|---|
| `session_id_unique` | session_id | Unique | Prevents duplicate sessions; Backend retrieves by this ID |
| `user_sessions_recent` | user_id, updated_at desc | Regular | Lists user's itineraries; Efficient "most recent first" queries |
| `chat_sessions` | chat_id | Regular | Links chat conversation to itinerary session |
| `stage_tracking` | stage, updated_at desc | Regular | Monitors workflow progress; Finds stuck conversations |
| `timestamp_desc` | timestamp desc | Regular | Recent logs first (debugging); Most common query pattern |
| `session_logs` | session_id, timestamp desc | Regular | All logs for one session (troubleshooting single conversation) |
| `ttl_30_days` | timestamp | TTL | Automatic cleanup; Deletes logs older than 30 days |

---

## Database Names by Environment

- **Local Development**: `n8n_voya_dev`
- **Staging**: `n8n_voya_staging` (or your staging database name)
- **Production**: `n8n_voya_production`

---

## References

- Backend n8n integration: `backend_python/app/domains/chat/service.py`
- Configuration: `backend_python/app/core/config.py` (line 139)
- Complete system guide: `docs/CREATE_ITINERARY_COMPLETE_GUIDE.md`

---

**Last Updated**: November 2025
