# Flight Search JSON Response Structure

This document describes the new structured JSON response format for flight search results, implemented as part of issue #72.

## Overview

When flights are found, the backend now returns a structured JSON response with type `"flight_search_results"` instead of just a formatted text message. This enables the frontend to render rich, interactive flight search results.

## Backend Changes

### Response Structure

The backend now returns:

```json
{
  "message": "✈️ Your journey: LAX → JFK...",  // Fallback text message
  "type": "flight_search_results",            // New specific type
  "data": {                                   // Structured flight data
    "search_params": { ... },
    "summary": { ... },
    "flights": { ... },
    "categories": { ... },
    "refinement": { ... }
  },
  "chat_id": "uuid",
  "intent_name": "flight_search",
  "confidence": 0.95
}
```

### Data Structure Details

#### `data.search_params`
```json
{
  "origin": "LAX",
  "destination": "JFK",
  "departure": {
    "type": "fixed|flexible",
    "date": "2024-01-15",           // ISO date string
    "display": "Mon, Jan 15"       // Human readable
  },
  "return": {
    "date": "2024-01-22",
    "display": "Mon, Jan 22"
  },
  "passengers": {
    "adults": 1,
    "children": 0,
    "infants": 0
  },
  "cabin_class": "economy",
  "journey_type": "OneWay"
}
```

#### `data.summary`
```json
{
  "route_text": "✈️ Your journey: LAX → JFK",
  "total_flights": 45,
  "direct_count": 12,
  "price_range": {
    "min": 299,
    "max": 899,
    "currency": "USD"
  },
  "is_round_trip": false
}
```

#### `data.flights`
```json
{
  "outbound": [
    {
      "id": "fare_source_code_123",
      "airline": "UA",
      "flight_number": "UA1234",
      "departure_time": "08:00",
      "arrival_time": "16:30", 
      "duration": "5h 30m",
      "stops": 0,
      "price": 299.99,
      "currency": "USD"
    }
  ],
  "inbound": [...]  // For round trips only
}
```

#### `data.categories`
Curated flight recommendations:

```json
{
  "lowest_price": {
    "emoji": "💵",
    "label": "Lowest Price",
    "flight": { /* flight object */ },
    "highlight": "Best price available"
  },
  "fastest": {
    "emoji": "⚡", 
    "label": "Fastest",
    "flight": { /* flight object */ },
    "highlight": "Shortest travel time"
  },
  "best_value": {
    "emoji": "⭐",
    "label": "Best Value", 
    "flight": { /* flight object */ },
    "highlight": "Great balance of price and convenience"
  }
}
```

#### `data.refinement`
```json
{
  "available": true,
  "message": "Want to refine your search instead?..."
}
```

## Frontend Integration Guide

### 1. Message Type Detection

In your chat message rendering component, check for the new type:

```javascript
// In ChatMessage.jsx or equivalent
if (msg.type === "flight_search_results" && msg.data) {
  return <FlightSearchResults data={msg.data} onBook={handleBookFlight} />;
} else {
  return <MarkdownChatMessage content={msg.message} />; // Fallback
}
```

### 2. Component Structure

Create a `FlightSearchResults` component that displays:

1. **Summary Header**: Route, flight count, price range
2. **Recommended Categories**: Cards for lowest price, fastest, best value
3. **Action Buttons**: "View All Flights", "Refine Search", etc.

### 3. Flight Booking Integration

When user selects a flight:

```javascript
const handleBookFlight = (flightId, category) => {
  const message = category 
    ? `Book the ${category} flight`
    : `Book flight ${flightId}`;
    
  sendChatMessage(message);
};
```

### 4. Fallback Behavior

Always provide fallback to the text message:

```javascript
// If structured data is missing or malformed
if (!msg.data || !msg.data.flights) {
  return <MarkdownChatMessage content={msg.message} />;
}
```

### 5. Backward Compatibility

The backend maintains backward compatibility:
- `message` field still contains formatted text
- `flights` and `search_params` fields still available at root level
- Only the `type` field changes from `"flight_results"` to `"flight_search_results"`

## Implementation Notes

### Backend Implementation
- New methods added to `EnhancedFlightBookingHandler`:
  - `_create_flight_search_data()` - Creates structured response
  - `_categorize_flights()` - Finds best options (💵⚡⭐)  
  - `_serialize_flight()` - Converts flight objects to frontend format

### Data Source
- Flight data comes from FlightLogic API via `FareItinerary` objects
- Prices extracted from `fare_totals.total_fare`
- Flight details from `flight_legs` array
- Categories determined by price, duration, and quality heuristics

### Error Handling
- If flight serialization fails, safe fallback data is returned
- Missing fields default to empty strings or 0 values
- Frontend should always check for data availability

## Testing

To test the new structure:

1. **Backend**: Search for flights via chat interface
2. **Verify Response**: Check that `type === "flight_search_results"`  
3. **Validate Data**: Ensure `data` object contains expected structure
4. **Test Fallback**: Verify `message` field still contains readable text

## Migration Timeline

- ✅ **Backend**: Structured data response implemented
- 🔄 **Frontend**: Needs implementation of new message type handling
- 📋 **Future**: Consider deprecating old `flight_results` type after frontend migration

## Related Files

**Backend**:
- `app/ai/enhanced_flight_handler.py` - Main implementation
- `app/ai/flight_summary_generator.py` - Text generation (still used)
- `app/domains/chat/schemas.py` - Response schema

**Frontend** (needs updates):
- `src/chatbot/components/Messages/ChatMessage.jsx` - Add type handling
- Create: `src/chatbot/components/Messages/MessageTypes/FlightSearchResults.jsx`

---

**Created**: November 2025  
**Issue**: #72  
**Status**: Backend Complete, Frontend Pending