# FlightLogic API - Local Development Guide

## Problem

FlightLogic API uses IP whitelisting for security. Only requests from whitelisted IPs (like staging NAT gateway: `98.89.125.207`) are allowed. Local developers with non-whitelisted IPs cannot test directly.

## Solution: X-Forwarded-For Header Spoofing

FlightLogic trusts the `X-Forwarded-For` HTTP header for IP validation. We can spoof this header locally to bypass IP whitelisting.

### Architecture

```
Local Backend (Python) → FlightLogic API
    ↓
Sets X-Forwarded-For: 98.89.125.207 (whitelisted NAT gateway IP)
```

## Quick Start

### 1. Configure Environment Variables

Edit `.env` in project root:

```bash
# FlightLogic API Configuration
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
FLIGHTLOGIC_USER_ID=myvoya_testAPI
FLIGHTLOGIC_PASSWORD=<get from AWS Secrets Manager>
FLIGHTLOGIC_ACCESS_TYPE=Test
FLIGHTLOGIC_IP_ADDRESS=98.89.125.207  # Used in request body
FLIGHTLOGIC_SPOOF_IP=98.89.125.207    # Used in X-Forwarded-For header
```

**Get password from AWS:**
```bash
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD \
  --query SecretString \
  --output text \
  --profile voya-poweruser
```

### 2. Start Backend with Environment Variables

**Important**: Docker Compose needs environment variables sourced before running:

```bash
# Source .env and start backend
set -a && source .env && set +a && docker compose up -d backend
```

**Or create a convenience script** (`scripts/start-dev.sh`):
```bash
#!/bin/bash
set -a
source .env
set +a
docker compose up -d "$@"
```

### 3. Verify Configuration

```bash
# Check environment variables loaded correctly
docker compose exec backend env | grep FLIGHTLOGIC

# Expected output:
# FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
# FLIGHTLOGIC_USER_ID=myvoya_testAPI
# FLIGHTLOGIC_PASSWORD=myvoyaTest@2025
# FLIGHTLOGIC_IP_ADDRESS=98.89.125.207
# FLIGHTLOGIC_SPOOF_IP=98.89.125.207
```

### 4. Test Flight Search

```bash
curl -X POST http://localhost:8000/api/flights/search \
  -H "Content-Type: application/json" \
  -d '{
    "journey_type": "OneWay",
    "origin_destination_info": [{
      "departure_date": "2025-12-15",
      "origin_airport": {"iata_code": "JNB", "name": "Johannesburg"},
      "destination_airport": {"iata_code": "CPT", "name": "Cape Town"}
    }],
    "cabin_class": "Economy",
    "adults": 1,
    "children": 0,
    "infants": 0
  }' | jq '{flights: (.fare_itineraries | length), session_id, error: (.errors[0].message // "none")}'
```

**Expected response:**
```json
{
  "flights": 32,
  "session_id": "MTc2Mjk2NjYwMV8yMjg2OTAw",
  "error": "none"
}
```

## How It Works

### 1. Configuration (`app/core/config.py`)

Added new environment variable for IP spoofing:

```python
FLIGHTLOGIC_SPOOF_IP: str | None = Field(
    default=None,
    description="IP address to spoof in X-Forwarded-For header (for local development bypassing IP whitelist)",
)
```

### 2. FlightLogic Client (`integrations/flightlogic/client.py`)

Modified `_make_request()` to conditionally add header:

```python
headers = {
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
}

# Add X-Forwarded-For header if spoofing IP is configured (for local dev)
if settings.FLIGHTLOGIC_SPOOF_IP:
    headers["X-Forwarded-For"] = settings.FLIGHTLOGIC_SPOOF_IP
```

### 3. Docker Compose Configuration

Updated `compose.dev.yaml` to pass through new environment variables:

```yaml
environment:
  - FLIGHTLOGIC_IP_ADDRESS=${FLIGHTLOGIC_IP_ADDRESS:-}
  - FLIGHTLOGIC_SPOOF_IP=${FLIGHTLOGIC_SPOOF_IP:-}
```

## Why Two IP Variables?

1. **`FLIGHTLOGIC_IP_ADDRESS`**: Used in request body `ip_address` field (FlightLogic API requirement)
2. **`FLIGHTLOGIC_SPOOF_IP`**: Used in `X-Forwarded-For` header (bypasses IP whitelist)

Both should be set to `98.89.125.207` (staging NAT gateway IP) for local development.

## Switching Between Mock and Real API

### Use Mock Server (Default)

```bash
# Comment out or remove these from .env:
# FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
# FLIGHTLOGIC_SPOOF_IP=98.89.125.207

# Or explicitly use mock:
FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5
FLIGHTLOGIC_USER_ID=mock_user
FLIGHTLOGIC_PASSWORD=mock_password
FLIGHTLOGIC_SPOOF_IP=  # Leave empty

docker compose up -d
```

### Use Real API (with IP spoofing)

```bash
# Set in .env:
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
FLIGHTLOGIC_USER_ID=myvoya_testAPI
FLIGHTLOGIC_PASSWORD=<from secrets manager>
FLIGHTLOGIC_IP_ADDRESS=98.89.125.207
FLIGHTLOGIC_SPOOF_IP=98.89.125.207

# Start with env vars sourced
set -a && source .env && set +a && docker compose up -d backend
```

## Troubleshooting

### "Invalid ip_address supplied" Error

```json
{
  "errors": [{
    "code": "FLSEARCHVAL",
    "message": "Invalid ip_address supplied (You are hitting the API from 188.90.163.183 and passing 127.0.0.1, which is not whitelisted in our system)."
  }]
}
```

**Cause**: Environment variables not loaded correctly.

**Fix**:
```bash
# Verify env vars in container
docker compose exec backend env | grep FLIGHTLOGIC

# If FLIGHTLOGIC_SPOOF_IP is missing:
set -a && source .env && set +a && docker compose up -d --force-recreate backend
```

### "Authentication failed" Error

**Cause**: Wrong credentials or expired password.

**Fix**: Get fresh password from AWS Secrets Manager:
```bash
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD \
  --query SecretString \
  --output text \
  --profile voya-poweruser
```

### Backend Not Picking Up .env Changes

**Cause**: Docker Compose caches environment variables.

**Fix**: Force recreate container:
```bash
set -a && source .env && set +a && docker compose up -d --force-recreate backend
```

## Alternative: nginx Proxy (Legacy/Debugging)

For debugging HTTP traffic, an nginx reverse proxy is deployed on ECS that also spoofs the X-Forwarded-For header. See `docs/FLIGHTLOGIC_PROXY.md` for details.

**When to use proxy:**
- Debugging HTTP requests/responses
- Inspecting headers and payloads
- Troubleshooting FlightLogic API issues

**For normal local development, use X-Forwarded-For spoofing instead** (simpler, no proxy needed).

## Security Notes

### Development Only

⚠️ **X-Forwarded-For spoofing should ONLY be used for local development**

- **Never deploy to production** with `FLIGHTLOGIC_SPOOF_IP` set
- Production should use actual whitelisted IPs (ECS NAT gateway)
- Staging ECS tasks do NOT need spoofing (already use NAT gateway)

### How It Works in Staging/Production

Staging and production ECS tasks are deployed in **private subnets** and route outbound traffic through a **NAT gateway** (`98.89.125.207`), which is whitelisted by FlightLogic. No header spoofing needed.

```
ECS Task (private subnet) → NAT Gateway (98.89.125.207) → FlightLogic API
                                   ↑
                             (whitelisted IP)
```

### Configuration by Environment

| Environment | IP Spoofing | Why |
|-------------|-------------|-----|
| **Local Dev** | ✅ Enabled (`FLIGHTLOGIC_SPOOF_IP=98.89.125.207`) | Bypass IP whitelist |
| **Staging** | ❌ Disabled | Routes through NAT gateway automatically |
| **Production** | ❌ Disabled | Routes through NAT gateway automatically |

## FlightLogic API Credentials

### Staging/Test Environment

- **User ID**: `myvoya_testAPI`
- **Password**: Stored in AWS Secrets Manager (`staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD`)
- **Access Type**: `Test`
- **Whitelisted IP**: `98.89.125.207` (staging NAT gateway)
- **Base URL**: `https://travelnext.works/api/aeroVE5`

### Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `/availability` | Flight search |
| `/fareRules` | Get fare rules |
| `/revalidate` | Revalidate fare |
| `/booking` | Create booking |
| `/issueTicket` | Issue ticket |
| `/cancelBooking` | Cancel booking |
| `/extraServices` | Get extra services |
| `/tripDetails` | Get trip details |

## Additional Resources

- **FlightLogic API docs**: `dev-tools/extern/flightlogic_apis/`
- **Field definitions**: `dev-tools/docs/flightlogic-field-definitions.md`
- **Backend client code**: `backend_python/integrations/flightlogic/client.py`
- **Proxy debugging guide**: `docs/FLIGHTLOGIC_PROXY.md` (optional, for debugging)

---

**Last Updated**: November 2025
**Maintainer**: DevOps Team
