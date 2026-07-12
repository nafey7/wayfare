# FlightLogic Mock Server - Docker Integration

The FlightLogic mock server is **included by default** in the development environment for easy local testing without hitting the real FlightLogic API.

## Quick Start

### Default Development (Mock API Included)

```bash
# Start all services including mock FlightLogic API
docker compose up -d

# Check services are running
docker compose ps

# View mock server logs
docker compose logs -f flightlogic-mock

# Stop all services
docker compose down
```

That's it! The mock server is automatically configured and ready to use.

## Docker Compose Architecture

The project uses a modular compose file structure:

```
compose.yaml              # Convenience file (includes compose.dev.yaml)
├── compose.dev.yaml      # Complete dev stack (all services)
└── compose.test.yaml     # Test environment (hardcoded ports, fully isolated)
```

### File Breakdown

**`compose.dev.yaml`** - Complete Development Stack:
- MongoDB (port 27017)
- Mongo Express (port 8081)
- Frontend (port 3000)
- Backend (port 8000) - **Automatically configured to use mock server**
- MailHog (port 8025)
- FlightLogic Mock Server (port 8002)
- n8n (port 5678)
- ngrok (port 4040)

**`compose.test.yaml`** - Isolated Test Environment:
- All ports hardcoded to avoid conflicts with dev (3001, 8001, 27018, etc.)
- Can run simultaneously with dev environment

**`compose.yaml`** - Convenience:
- Includes `compose.dev.yaml`
- Single command: `docker compose up -d`

## Service URLs

When running `docker compose up -d`:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | React application |
| Backend API | http://localhost:8000/api | FastAPI endpoints |
| API Docs | http://localhost:8000/api/docs | Swagger/OpenAPI |
| MongoDB | localhost:27017 | Database |
| Mongo Express | http://localhost:8081 | Database UI |
| MailHog | http://localhost:8025 | Email testing UI |
| Mock FlightLogic | http://localhost:8002 | Mock API server |
| Mock API Docs | http://localhost:8002/docs | Mock API Swagger |

## Configuration

### Backend Automatically Uses Mock

In `compose.dev.yaml`, the backend is pre-configured to use the mock server:

```yaml
environment:
  - FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5
  - FLIGHTLOGIC_ACCESS_TYPE=Test
  - FLIGHTLOGIC_API_KEY=mock-api-key
```

No manual configuration needed!

### Override to Use Real FlightLogic API

If you need to test against the real API:

```bash
# Option 1: Environment variable override
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5 \
FLIGHTLOGIC_API_KEY=your-real-key \
  docker compose up -d backend

# Option 2: Edit backend_python/.env
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
FLIGHTLOGIC_API_KEY=your-real-key
docker compose up -d
```

## Testing Scenarios

### Scenario 1: Default Development Workflow

```bash
# 1. Start all services (includes mock API)
docker compose up -d

# 2. Open frontend
open http://localhost:3000

# 3. Test flight booking
#    - Search: "Amsterdam to London"
#    - Backend automatically calls mock server
#    - Returns 3 mock flights
#    - Select and book a flight

# 4. Check mock server handled the requests
docker compose logs flightlogic-mock
```

### Scenario 2: Test Against Real FlightLogic API

```bash
# Stop services
docker compose down

# Start with real API
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5 \
FLIGHTLOGIC_API_KEY=your-key \
  docker compose up -d

# Test booking flow with real data
```

### Scenario 3: Reproduce Production Bug

```bash
# Mock server validates session relationships
# View backend logs to see session_id handling
docker compose logs -f backend

# View mock server validation
docker compose logs -f flightlogic-mock

# If backend passes wrong session_id, mock returns:
# HTTP 400: "Invalid session_id or fare_source_code"
```

## Advanced Usage

### Start Specific Services

```bash
# Start only database and mock server
docker compose up -d mongodb flightlogic-mock

# Run backend locally (connects to containerized mock)
cd backend_python
uvicorn app.main:app --reload --port 8000
```

### Use Different Compose Files

```bash
# Development (default)
docker compose up -d

# Testing environment (separate database, different ports)
docker compose -f compose.test.yaml up -d

# Run both simultaneously (no port conflicts)
docker compose up -d && docker compose -f compose.test.yaml up -d
```

### Rebuild Mock Server

```bash
# After changing mock server code
docker compose build flightlogic-mock
docker compose up -d flightlogic-mock

# Force rebuild without cache
docker compose build --no-cache flightlogic-mock
```

## Environment Variables

Control services via environment variables or `.env` file:

```bash
# Port configuration
FRONTEND_PORT=3000
BACKEND_PORT=8000
MONGODB_PORT=27017
FLIGHTLOGIC_MOCK_PORT=8002

# FlightLogic configuration
FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5  # Mock (default)
# FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5    # Real API
FLIGHTLOGIC_ACCESS_TYPE=Test
FLIGHTLOGIC_API_KEY=mock-api-key

# Database
DATABASE_NAME=voya_dev
MONGODB_URI=mongodb://mongodb:27017
```

## Troubleshooting

### Mock Server Not Starting

```bash
# Check logs
docker compose logs flightlogic-mock

# Common issues:
# - Port 8002 already in use
# - Build failed (check Dockerfile)

# Rebuild and restart
docker compose build flightlogic-mock
docker compose up -d --force-recreate flightlogic-mock
```

### Backend Can't Reach Mock Server

```bash
# Verify services on same network
docker compose ps

# Check backend environment variables
docker compose exec backend env | grep FLIGHTLOGIC

# Should show:
# FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5

# Check network connectivity
docker compose exec backend ping flightlogic-mock
```

### Port Conflicts

```bash
# If port 8002 is in use
echo "FLIGHTLOGIC_MOCK_PORT=8003" >> .env
docker compose up -d

# Or stop conflicting service
lsof -ti:8002 | xargs kill -9
```

### View All Service Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f flightlogic-mock
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 flightlogic-mock
```

## Mock Server Endpoints

The mock server provides the same endpoints as the real FlightLogic API:

### GET /health
```bash
curl http://localhost:8002/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T12:34:56"
}
```

### POST /api/aeroVE5/availability (Flight Search)
```bash
curl -X POST http://localhost:8002/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "AMS",
    "destination": "LHR",
    "departure_date": "2025-11-15",
    "adults": 1
  }'
```

**Returns**: 3 mock flights (Best Value, Cheapest, Direct)

### POST /api/aeroVE5/booking (Create Booking)
```bash
curl -X POST http://localhost:8002/api/aeroVE5/booking \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "MOCK_SESSION_20251010123456",
    "fare_source_code": "MOCK_FARE_BEST_VALUE_123456",
    "passengers": [{"name": "John Doe"}]
  }'
```

**Validates**: session_id must match the session from search response

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start services with mock API
        run: docker compose up -d

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
          timeout 30 bash -c 'until curl -f http://localhost:8002/health; do sleep 2; done'

      - name: Run integration tests
        run: pytest backend_python/tests/integration_tests/

      - name: Check logs on failure
        if: failure()
        run: |
          docker compose logs backend
          docker compose logs flightlogic-mock
```

## When to Use Mock vs Real API

| Scenario | Use Mock | Use Real API |
|----------|----------|--------------|
| Local development | ✅ Default | ❌ |
| Unit tests | ✅ | ❌ |
| Integration tests | ✅ | ⚠️ Optional |
| Bug reproduction | ✅ | ❌ |
| Staging | ⚠️ Optional | ✅ |
| Production | ❌ | ✅ |

## Mock Server Features

✅ **Session Validation** - Enforces session_id → fare_source_code relationships
✅ **Request Logging** - Detailed logs for debugging
✅ **Health Checks** - Proper health monitoring
✅ **Automatic Startup** - Included in default dev environment
✅ **Network Isolation** - Runs in Docker network
✅ **Bug Reproduction** - Helps validate session_id collision fixes

## Related Documentation

- **Mock Server Details**: `backend_python/tests/mocks/flightlogic/README.md`
- **Mock Data Structure**: `backend_python/tests/mocks/README.md`
- **Production Bug Investigation**: `backend_python/CLAUDE.local.md`
- **Compose Files**:
  - `compose.yaml` - Convenience file (includes compose.dev.yaml)
  - `compose.dev.yaml` - Complete development stack
  - `compose.test.yaml` - Isolated test environment (hardcoded ports)

---

**Quick Commands**:

```bash
# Start everything (default includes mock server)
docker compose up -d

# View mock server logs
docker compose logs -f flightlogic-mock

# Test mock server health
curl http://localhost:8002/health

# Stop all services
docker compose down
```
