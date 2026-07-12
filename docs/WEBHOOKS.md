# Stripe Webhook Integration Guide

Complete guide to Stripe webhook setup, testing, and event handling for the Voya payment system.

## Table of Contents
- [Overview](#overview)
- [Webhook Implementation](#webhook-implementation)
- [Environment Configuration](#environment-configuration)
- [Local Testing with ngrok](#local-testing-with-ngrok)
- [Testing with Stripe CLI](#testing-with-stripe-cli)
- [Testing with Stripe Dashboard](#testing-with-stripe-dashboard)
- [Event Handlers Reference](#event-handlers-reference)
- [Troubleshooting](#troubleshooting)
- [Testing Tools](#testing-tools)

## Overview

Stripe webhooks allow the Voya backend to receive real-time notifications about payment events (successful payments, failed charges, transfers, etc.).

**Why Webhooks?**
- **Real-time updates**: Get notified immediately when payment status changes
- **Reliability**: Stripe retries failed webhook deliveries automatically
- **Security**: Webhook signatures prevent spoofed requests
- **Async processing**: Handle long-running operations without blocking user requests

**Webhook Endpoint**: `POST /webhooks/stripe`
**Location**: `app/api/webhooks.py`
**Events Handled**: 8 event types (payment_intent.*, charge.*, transfer.*, account.*)

## Webhook Implementation

### Endpoint Overview

**Path**: `/webhooks/stripe` (no `/api` prefix for Stripe compatibility)

**Features**:
- ✅ Signature verification with `STRIPE_WEBHOOK_SECRET`
- ✅ 8 event handlers with comprehensive logging
- ✅ Transaction status updates in MongoDB
- ✅ Error handling and retry logic
- ✅ Email confirmation triggers (pending implementation)

**Implementation** (`app/api/webhooks.py`):
```python
@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> dict[str, Any]:
    """Handle Stripe webhook events."""
    payload = await request.body()

    # Verify webhook signature
    if webhook_secret and stripe_signature:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    else:
        # Testing mode: no signature verification
        event = json.loads(payload)

    # Extract event details
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    # Route to appropriate handler
    if event_type == "payment_intent.succeeded":
        await handle_payment_intent_succeeded(event_data)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_intent_failed(event_data)
    # ... 6 more event types

    return {"status": "success", "event_id": event_id, "event_type": event_type}
```

### Event Handlers

All event handlers follow the pattern:
```python
async def handle_event_name(event_data: dict[str, Any]) -> None:
    """Handle event - update database, send emails, etc."""
    logger.info(f"Processing {event_type}: {event_data.get('id')}")

    # Business logic here
    # - Update MongoDB transaction status
    # - Send email notifications
    # - Trigger other async operations

    logger.info(f"✅ {event_type} processed successfully")
```

### Signature Verification

**Purpose**: Prevent spoofed webhook requests

**How it works**:
1. Stripe signs each webhook with `STRIPE_WEBHOOK_SECRET`
2. Backend verifies signature using `stripe.Webhook.construct_event()`
3. Rejects requests with invalid/missing signatures

**Implementation**:
```python
try:
    event = stripe.Webhook.construct_event(
        payload, stripe_signature, webhook_secret
    )
    logger.info("✅ Webhook signature verified")
except ValueError:
    raise HTTPException(400, "Invalid payload")
except stripe.error.SignatureVerificationError:
    raise HTTPException(400, "Invalid signature")
```

## Environment Configuration

### Required Environment Variables

**Backend** (`.env`):
```bash
# Stripe webhook signing secret
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe API keys (also needed for payment processing)
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_PUBLISHABLE_KEY=pk_test_51...
```

### Getting Webhook Secret

**For Local Testing** (ngrok):
1. Create local webhook endpoint (see [Local Testing with ngrok](#local-testing-with-ngrok))
2. Go to https://dashboard.stripe.com/test/webhooks
3. Find the webhook you just created (newest one)
4. Click "Reveal" next to "Signing secret"
5. Copy secret (starts with `whsec_`)

**For Production**:
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click webhook `we_1SIq7vPD9V3ngpzahipuQDNL` (production endpoint)
3. Click "Reveal" next to "Signing secret"
4. Copy secret

**Add to .env**:
```bash
# Edit .env file
nano .env

# Add this line:
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
```

**Restart Backend** to load new secret:
```bash
# Docker
docker restart voya-backend

# Local development
# Ctrl+C to stop, then:
uvicorn app.main:app --reload --port 8000
```

## Local Testing with ngrok

ngrok creates a secure tunnel from a public URL to your local backend, allowing Stripe to deliver webhooks during development.

### Quick Start with Docker Compose (Recommended)

**Step 1: Add ngrok auth token to .env** (REQUIRED for Docker)
```bash
# ngrok requires authentication (as of 2025)
# Get token from https://dashboard.ngrok.com/get-started/your-authtoken
# Add to .env:
NGROK_AUTH_TOKEN=your_token_here
```

**Note**: The auth token is required when running ngrok in Docker because containers don't have access to your local ngrok config (`~/.config/ngrok/ngrok.yml`). Without it, you'll get `ERR_NGROK_4018`. See [Troubleshooting](#ngrok-authentication-failed-err_ngrok_4018).

**Step 2: Start all services including ngrok**
```bash
docker compose up -d
```

The ngrok service automatically:
- Creates a tunnel to the backend service
- Provides a public URL for webhooks
- Runs the ngrok dashboard at http://localhost:4040

**Step 3: Get your public URL**

Option A - Open ngrok dashboard:
```bash
# Visit in browser
http://localhost:4040
```

Option B - Use curl:
```bash
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
```

You'll get a URL like: `https://abc123.ngrok-free.app`

**Step 4: Create Stripe webhook endpoint**

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "+ Add endpoint"
3. Endpoint URL: `https://YOUR-NGROK-URL/webhooks/stripe`
4. Select events to listen to:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.succeeded`
   - `charge.failed`
   - `transfer.created`
   - `transfer.updated`
   - `account.updated`
   - `account.application.deauthorized`
5. Click "Add endpoint"

**Step 5: Update webhook secret in .env**
```bash
# Copy the signing secret from Stripe dashboard
# Update .env:
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
```

**Step 6: Restart backend to load new secret**
```bash
docker compose restart backend
```

**Step 7: Test webhook delivery**

Make a test payment and watch:

1. **Backend logs**:
```bash
docker compose logs -f backend
# You'll see:
💰 Payment succeeded: pi_xxx
   Amount: $100.00
✅ Webhook processed successfully
```

2. **ngrok dashboard** - http://localhost:4040 shows all HTTP requests

3. **Stripe dashboard** - https://dashboard.stripe.com/test/webhooks shows delivery status

**Note**: When ngrok restarts (URL changes), use the automated script:
```bash
./backend_python/scripts/update-webhook-url.sh
docker compose restart backend
```

### Alternative: Manual ngrok Setup (Without Docker)

If you prefer to run ngrok outside Docker (uses local ngrok config instead of .env):

**Step 1: Install ngrok** (if not installed)
```bash
# Download ngrok
cd ~
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Verify installation
ngrok version

# Authenticate (REQUIRED as of 2025)
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

**Note**: This method stores the auth token in `~/.config/ngrok/ngrok.yml`, which is accessible to the ngrok CLI but not to Docker containers. For Docker deployments, use the Docker Compose method above.

**Step 2: Start your backend**
```bash
cd backend_python
uvicorn app.main:app --reload --port 8000
```

**Step 3: Start ngrok** (in another terminal)
```bash
ngrok http 8000
```

**Step 4: Configure webhook endpoint** in Stripe dashboard:
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "+ Add endpoint"
3. Endpoint URL: `https://YOUR-NGROK-URL/webhooks/stripe`
4. Select events: payment_intent.*, charge.*, transfer.*, account.*
5. Click "Add endpoint"
6. Copy the webhook signing secret
7. Add to `.env`: `STRIPE_WEBHOOK_SECRET=whsec_...`
8. Restart backend

## Testing with Stripe CLI

The Stripe CLI provides the easiest local webhook testing without ngrok.

### Installation

**Ubuntu/Debian**:
```bash
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee -a /etc/apt/sources.list.d/stripe.list
sudo apt update
sudo apt install stripe
```

**Verify Installation**:
```bash
stripe --version
```

### Authentication

```bash
stripe login
# Follow the prompts to authenticate with your Stripe account
```

### Forward Webhooks to Local Server

```bash
# Start your backend first
uvicorn app.main:app --reload --port 8000

# In another terminal, forward webhooks
stripe listen --forward-to localhost:8000/webhooks/stripe
```

**Output**:
```
> Ready! Your webhook signing secret is whsec_...
> Listening for events...
```

**Add secret to .env**:
```bash
# Copy the signing secret from output
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Restart backend** to load new secret.

### Trigger Test Events

```bash
# In another terminal
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
stripe trigger charge.succeeded
stripe trigger charge.failed
stripe trigger transfer.created
```

**Advantages of Stripe CLI**:
- ✅ No ngrok needed
- ✅ Automatic secret generation
- ✅ Easy event triggering
- ✅ Real-time event streaming

## Testing with Stripe Dashboard

Send test webhooks directly from Stripe dashboard (works for both local and production endpoints).

### Send Test Webhook

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click your webhook endpoint
3. Click "Send test webhook"
4. Select event type (e.g., `payment_intent.succeeded`)
5. Optionally edit JSON payload
6. Click "Send test webhook"

**Note**: For local testing, this only works if:
- You're using ngrok or Stripe CLI
- Your local backend is running
- Webhook endpoint is accessible from internet

### View Webhook Logs

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click your webhook endpoint
3. Scroll down to "Webhook attempts"
4. See delivery status, response code, and payload

**Successful delivery**:
- Status: ✅ `200 OK`
- Response body: `{"status":"success","event_id":"evt_xxx"}`

**Failed delivery**:
- Status: ❌ `400`, `404`, `500`
- Response body: Error details
- Retry schedule shown

## Event Handlers Reference

Voya handles 8 Stripe event types for comprehensive payment tracking.

### 1. payment_intent.succeeded

**Trigger**: Payment successfully completed

**Handler** (`handle_payment_intent_succeeded`):
- Updates transaction status to `SUCCEEDED` in MongoDB
- Records `paid_at` timestamp
- Stores `stripe_charge_id`
- Triggers confirmation email (TODO)

**Use case**: Primary success event for confirming booking payments

**Example log**:
```
💰 Payment succeeded: pi_3ABC123...
   Amount: $100.00
   Currency: USD
   Status: succeeded
✅ Transaction updated for VOYA-TEST-12345
```

### 2. payment_intent.payment_failed

**Trigger**: Payment failed (card declined, insufficient funds, etc.)

**Handler** (`handle_payment_intent_failed`):
- Logs failure details
- TODO: Update booking status to failed
- TODO: Send failure notification email

**Example log**:
```
❌ Payment failed: pi_3XYZ789...
   Amount: $100.00
   Last error: Your card was declined
```

### 3. charge.succeeded

**Trigger**: Charge successfully completed (after payment_intent.succeeded)

**Handler** (`handle_charge_succeeded`):
- Logs charge for reconciliation
- TODO: Update transaction records

**Use case**: Secondary confirmation, useful for reconciliation

### 4. charge.failed

**Trigger**: Charge failed (rare, usually payment_intent fails first)

**Handler** (`handle_charge_failed`):
- Logs failure message
- TODO: Implement retry logic or notification

### 5. transfer.created

**Trigger**: Transfer to supplier account created (Stripe Connect)

**Handler** (`handle_transfer_created`):
- Logs transfer details (amount, destination)
- TODO: Update payout records in MongoDB

**Use case**: Track when supplier payouts are initiated

**Example log**:
```
💸 Transfer created: tr_3DEF456...
   Amount: $95.00
   Destination: acct_1SIqFwAcjtxA6BLd
```

### 6. transfer.updated

**Trigger**: Transfer status changed (pending → paid, failed, etc.)

**Handler** (`handle_transfer_updated`):
- Logs status update
- TODO: Update transfer status in database

### 7. account.updated

**Trigger**: Stripe Connect account updated (capabilities, verification status)

**Handler** (`handle_account_updated`):
- Logs account changes
- TODO: Sync account capabilities
- TODO: Check verification status

### 8. account.application.deauthorized

**Trigger**: Supplier deauthorizes platform access

**Handler** (`handle_account_deauthorized`):
- Logs deauthorization
- TODO: Disable payment features for this account

## Troubleshooting

### Webhook Not Receiving Events

**Symptoms**: No logs in backend, no requests in ngrok dashboard

**Checks**:
1. Is backend running?
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Is ngrok running?
   ```bash
   curl http://localhost:4040/api/tunnels | python3 -m json.tool
   ```

3. Does webhook URL match ngrok public URL?
   - Check Stripe dashboard webhook URL
   - Compare with ngrok URL (shown in ngrok dashboard)

4. Is webhook endpoint enabled in Stripe?
   - Go to https://dashboard.stripe.com/test/webhooks
   - Check endpoint status is "Enabled"

### Signature Verification Failing

**Symptoms**: `400 Invalid signature` error

**Solutions**:

1. **Wrong secret**: Verify `STRIPE_WEBHOOK_SECRET` matches webhook endpoint
   ```bash
   # Check .env file
   cat .env | grep STRIPE_WEBHOOK_SECRET

   # Compare with Stripe dashboard secret
   # https://dashboard.stripe.com/test/webhooks → Click webhook → Reveal secret
   ```

2. **Backend not restarted**: Restart after adding secret
   ```bash
   # Docker
   docker restart voya-backend

   # Local
   # Ctrl+C, then restart uvicorn
   ```

3. **Using wrong webhook**: If you created multiple webhooks, make sure secret matches the active one
   ```bash
   # List all webhooks
   python test_webhook_setup.py list-webhooks
   ```

### ngrok Authentication Failed (ERR_NGROK_4018)

**Symptoms**: ngrok container stuck in restart loop with error:
```
ERROR: authentication failed: Usage of ngrok requires a verified account and authtoken.
ERR_NGROK_4018
```

**Cause**: ngrok now requires authentication even for free tier usage.

**Solution**:

1. **Get ngrok auth token**:
   - Visit https://dashboard.ngrok.com/get-started/your-authtoken
   - Sign up or log in to ngrok
   - Copy your auth token

2. **Add to .env file**:
   ```bash
   # Add this line to .env
   NGROK_AUTH_TOKEN=your_token_here
   ```

3. **Ensure Docker Compose passes token correctly**:
   ```yaml
   # compose.dev.yaml should have:
   ngrok:
     command:
       - "http"
       - "backend:80"
       - "--authtoken=${NGROK_AUTH_TOKEN:-}"
   ```

4. **Restart ngrok**:
   ```bash
   docker compose up -d ngrok
   ```

5. **Verify it's running**:
   ```bash
   docker compose ps ngrok
   curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
   ```

### ngrok Tunnel Expired or URL Changed

**Symptoms**: Webhook delivery fails after ngrok restart (URL changed)

**Solution**: Use automated script (recommended)

```bash
# Automated update script
./backend_python/scripts/update-webhook-url.sh

# Then restart backend
docker compose restart backend
```

**Manual alternative**:
```bash
# Get new ngrok URL
NEW_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

# Update webhook
stripe webhook_endpoints update we_1SJfsKPD9V3ngpza4LdY8VLF \
  --url "$NEW_URL/webhooks/stripe"

# Restart backend
docker compose restart backend
```

**Note**: Free tier ngrok URLs change on every restart. The automated script handles the entire update process.

### Backend Returning 404

**Symptoms**: Webhook delivery shows `404 Not Found`

**Checks**:

1. Is webhook router registered in `main.py`?
   ```python
   # app/main.py should have:
   from app.api.webhooks import router as webhooks_router
   app.include_router(webhooks_router)
   ```

2. Is path correct? Should be `/webhooks/stripe` (NOT `/api/webhooks/stripe`)

3. Test directly:
   ```bash
   curl -X POST http://localhost:8000/webhooks/stripe \
     -H "Content-Type: application/json" \
     -d '{"type":"test.event","data":{"object":{}}}'
   ```

### Event Handler Errors

**Symptoms**: Webhook received but processing fails

**Debug**:

1. Check backend logs for exceptions:
   ```bash
   docker logs -f voya-backend | grep ERROR

   # Or in local development, check terminal output
   ```

2. Check specific event handler logic in `app/api/webhooks.py`

3. Test event handler directly:
   ```python
   # In Python console
   from app.api.webhooks import handle_payment_intent_succeeded
   test_data = {"id": "pi_test", "amount": 10000, "currency": "usd"}
   await handle_payment_intent_succeeded(test_data)
   ```

### MongoDB Connection Issues

**Symptoms**: `Transaction update failed` in logs

**Solution**: Verify MongoDB connection
```bash
# Check MongoDB is running
docker ps | grep mongo

# Test connection
python -c "from app.database.connection import test_connection; import asyncio; asyncio.run(test_connection())"
```

## Testing Tools

### Docker Compose (Recommended)

The ngrok service is integrated into Docker Compose for easy webhook testing:

```bash
# Start all services including ngrok
docker compose up -d

# Get ngrok public URL
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'

# Update Stripe webhook with new ngrok URL (when ngrok restarts)
./backend_python/scripts/update-webhook-url.sh

# View ngrok dashboard
open http://localhost:4040  # macOS
xdg-open http://localhost:4040  # Linux

# Watch webhook requests in real-time
docker compose logs -f backend | grep WEBHOOK

# Restart services after updating .env
docker compose restart backend
```

### Webhook Management via Stripe CLI

The Stripe CLI provides powerful webhook management capabilities, especially useful for updating webhook URLs when ngrok restarts.

#### Installation

**Ubuntu/Debian**:
```bash
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee /etc/apt/sources.list.d/stripe.list
sudo apt update && sudo apt install stripe
```

**Verify installation**:
```bash
stripe --version
```

#### Authentication

```bash
stripe login
# Follow the prompts to authenticate with your Stripe account
```

#### Common Webhook Operations

**List all webhook endpoints**:
```bash
stripe webhook_endpoints list
```

**Update webhook URL** (useful when ngrok restarts):
```bash
# Get current ngrok URL
NEW_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

# Update local dev webhook (ID: we_1SJfsKPD9V3ngpza4LdY8VLF)
stripe webhook_endpoints update we_1SJfsKPD9V3ngpza4LdY8VLF \
  --url "$NEW_URL/webhooks/stripe"
```

**Create new webhook endpoint**:
```bash
stripe webhook_endpoints create \
  --url https://YOUR-NGROK-URL/webhooks/stripe \
  --enabled-events payment_intent.succeeded,payment_intent.payment_failed,charge.succeeded,charge.failed,transfer.created,transfer.updated
```

**Delete webhook endpoint**:
```bash
stripe webhook_endpoints delete <webhook-id>
```

**Automated ngrok URL Update Script**:

Available at `backend_python/scripts/update-webhook-url.sh`

```bash
# Run the script when ngrok URL changes
./backend_python/scripts/update-webhook-url.sh

# Restart backend to apply changes
docker compose restart backend
```

The script automatically:
- ✅ Gets new ngrok URL from http://localhost:4040
- ✅ Updates Stripe webhook endpoint (`we_1SJfsKPD9V3ngpza4LdY8VLF`)
- ✅ Provides error messages if ngrok/Stripe CLI not available
- ✅ Shows verification steps

## Production Webhook Configuration

**Production Webhook** (already configured):
- **ID**: `we_1SIq7vPD9V3ngpzahipuQDNL`
- **URL**: `https://app.myvoya.ai/webhooks/stripe`
- **Status**: Enabled
- **Events**: 8 events configured

**Getting Production Secret**:
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click `we_1SIq7vPD9V3ngpzahipuQDNL`
3. Click "Reveal" next to "Signing secret"
4. Add to production `.env`: `STRIPE_WEBHOOK_SECRET=whsec_...`
5. Deploy updated backend to production

## Related Documentation

- **[PAYMENTS.md](PAYMENTS.md)** - Complete payment integration guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture with payment flow
- **[FRONTEND_BACKEND_COLLABORATION.md](FRONTEND_BACKEND_COLLABORATION.md)** - API patterns
- **Stripe Webhooks Dashboard**: https://dashboard.stripe.com/test/webhooks
- **Stripe Events Log**: https://dashboard.stripe.com/test/events
- **Stripe Webhook Docs**: https://stripe.com/docs/webhooks

---

**Last Updated**: October 2025
**Maintainer**: Backend Team
**Questions**: Create GitHub issue with label `webhooks`
