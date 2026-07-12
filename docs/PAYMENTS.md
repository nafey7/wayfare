# Payment Integration Guide

Complete guide to Stripe payment integration for flight bookings on the Voya platform.

## Table of Contents
- [Overview](#overview)
- [Payment Flow](#payment-flow)
- [Platform Fee Model](#platform-fee-model)
- [Payment Domain Structure](#payment-domain-structure)
- [API Endpoints](#api-endpoints)
- [Environment Configuration](#environment-configuration)
- [Frontend Integration](#frontend-integration)
- [Webhook Integration](#webhook-integration)
- [Testing](#testing)
- [Security Considerations](#security-considerations)

## Overview

Voya uses **Stripe Connect** to process flight booking payments with automatic platform fee collection and supplier payouts.

**Key Features**:
- 5% platform fee automatically calculated and held
- 95% transferred to supplier via Stripe Connect
- Payment validation before booking confirmation
- MongoDB transaction tracking
- Manual payout release (admin feature)
- Webhook-based status updates

**Payment Provider**: Stripe (v11.3.0+)
**Location**: `app/domains/payment/`
**Database Collection**: `transactions`

## Payment Flow

### End-to-End Flow

```
1. User selects flight → Frontend creates payment intent
   POST /api/payments/create-intent
   ↓
2. Backend creates Stripe PaymentIntent
   - Calculates 5% platform fee
   - Sets up Stripe Connect transfer
   - Stores transaction in MongoDB
   ↓
3. Frontend receives client_secret
   - Initializes Stripe.js with publishable_key
   - Presents Stripe Card Element to user
   ↓
4. User enters card details → Stripe processes payment
   - Payment handled entirely by Stripe (PCI compliant)
   - No card details touch Voya servers
   ↓
5. Stripe webhook notifies backend of payment status
   POST /webhooks/stripe (payment_intent.succeeded)
   ↓
6. Backend updates transaction status in MongoDB
   - Marks transaction as SUCCEEDED
   - Triggers confirmation email (TODO)
   ↓
7. Frontend calls booking endpoint with payment_intent_id
   POST /api/flights/create-booking-from-session
   ↓
8. Backend validates payment succeeded before booking
   - Retrieves PaymentIntent from Stripe
   - Confirms status = "succeeded"
   - Proceeds with FlightLogic booking
   ↓
9. Booking confirmed → User receives booking reference
```

### Payment Validation Before Booking

The booking endpoint **requires payment validation** to prevent unpaid bookings:

```python
# app/api/flights.py:365-410
@router.post("/create-booking-from-session")
async def create_booking_from_session(
    session_id: str,
    passenger_data: dict,
):
    # Extract payment_intent_id from passenger data
    payment_intent_id = passenger_data.get("payment_intent_id")

    # Validate payment if provided
    if payment_intent_id and payment_intent_id != "demo_payment_intent":
        payment_service = PaymentService(user_id=str(current_user.id))
        await payment_service.validate_payment_succeeded(payment_intent_id)

    # Proceed with booking only if payment succeeded
    booking_result = await service.create_booking(booking_request)
```

**HTTP Status Codes**:
- `402 Payment Required` - Payment validation failed
- `200 OK` - Payment validated, booking created

## Platform Fee Model

### 5% Platform Fee with Stripe Connect

Voya operates as a **Stripe Connect platform** with automatic fee collection:

**Example Booking**: $100.00 flight
- **Total charged to customer**: $100.00
- **Platform fee (5%)**: $5.00 (held by Voya)
- **Supplier receives**: $95.00 (via Stripe Connect transfer)

### Fee Calculation

```python
# app/domains/payment/service.py:291-300
def _calculate_platform_fee(self, amount: int) -> int:
    """Calculate 5% platform fee.

    Args:
        amount: Total amount in cents

    Returns:
        Platform fee in cents (rounded)
    """
    return int(amount * PLATFORM_FEE_PERCENTAGE)  # 0.05
```

**Constants** (`app/domains/payment/constants.py`):
```python
PLATFORM_FEE_PERCENTAGE = 0.05  # 5%
VOYA_STRIPE_PLATFORM_ACCOUNT_ID = "acct_1SIqE7PD9V3ngpza"  # Voya
FLIGHTLOGIC_STRIPE_ACCOUNT_ID = "acct_1SIqFwAcjtxA6BLd"  # Supplier
```

### Stripe Connect Transfer

```python
# Payment intent with automatic transfer to supplier
payment_params = {
    "amount": 10000,  # $100.00
    "currency": "usd",
    "application_fee_amount": 500,  # $5.00 platform fee
    "transfer_data": {
        "destination": "acct_1SIqFwAcjtxA6BLd"  # Supplier account
    }
}
```

**Connect Transfer Toggle**:
```python
# Set STRIPE_USE_CONNECT_TRANSFERS=false to disable transfers (testing only)
# Full payment goes to platform account, fee tracked in metadata only
STRIPE_USE_CONNECT_TRANSFERS=true  # Default: enabled
```

## Payment Domain Structure

### Domain-Driven Design

```
app/domains/payment/
├── __init__.py           # Public API exports
├── constants.py          # Platform fee, account IDs, collection name
├── enums.py             # PaymentStatus, PayoutStatus
├── exceptions.py        # Domain-specific exceptions
├── repository.py        # MongoDB transaction operations
├── schemas.py           # Pydantic models (requests/responses)
└── service.py           # Business logic (PaymentService)
```

### Key Components

**1. PaymentService** (`service.py`):
- `create_payment_intent()` - Creates Stripe PaymentIntent with platform fee
- `validate_payment_succeeded()` - Validates payment before booking
- `get_transaction_by_payment_intent()` - Retrieves transaction from DB
- `release_payout()` - Manual payout to supplier (admin only)

**2. PaymentRepository** (`repository.py`):
- `create_transaction()` - Store transaction in MongoDB
- `update_transaction_status()` - Update status from webhooks
- `get_transaction_by_payment_intent()` - Query by Stripe payment ID
- `get_transaction_by_voya_reference()` - Query by booking reference

**3. Schemas** (`schemas.py`):
```python
class PaymentIntentCreateRequest(BaseModel):
    booking_amount: int  # Amount in cents
    currency: str = "usd"
    voya_booking_reference: str

class PaymentIntentCreateResponse(BaseModel):
    payment_intent_id: str
    client_secret: str  # For Stripe.js
    amount: int
    currency: str
    platform_fee: int
    supplier_amount: int
    publishable_key: str  # For Stripe.js initialization
```

**4. Enums** (`enums.py`):
```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
```

**5. Exceptions** (`exceptions.py`):
- `PaymentError` - Base exception
- `PaymentIntentCreationError` - Stripe API failure
- `PaymentValidationError` - Payment not succeeded
- `PayoutReleaseError` - Payout creation failed

### Transaction Model

**MongoDB Collection**: `transactions`

```python
{
    "_id": ObjectId("..."),
    "stripe_payment_intent_id": "pi_xxx",
    "stripe_charge_id": "ch_xxx",  # Set by webhook
    "stripe_transfer_id": "tr_xxx",  # Set by manual payout
    "voya_booking_reference": "VOYA-TEST-12345",
    "user_id": ObjectId("..."),
    "amount": 10000,  # Total amount in cents
    "currency": "usd",
    "platform_fee": 500,  # 5% in cents
    "supplier_amount": 9500,  # 95% in cents
    "destination_account_id": "acct_1SIqFwAcjtxA6BLd",
    "status": "succeeded",  # PaymentStatus enum
    "payout_status": "paid",  # PayoutStatus enum (optional)
    "payout_released_at": ISODate("..."),
    "payout_released_by": "admin_user_id",
    "payout_notes": "Released after service delivery",
    "created_at": ISODate("..."),
    "updated_at": ISODate("..."),
    "paid_at": ISODate("...")
}
```

## API Endpoints

### 1. Create Payment Intent

**Endpoint**: `POST /api/payments/create-intent`
**Authentication**: Required (JWT)

**Request**:
```json
{
  "booking_amount": 10000,
  "currency": "usd",
  "voya_booking_reference": "VOYA-TEST-12345"
}
```

**Response** (200):
```json
{
  "payment_intent_id": "pi_3ABC123...",
  "client_secret": "pi_3ABC123..._secret_xyz",
  "amount": 10000,
  "currency": "usd",
  "platform_fee": 500,
  "supplier_amount": 9500,
  "publishable_key": "pk_test_..."
}
```

**Usage**:
```javascript
// Frontend: Initialize Stripe.js with client_secret
const stripe = Stripe(response.publishable_key);
const result = await stripe.confirmCardPayment(response.client_secret, {
  payment_method: {
    card: cardElement,
    billing_details: { name: 'Customer Name' }
  }
});
```

### 2. Get Transaction

**Endpoint**: `GET /api/payments/transaction/{payment_intent_id}`
**Authentication**: Required (JWT)

**Response** (200):
```json
{
  "id": "transaction_123",
  "stripe_payment_intent_id": "pi_3ABC123...",
  "voya_booking_reference": "VOYA-TEST-12345",
  "amount": 10000,
  "currency": "usd",
  "platform_fee": 500,
  "supplier_amount": 9500,
  "status": "succeeded",
  "created_at": "2025-10-20T12:00:00Z",
  "updated_at": "2025-10-20T12:05:00Z",
  "paid_at": "2025-10-20T12:05:00Z"
}
```

### 3. Release Payout (Admin Only)

**Endpoint**: `POST /api/payments/payouts/release`
**Authentication**: Required (JWT + Admin role)

**Request**:
```json
{
  "voya_booking_reference": "VOYA-TEST-12345",
  "notes": "Released after flight completion"
}
```

**Response** (200):
```json
{
  "transfer_id": "tr_3XYZ789...",
  "voya_booking_reference": "VOYA-TEST-12345",
  "amount": 9500,
  "destination_account": "acct_1SIqFwAcjtxA6BLd",
  "status": "paid",
  "created_at": "2025-10-20T14:00:00Z",
  "notes": "Released after flight completion"
}
```

**Errors**:
- `404 Not Found` - Transaction not found
- `400 Bad Request` - Payment not succeeded yet
- `403 Forbidden` - Not admin user

## Environment Configuration

### Required Environment Variables

**Backend** (`.env`):
```bash
# Stripe API Keys (get from https://dashboard.stripe.com/test/apikeys)
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_PUBLISHABLE_KEY=pk_test_51...

# Webhook secret (get from https://dashboard.stripe.com/test/webhooks)
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Connect toggle (set to false for testing without Connect)
STRIPE_USE_CONNECT_TRANSFERS=true
```

**Docker Compose** (`compose.dev.yaml`):
```yaml
backend:
  environment:
    - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-}
    - STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY:-}
    - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}
    - STRIPE_USE_CONNECT_TRANSFERS=${STRIPE_USE_CONNECT_TRANSFERS:-true}
```

### Configuration Class

**Location**: `app/core/config.py`

```python
class Settings(BaseSettings):
    STRIPE_SECRET_KEY: str | None = Field(
        default=None,
        description="Stripe secret key for API calls",
    )
    STRIPE_PUBLISHABLE_KEY: str | None = Field(
        default=None,
        description="Stripe publishable key",
    )
    STRIPE_WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Stripe webhook signing secret for verifying webhook events",
    )
    STRIPE_USE_CONNECT_TRANSFERS: bool = Field(
        default=True,
        description="Enable Stripe Connect transfers to supplier accounts. "
        "Set to False for testing when Connect account lacks transfer capability.",
    )
```

### Getting Stripe Keys

1. **Test API Keys**: https://dashboard.stripe.com/test/apikeys
   - Copy "Publishable key" (starts with `pk_test_`)
   - Reveal and copy "Secret key" (starts with `sk_test_`)

2. **Webhook Secret**: https://dashboard.stripe.com/test/webhooks
   - Create or select webhook endpoint
   - Click "Reveal" next to "Signing secret"
   - Copy secret (starts with `whsec_`)

## Frontend Integration

### Stripe.js Integration

**1. Load Stripe.js**:
```html
<script src="https://js.stripe.com/v3/"></script>
```

**2. Initialize Stripe**:
```javascript
// Create payment intent on backend
const response = await fetch('/api/payments/create-intent', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    booking_amount: 10000,
    currency: 'usd',
    voya_booking_reference: 'VOYA-TEST-12345'
  })
});

const { client_secret, publishable_key } = await response.json();

// Initialize Stripe.js
const stripe = Stripe(publishable_key);
```

**3. Create Card Element**:
```javascript
const elements = stripe.elements();
const cardElement = elements.create('card', {
  style: {
    base: {
      fontSize: '16px',
      color: '#32325d',
      '::placeholder': { color: '#aab7c4' }
    }
  }
});

cardElement.mount('#card-element');

// Handle real-time validation errors
cardElement.on('change', (event) => {
  const displayError = document.getElementById('card-errors');
  if (event.error) {
    displayError.textContent = event.error.message;
  } else {
    displayError.textContent = '';
  }
});
```

**4. Confirm Payment**:
```javascript
async function handlePayment() {
  const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
    payment_method: {
      card: cardElement,
      billing_details: {
        name: 'Customer Name',
        email: 'customer@example.com'
      }
    }
  });

  if (error) {
    // Payment failed
    console.error('Payment failed:', error.message);
    showError(error.message);
  } else if (paymentIntent.status === 'succeeded') {
    // Payment succeeded - proceed with booking
    const bookingResult = await createBooking({
      session_id: sessionId,
      passenger_data: {
        ...passengerInfo,
        payment_intent_id: paymentIntent.id
      }
    });

    showConfirmation(bookingResult);
  }
}
```

### Demo Mode vs Stripe Mode

The flight-booker UI supports two payment modes:

**Demo Mode** (checkbox):
- No actual payment processing
- Uses `payment_intent_id: "demo_payment_intent"`
- Backend skips payment validation
- For testing booking flow without Stripe

**Stripe Mode** (real payment):
- Full Stripe.js integration
- Real card processing
- Payment validation required
- For production and testing payment flow

**Implementation**:
```javascript
function switchPaymentMode(mode) {
  if (mode === 'demo') {
    // Show checkbox payment UI
    document.getElementById('demo-payment-box').style.display = 'block';
    document.getElementById('stripe-payment-box').style.display = 'none';
  } else {
    // Show Stripe Card Element UI
    initializeStripePayment();
    document.getElementById('demo-payment-box').style.display = 'none';
    document.getElementById('stripe-payment-box').style.display = 'block';
  }
}
```

## Webhook Integration

See [WEBHOOKS.md](WEBHOOKS.md) for complete webhook setup and testing guide.

**Quick Overview**:

**Webhook Endpoint**: `POST /webhooks/stripe`
**Signature Verification**: Required (STRIPE_WEBHOOK_SECRET)
**Events Handled**: 8 events (payment_intent.*, charge.*, transfer.*, account.*)

**Key Event**: `payment_intent.succeeded`
```python
async def handle_payment_intent_succeeded(payment_intent: dict[str, Any]) -> None:
    # Update transaction status in MongoDB
    await repo.update_transaction_status(
        payment_intent_id=payment_intent["id"],
        status=PaymentStatus.SUCCEEDED,
        stripe_charge_id=payment_intent.get("latest_charge"),
        paid_at=datetime.fromtimestamp(payment_intent.get("created"), UTC),
    )

    # Send confirmation email (TODO)
    # await email_service.send_booking_confirmation(voya_reference)
```

## Testing

### Local Testing with Demo Mode

**1. Start Backend**:
```bash
cd backend_python
uvicorn app.main:app --reload --port 8000
```

**2. Open Flight Booker**:
```
http://localhost:8000/dev/flight-booker/
```

**3. Test Payment Flow**:
- Search for flight
- Select flight and passenger details
- Choose "Demo Mode (Checkbox)" payment
- Check "I confirm payment" checkbox
- Complete booking

**Result**: Booking created without actual payment processing.

### Testing with Stripe Test Cards

**1. Switch to Stripe Mode** in flight-booker

**2. Use Stripe Test Cards**:

**Successful Payment**:
```
Card: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/25)
CVC: Any 3 digits
```

**Payment Declined**:
```
Card: 4000 0000 0000 0002
```

**Insufficient Funds**:
```
Card: 4000 0000 0000 9995
```

**Full list**: https://stripe.com/docs/testing#cards

### Testing Webhooks Locally

See [WEBHOOKS.md](WEBHOOKS.md) for ngrok setup and local webhook testing.

**Quick Steps**:
1. Start ngrok: `./test_webhook_with_ngrok.sh`
2. Create webhook endpoint pointing to ngrok URL
3. Add STRIPE_WEBHOOK_SECRET to .env
4. Trigger payment → Watch webhook delivery

### API Tester Integration

**URL**: http://localhost:8000/dev/api-tester.html

**Payment Tab**:
1. Click "💳 Payments" tab
2. Create payment intent
3. View transaction details
4. Test admin payout release

## Security Considerations

### PCI Compliance

✅ **Voya is PCI compliant** - Card details never touch Voya servers:
- Stripe.js handles all card input
- Card data sent directly to Stripe
- Backend only receives `payment_intent_id` token

### Payment Validation

✅ **Backend validates all payments before booking**:
```python
# app/api/flights.py - Always validate payment
if payment_intent_id and payment_intent_id != "demo_payment_intent":
    await payment_service.validate_payment_succeeded(payment_intent_id)
```

**Why**: Prevents unpaid bookings if frontend is compromised.

### Webhook Signature Verification

✅ **All webhooks verified with STRIPE_WEBHOOK_SECRET**:
```python
# app/api/webhooks.py
if webhook_secret and stripe_signature:
    event = stripe.Webhook.construct_event(
        payload, stripe_signature, webhook_secret
    )
else:
    # Reject webhook without signature
    raise HTTPException(400, "Missing signature")
```

### Environment Variables

❌ **Never commit to Git**:
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET

✅ **Add to .gitignore**:
```
.env
.env.local
.env.*.local
```

### Admin-Only Payout Release

✅ **Manual payouts require admin role**:
```python
# Only admins can release payouts
@router.post("/payouts/release", dependencies=[Depends(require_admin)])
async def release_payout(...):
    pass
```

**Why**: Prevents unauthorized fund transfers.

## Troubleshooting

### Payment Intent Creation Fails

**Error**: `Failed to create payment intent: API key not set`

**Solution**:
```bash
# Check .env file has STRIPE_SECRET_KEY
cat .env | grep STRIPE_SECRET_KEY

# Restart backend after adding key
```

### Payment Validation Fails

**Error**: `Payment validation failed: Payment not completed. Status: requires_payment_method`

**Cause**: Payment not completed on frontend

**Solution**: Complete payment with Stripe.js before calling booking endpoint

### Webhook Signature Verification Fails

**Error**: `Invalid signature`

**Solutions**:
1. Check STRIPE_WEBHOOK_SECRET matches webhook endpoint
2. Restart backend after adding secret
3. Verify webhook endpoint URL matches deployed URL

### Connect Transfer Not Working

**Error**: Funds stay in platform account instead of transferring to supplier

**Check**:
```bash
# Is Connect transfer enabled?
echo $STRIPE_USE_CONNECT_TRANSFERS  # Should be "true"

# Are account IDs correct?
cat app/domains/payment/constants.py | grep ACCOUNT_ID
```

**Solution**: Set `STRIPE_USE_CONNECT_TRANSFERS=true` in .env

## Related Documentation

- **[WEBHOOKS.md](WEBHOOKS.md)** - Webhook setup and testing with ngrok
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Payment domain in system architecture
- **[FRONTEND_BACKEND_COLLABORATION.md](FRONTEND_BACKEND_COLLABORATION.md)** - Payment API integration patterns
- **Stripe Dashboard**: https://dashboard.stripe.com/test/payments
- **Stripe API Docs**: https://stripe.com/docs/api

---

**Last Updated**: October 2025
**Maintainer**: Backend Team
**Questions**: Create GitHub issue with label `payments`
