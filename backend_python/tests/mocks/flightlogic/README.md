# FlightLogic Mock Server

A lightweight FastAPI-based mock server that simulates the FlightLogic API for local development and testing.

## Purpose

- **Test Flight Booking Flow**: Test complete search → select → book flow without hitting production API
- **Reproduce Bugs Locally**: Debug session_id and fare_source_code extraction issues
- **Validate Request/Response Formats**: Ensure API integration matches expected structure
- **CI/CD Testing**: Run integration tests without external dependencies

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services including mock server (mock is included by default)
docker compose up -d

# View mock server logs
docker compose logs -f flightlogic-mock

# Access mock server at http://localhost:8002
```

See [docker-mock-server.md](../../../../docs/docker-mock-server.md) for complete Docker integration guide.

### Option 2: Standalone Python (Local Development)

```bash
# From backend_python directory
python -m tests.mocks.flightlogic.server

# Custom port
python -m tests.mocks.flightlogic.server --port 8002
```

The server will start on `http://localhost:8002` by default.

### Configure Backend to Use Mock

Update your `.env` file:

```bash
# Point to mock server instead of production FlightLogic API
FLIGHTLOGIC_API_URL=http://localhost:8002/api/aeroVE5

# Keep your API key (mock server doesn't validate it)
FLIGHTLOGIC_API_KEY=your-key-here
```

### Test the Mock Server

```bash
# Health check
curl http://localhost:8002/health

# Search flights
curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "AMS",
    "destination": "LHR",
    "departure_date": "2025-11-15",
    "adults": 1
  }'

# Book flight (use session_id and fare_source_code from search response)
curl -X POST http://localhost:8002/api/aeroVE5/booking \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "MOCK_SESSION_20251010123456",
    "fare_source_code": "MOCK_FARE_BEST_VALUE_123456",
    "passengers": [{"name": "John Doe", "dob": "1990-01-01"}]
  }'
```

## API Endpoints

### POST `/api/aeroVE5/availability` - Flight Search

**Request**:
```json
{
  "origin": "AMS",
  "destination": "LHR",
  "departure_date": "2025-11-15",
  "return_date": null,
  "adults": 1,
  "children": 0,
  "infants": 0
}
```

**Response**:
```json
{
  "AirSearchResponse": {
    "session_id": "MOCK_SESSION_20251010123456",
    "supplier": "MockAir",
    "AirSearchResult": {
      "FareItineraries": [
        {
          "AirItineraryFareInfo": {
            "FareSourceCode": "MOCK_FARE_BEST_VALUE_123456",
            "ItinTotalFares": {
              "TotalFare": {"Amount": "295.50", "CurrencyCode": "EUR"}
            }
          },
          "OriginDestinationOptions": [...]
        }
      ]
    }
  }
}
```

Returns **3 mock flights** with multi-segment and round-trip support:

| Flight | Airline | Stops | One-Way Price | Round-Trip Price |
|--------|---------|-------|---------------|------------------|
| Best Value | British Airways (BA) | 1 | €295.50 | €531.90 |
| Cheapest | Ryanair (FR) | 2 | €215.00 | €387.00 |
| Direct | KLM (KL) | 0 | €375.00 | €675.00 |

**Multi-Segment Features**:
- Flights with stops include proper intermediate segments (e.g., LHR → FRA → AMS)
- Each layover segment includes `StopQuantityInfo` with duration and location
- Hub airports used for layovers: FRA, CDG, MAD, FCO, MUC, ZRH

**Round-Trip Support**:
- If `return_date` is provided, response includes both outbound and return legs
- `DirectionInd: "Return"` for round-trips, `"OneWay"` for one-way
- Backend adds `is_round_trip: true` flag for frontend display

See examples below in the "Multi-Segment Flight Examples" section

### POST `/api/aeroVE5/booking` - Create Booking

**Request**:
```json
{
  "session_id": "MOCK_SESSION_20251010123456",
  "fare_source_code": "MOCK_FARE_BEST_VALUE_123456",
  "passengers": [
    {
      "name": "John Doe",
      "dob": "1990-01-01",
      "passport": "AB123456"
    }
  ],
  "contact_info": {
    "email": "john@example.com",
    "phone": "+31612345678"
  }
}
```

**Success Response** (HTTP 200):
```json
{
  "BookFlightResponse": {
    "BookFlightResult": {
      "Status": "CONFIRMED",
      "Success": true,
      "UniqueID": "MOCK_BOOKING_20251010123500",
      "TktTimeLimit": "2025-10-11T12:35:00",
      "Target": "Test"
    }
  }
}
```

**Error Response** (HTTP 400):
```json
{
  "Errors": {
    "ErrorCode": "INVALID_SESSION",
    "ErrorMessage": "Invalid session_id or fare_source_code. Session: MOCK_SESSION_123, Fare: INVALID_FARE"
  }
}
```

### GET `/health` - Health Check

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T12:34:56"
}
```

## Session Validation

The mock server validates that `session_id` and `fare_source_code` match:

1. **Search** creates a session with valid fare codes
2. **Booking** validates the fare code belongs to that session
3. **Invalid combinations** return `HTTP 400` error

This reproduces the production bug where session_id collision causes booking failures.

## Mock Data Structure

- **`mock_data.py`**: Contains sample responses and validation logic
- **`MOCK_SESSIONS`**: In-memory dict tracking session_id → fare_codes
- **`generate_mock_session_id()`**: Creates unique session IDs with timestamp
- **`get_mock_search_response()`**: Returns 3 realistic flight options
- **`get_mock_booking_response()`**: Returns success/error based on validation
- **`validate_booking_request()`**: Checks session_id + fare_source_code match

## Mock Server Behavior

### Default: Always Returns 3 Flights

**The mock server returns 3 mock flights** for any valid search request, regardless of:
- Origin/destination airports (except special test cases)
- Dates (past, present, or future)
- Number of passengers
- Cabin class

This ensures you can test the complete booking flow without worrying about IP whitelisting or API rate limits.

**The 3 mock flights are:**
1. **Best Value** - €295.50 (one-way) / €531.90 (round-trip) - British Airways - 1 stop
2. **Cheapest** - €215.00 (one-way) / €387.00 (round-trip) - Ryanair - 2 stops
3. **Direct** - €375.00 (one-way) / €675.00 (round-trip) - KLM - 0 stops

Each flight with stops includes proper multi-segment data with layover information.

### Special Test Airport Code: "XXX"

**To test "No Results" scenario**, use airport code **`XXX`** as origin or destination:

```bash
# Example 1: Search from XXX (returns 0 results)
curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{"origin":"XXX","destination":"LHR","departure_date":"2025-11-15","adults":1}'

# Example 2: Search to XXX (returns 0 results)
curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{"origin":"AMS","destination":"XXX","departure_date":"2025-11-15","adults":1}'

# Example 3: In chat UI - just say "I want to fly to XXX"
```

**Frontend Testing:**
1. Open chat
2. Say: "I want to fly from Amsterdam to XXX tomorrow"
3. Voya will show: "No flights found matching your criteria..."

### Why This Design?

The mock server prioritizes **consistent, reproducible testing**:
- ✅ Developers can always test booking flow (any route except XXX)
- ✅ Easy to test "no results" scenario (use XXX airport code)
- ✅ CI/CD tests are stable and predictable
- ✅ No dependency on external API availability
- ✅ No IP whitelisting requirements
- ✅ Fast response times (no network latency)
- ✅ No code changes or restarts needed to switch between scenarios

## Testing Scenarios

### Scenario 1: Happy Path (Complete Booking Flow)
```bash
# 1. Search flights
SEARCH_RESPONSE=$(curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{"origin":"AMS","destination":"LHR","departure_date":"2025-11-15","adults":1}')

# 2. Extract session_id and first fare_source_code
SESSION_ID=$(echo $SEARCH_RESPONSE | jq -r '.AirSearchResponse.session_id')
FARE_CODE=$(echo $SEARCH_RESPONSE | jq -r '.AirSearchResponse.AirSearchResult.FareItineraries[0].AirItineraryFareInfo.FareSourceCode')

# 3. Book flight
curl -X POST http://localhost:8002/api/aeroVE5/booking \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"fare_source_code\":\"$FARE_CODE\",\"passengers\":[{\"name\":\"Test User\"}]}"
```

### Scenario 2: Session ID Mismatch (Reproduce Bug)
```bash
# Search to get valid session
SEARCH_RESPONSE=$(curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{"origin":"AMS","destination":"LHR","departure_date":"2025-11-15","adults":1}')

FARE_CODE=$(echo $SEARCH_RESPONSE | jq -r '.AirSearchResponse.AirSearchResult.FareItineraries[0].AirItineraryFareInfo.FareSourceCode')

# Try to book with WRONG session_id (simulates the production bug)
curl -X POST http://localhost:8002/api/aeroVE5/booking \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"WRONG_SESSION_ID\",\"fare_source_code\":\"$FARE_CODE\",\"passengers\":[{\"name\":\"Test\"}]}"

# Expected: HTTP 400 with "Invalid session_id" error
```

### Scenario 3: Invalid Fare Code
```bash
# Valid session, but invalid fare code
SESSION_ID=$(echo $SEARCH_RESPONSE | jq -r '.AirSearchResponse.session_id')

curl -X POST http://localhost:8002/api/aeroVE5/booking \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"fare_source_code\":\"INVALID_FARE_CODE\",\"passengers\":[{\"name\":\"Test\"}]}"

# Expected: HTTP 400 with "Invalid fare_source_code" error
```

## Debugging with Mock Server

### View Request Logs
The server logs all incoming requests and responses:

```
2025-10-10 12:34:56 - INFO - → POST /api/aeroVE5/availability
2025-10-10 12:34:56 - INFO - Search request: {'origin': 'AMS', 'destination': 'LHR', ...}
2025-10-10 12:34:56 - INFO - Generated session_id: MOCK_SESSION_20251010123456
2025-10-10 12:34:56 - INFO - Returning 3 mock flights
2025-10-10 12:34:56 - INFO - ← 200 (0.012s)
```

### Reproduce Production Bug Locally

The mock server helps reproduce the session_id collision bug:

1. **Search** returns `session_id: "MOCK_SESSION_123"`
2. **Backend** stores this in `search_params["session_id"]`
3. **User selects flight** → Backend should pass `MOCK_SESSION_123` to booking
4. **Bug**: If `search_params["session_id"]` was overwritten with chat session ID, booking fails

Use the mock server to test the fix:
- Verify `search_params["flightlogic_session_id"]` is used correctly
- Ensure booking endpoint receives correct session token
- Validate error messages match expected format

## Integration with Backend

The backend's FlightLogic client (`integrations/flightlogic/client.py`) works with the mock server without code changes:

```python
# In .env
FLIGHTLOGIC_API_URL=http://localhost:8002/api/aeroVE5

# Backend code remains the same
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{settings.FLIGHTLOGIC_API_URL}/availability",
        json=search_params
    )
    # Works with both mock and production API
```

## Multi-Segment Flight Examples

### Example 1: Round Trip with 1 Stop

**Request**:
```json
{
  "origin": "LHR",
  "destination": "AMS",
  "departure_date": "2026-02-20",
  "return_date": "2026-03-10",
  "adults": 1
}
```

**Response Structure** (British Airways option):
```json
{
  "FareItinerary": {
    "DirectionInd": "Return",
    "OriginDestinationOptions": [
      {
        "OriginDestinationOption": [
          {
            "FlightSegment": {
              "DepartureAirportLocationCode": "LHR",
              "ArrivalAirportLocationCode": "FRA"
            },
            "StopQuantity": 1,
            "StopQuantityInfo": {
              "LocationCode": "FRA",
              "Duration": "1h 0m"
            }
          },
          {
            "FlightSegment": {
              "DepartureAirportLocationCode": "FRA",
              "ArrivalAirportLocationCode": "AMS"
            },
            "StopQuantity": 0
          }
        ],
        "TotalStops": 1
      },
      {
        "OriginDestinationOption": [
          {
            "FlightSegment": {
              "DepartureAirportLocationCode": "AMS",
              "ArrivalAirportLocationCode": "LHR"
            },
            "StopQuantity": 0
          }
        ],
        "TotalStops": 0
      }
    ]
  }
}
```

### Example 2: One-Way Direct Flight

**Request**:
```json
{
  "origin": "AMS",
  "destination": "LHR",
  "departure_date": "2026-01-14",
  "adults": 1
}
```

**Response Structure** (KLM option):
```json
{
  "FareItinerary": {
    "DirectionInd": "OneWay",
    "OriginDestinationOptions": [
      {
        "OriginDestinationOption": [
          {
            "FlightSegment": {
              "DepartureAirportLocationCode": "AMS",
              "ArrivalAirportLocationCode": "LHR"
            },
            "StopQuantity": 0
          }
        ],
        "TotalStops": 0
      }
    ]
  }
}
```

### Hub Airports for Layovers

The mock uses these hub airports for intermediate stops:

| Code | City | Airport Name |
|------|------|--------------|
| FRA | Frankfurt | Frankfurt Airport |
| CDG | Paris | Charles de Gaulle Airport |
| MAD | Madrid | Madrid-Barajas Airport |
| FCO | Rome | Rome Fiumicino Airport |
| MUC | Munich | Munich Airport |
| ZRH | Zurich | Zurich Airport |

## Limitations

- **In-Memory Sessions**: Sessions are lost when server restarts
- **No Rate Limiting**: Unlike production API
- **Simplified Responses**: Mock data is simplified for testing
- **No Authentication**: API key validation not implemented
- **Fixed Flight Data**: Always returns same 3 flights for any search

## Development Notes

- **File**: `tests/mocks/flightlogic/server.py` (272 lines)
- **Mock Data**: `tests/mocks/flightlogic/mock_data.py` (300 lines)
- **Framework**: FastAPI with uvicorn
- **Port**: 8002 (default, configurable)
- **Logging**: INFO level with request/response details

## Next Steps

1. **Test Mock Server**: `python -m tests.mocks.flightlogic.server`
2. **Update .env**: Point `FLIGHTLOGIC_API_URL` to mock
3. **Run Backend**: `uvicorn app.main:app --reload`
4. **Test Booking Flow**: Use frontend or API calls
5. **Reproduce Bug**: Test session_id collision scenario
6. **Apply Fix**: Update `enhanced_flight_handler.py` to use `flightlogic_session_id`
7. **Verify Fix**: Retest with mock server

---

## Related Documentation

- **Docker Integration**: [docs/docker-mock-server.md](../../../../docs/docker-mock-server.md)

---

**Status**: Mock server ready for testing (multi-segment and round-trip support added January 2026)
**Use Case**: Test complete flight booking flow with realistic multi-segment data
**Last Updated**: January 2026
