# Python Coding Standards - Voya Backend

**Version:** 2.0 (Consolidated)
**Last Updated**: October 2025
**Target Audience**: All backend Python developers
**Scope**: Python 3.12+, FastAPI applications

**Note**: This is the consolidated coding standards document. For quick reference patterns, see `backend_python/CLAUDE.md`.

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Code Structure & Organization](#code-structure--organization)
3. [Naming Conventions](#naming-conventions)
4. [Type Hints](#type-hints)
5. [Async/Await Patterns](#asyncawait-patterns)
6. [Pydantic Models](#pydantic-models)
7. [Error Handling](#error-handling)
8. [Security Best Practices](#security-best-practices)
9. [Testing Standards](#testing-standards)
10. [Functions & Methods](#functions--methods)
11. [Classes & Objects](#classes--objects)
12. [Logging & Monitoring](#logging--monitoring)
13. [Performance](#performance)
14. [Documentation](#documentation)
15. [Tool Configuration](#tool-configuration)
16. [Code Review Checklist](#code-review-checklist)

---

## Core Principles

### Readability First
Code is read far more often than it's written. Optimize for the reader, not the writer.

### Explicit Over Implicit
Prefer clarity over cleverness. Magic is for frameworks, not application code.

### Fail Fast and Loudly
Catch errors at the boundary. Invalid data should never reach business logic.

### No Surprises
Functions should do what their names suggest, nothing more. Side effects should be obvious.

### Type Safety
Use comprehensive type hints. They serve as inline documentation and catch bugs before runtime.

### Async First
This is a FastAPI application. Understand async/await deeply—blocking the event loop breaks everything.

### Security by Default
Never trust user input. Validate everything. Assume attackers will try every endpoint.

---

## Code Structure & Organization

### Project Layout

```
backend_python/
├── app/
│   ├── main.py              # Application entry point
│   ├── api/                 # API endpoints (routes)
│   ├── core/                # Config, security, logging
│   ├── domains/             # Business logic by domain (DDD)
│   │   ├── auth/
│   │   │   ├── schemas.py   # Request/response models
│   │   │   ├── service.py   # Business logic
│   │   │   ├── repository.py # Database operations
│   │   │   └── exceptions.py # Domain-specific errors
│   │   ├── bookings/
│   │   └── flights/
│   ├── database/            # Database connections
│   └── integrations/        # External API clients
├── tests/
│   ├── unit_tests/
│   └── integration_tests/
└── pyproject.toml
```

### Module Organization

**One responsibility per module:**
- `schemas.py`: Data validation models (Pydantic)
- `service.py`: Business logic and orchestration
- `repository.py`: Database operations only
- `exceptions.py`: Custom exception classes
- `enums.py`: Enumerations and constants

### Dependency Direction

```
API Layer → Service Layer → Repository Layer → Database
         ↓
      Schemas (used by all layers)
```

**Never:**
- Repository calling service
- Database logic in API handlers
- Business rules in repositories

### Domain-Driven Design (DDD)

Voya uses DDD for business logic organization:

```python
# Example domain structure
app/domains/bookings/
├── schemas.py      # BookingCreate, BookingResponse, BookingUpdate
├── service.py      # BookingService with business logic
├── repository.py   # BookingRepository for database operations
├── exceptions.py   # BookingError, FlightUnavailable
└── enums.py        # BookingStatus, PaymentStatus
```

---

## Naming Conventions

### General Rules

**Be explicit and descriptive:**
```python
# Good
def calculate_total_price_with_tax(subtotal: float, tax_rate: float) -> float:
    return subtotal * (1 + tax_rate)

# Bad - too vague
def calc(x: float, y: float) -> float:
    return x * (1 + y)
```

**Use verbs for functions, nouns for classes:**
```python
# Functions - actions
def fetch_user_profile(user_id: str) -> User:
def validate_email_format(email: str) -> bool:
def send_confirmation_email(recipient: str) -> None:

# Classes - things
class UserProfile:
class EmailValidator:
class PaymentProcessor:
```

### Conventions by Type

| Type | Convention | Example |
|------|-----------|---------|
| Module/Package | `snake_case` | `user_service.py` |
| Class | `PascalCase` | `BookingService` |
| Function/Method | `snake_case` | `create_booking()` |
| Variable | `snake_case` | `user_email` |
| Constant | `UPPER_CASE` | `MAX_RETRY_ATTEMPTS` |
| Private | `_leading_underscore` | `_internal_method()` |
| Type Variable | `PascalCase` | `T`, `UserT` |

### Avoid Abbreviations

```python
# Good
user_repository = UserRepository()
maximum_attempts = 3
authentication_token = "abc123"

# Bad
usr_repo = UserRepository()
max_att = 3
auth_tok = "abc123"
```

**Exception**: Industry-standard abbreviations are acceptable:
- `id` (identifier)
- `url`, `uri`
- `html`, `json`, `xml`
- `api`, `http`, `db`

---

## Type Hints

### Required on All Public Interfaces

**All public functions, methods, and module-level variables must have type hints:**

```python
from typing import Any

# Correct
def process_payment(amount: float, currency: str) -> dict[str, Any]:
    return {"status": "success", "amount": amount}

# Wrong - missing types
def process_payment(amount, currency):
    return {"status": "success", "amount": amount}
```

### Modern Python 3.10+ Syntax

Use built-in types and union syntax:

```python
# Correct - Python 3.10+
def find_user(email: str) -> dict[str, Any] | None:
    pass

def get_ids(users: list[dict]) -> list[str]:
    pass

# Avoid - old typing module syntax
from typing import Optional, Union, List, Dict

def find_user(email: str) -> Optional[Dict[str, Any]]:
    pass
```

### Async Function Return Types

Annotate the return value, not the coroutine wrapper:

```python
# CORRECT
async def get_flights() -> list[Flight]:
    return await flight_service.search()

# WRONG
async def get_flights() -> Coroutine[Any, Any, list[Flight]]:
    return await flight_service.search()
```

### Complex Types

```python
from typing import TypeAlias, Literal, TypedDict
from collections.abc import Callable

# Type aliases for clarity
UserId: TypeAlias = str
Price: TypeAlias = float

# Literal for enumerated values
Status: TypeAlias = Literal["pending", "confirmed", "cancelled"]
FlightClass: TypeAlias = Literal["economy", "business", "first"]

# TypedDict for structured dicts
class UserDict(TypedDict):
    id: str
    email: str
    age: int

# Callable types
ProcessorFunc: TypeAlias = Callable[[dict], dict]
```

### TypedDict for Database Documents

```python
from typing import TypedDict

class BookingDoc(TypedDict):
    _id: str
    user_id: str
    flight_number: str
    passenger_name: str
    status: Literal["pending", "confirmed", "cancelled"]
    created_at: str

collection: AsyncIOMotorCollection[BookingDoc] = db.bookings
```

### Generic Types

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def find_by_id(self, id: str) -> T | None:
        pass

    def save(self, entity: T) -> T:
        pass

user_repo: Repository[User] = Repository()
```

---

## Async/Await Patterns

### CRITICAL: Event Loop Safety

**The single most important rule:** Never block the event loop in async functions.

```python
import asyncio
import time

# CORRECT - Async I/O with await
async def search_flights(origin: str, destination: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/search?from={origin}&to={destination}")
    return response.json()

# CORRECT - Blocking operation in regular function
def process_payment(amount: int) -> dict:
    # Stripe SDK is synchronous - use regular def
    # FastAPI automatically runs this in threadpool
    return stripe.PaymentIntent.create(amount=amount)

# WRONG - Blocks event loop
async def bad_sleep():
    time.sleep(5)  # BLOCKS ALL REQUESTS!

# CORRECT - Yields to event loop
async def good_sleep():
    await asyncio.sleep(5)

# WRONG - Synchronous I/O in async function
async def bad_file_read():
    with open("file.txt") as f:  # Blocks!
        return f.read()

# CORRECT - Use async file operations
async def good_file_read():
    async with aiofiles.open("file.txt") as f:
        return await f.read()
```

### When to Use async def vs def

**Use `async def` for:**
- Database operations (Motor)
- HTTP requests (httpx)
- File I/O (aiofiles)
- Any operation with `await`

**Use `def` for:**
- Synchronous SDKs (Stripe, some Google APIs)
- CPU-bound operations
- Pure calculations with no I/O

```python
# Async - I/O bound
async def fetch_user_data(user_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
    return response.json()

# Sync - CPU bound
def calculate_statistics(data: list[float]) -> dict:
    return {
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data)
    }
```

### Wrapping Synchronous Operations

```python
from fastapi.concurrency import run_in_threadpool

async def create_payment_intent(amount: int) -> dict:
    def _create() -> dict:
        return stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            automatic_payment_methods={"enabled": True}
        )

    intent = await run_in_threadpool(_create)
    # Return typed dict, not raw Stripe object
    return {
        "client_secret": intent.client_secret,
        "id": intent.id,
        "status": intent.status
    }
```

### Always Await Coroutines

```python
# Wrong - forgot await
async def get_user(user_id: str):
    user = db.users.find_one({"_id": user_id})  # Returns coroutine object
    return user  # Returns <coroutine object>, not data!

# Correct
async def get_user(user_id: str):
    user = await db.users.find_one({"_id": user_id})
    return user
```

---

## Pydantic Models

### Separate Input and Output Models

Always separate input validation from output serialization:

```python
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Input - validates incoming data
class BookingCreate(BaseModel):
    passenger_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    flight_number: str = Field(pattern=r'^[A-Z]{2}\d{3,4}$')
    departure_date: datetime

# Output - filters response
class BookingResponse(BaseModel):
    id: str
    passenger_name: str
    flight_number: str
    status: Literal["pending", "confirmed", "cancelled"]
    created_at: datetime

# Internal - database representation
class BookingDB(BaseModel):
    id: str
    passenger_name: str
    email: str
    flight_number: str
    status: str
    created_at: datetime
    payment_details: dict  # Internal only
```

### Field Validation

```python
from pydantic import field_validator, model_validator

class BookingCreate(BaseModel):
    departure_date: datetime
    return_date: datetime | None = None

    @field_validator('departure_date')
    @classmethod
    def departure_must_be_future(cls, v: datetime) -> datetime:
        if v < datetime.now():
            raise ValueError('Departure must be in the future')
        return v

    @model_validator(mode='after')
    def return_after_departure(self) -> 'BookingCreate':
        if self.return_date and self.return_date <= self.departure_date:
            raise ValueError('Return must be after departure')
        return self
```

### Use Field() with Validation

```python
class UserCreate(BaseModel):
    email: EmailStr = Field(
        description="User's email address",
        examples=["user@example.com"]
    )
    age: int = Field(
        ge=18,
        le=120,
        description="User's age (must be 18+)",
        examples=[25]
    )
    phone: str | None = Field(None, pattern=r'^\+?1?\d{9,15}$')

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john@example.com",
                    "age": 30
                }
            ]
        }
    }
```

### Never Return Pydantic Instances to Database

```python
# WRONG - Double validation overhead
async def bad_create(booking: BookingCreate) -> BookingResponse:
    result = await db.bookings.insert_one(booking)  # Pydantic instance
    return result

# CORRECT - Convert to dict first
async def good_create(booking: BookingCreate) -> BookingResponse:
    doc = booking.model_dump()  # Convert to dict
    result = await db.bookings.insert_one(doc)
    inserted = await db.bookings.find_one({"_id": result.inserted_id})
    return BookingResponse(**inserted)
```

### FastAPI Response Model

```python
@app.post("/bookings/", response_model=BookingResponse, status_code=201)
async def create_booking(booking: BookingCreate):
    # response_model automatically validates and filters output
    result = await bookings_service.create(booking.model_dump())
    return result  # FastAPI validates against BookingResponse
```

---

## Error Handling

### Use Specific Exceptions

```python
from fastapi import HTTPException

# Good - specific exceptions
class BookingNotFoundError(Exception):
    pass

class PaymentFailedError(Exception):
    pass

def get_booking(booking_id: str) -> Booking:
    booking = db.find(booking_id)
    if not booking:
        raise BookingNotFoundError(f"Booking {booking_id} not found")
    return booking

# Bad - generic exceptions
def get_booking(booking_id: str) -> Booking:
    booking = db.find(booking_id)
    if not booking:
        raise Exception("Error occurred")  # Which error?
    return booking
```

### Use HTTPException with Specific Status Codes

```python
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking

# Common status codes:
# 400 - Bad Request (validation error)
# 401 - Unauthorized (missing/invalid token)
# 403 - Forbidden (valid token, insufficient permissions)
# 404 - Not Found
# 422 - Unprocessable Entity (Pydantic validation)
# 500 - Internal Server Error
# 502 - Bad Gateway (external API error)
# 504 - Gateway Timeout (external API timeout)
```

### Exception Context

Always provide actionable context:

```python
# Good
try:
    payment = process_payment(amount)
except StripeError as e:
    logger.error(
        "Payment failed",
        extra={
            "amount": amount,
            "user_id": user.id,
            "error_code": e.code,
            "error_message": str(e)
        }
    )
    raise PaymentFailedError(
        f"Payment of ${amount} failed for user {user.id}: {e.code}"
    ) from e

# Bad - no context
except StripeError as e:
    raise PaymentFailedError("Payment failed")
```

### Implement Retry Logic for External APIs

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_flight_api(params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(API_URL, json=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Flight API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Flight API error: {e.response.status_code}")
```

### Don't Silence Errors

```python
# Wrong - silent failure
try:
    result = risky_operation()
except Exception:
    pass  # Error swallowed!

# Correct - log and re-raise or handle
try:
    result = risky_operation()
except SpecificError as e:
    logger.warning(f"Expected error: {e}")
    result = default_value
except Exception:
    logger.exception("Unexpected error in risky_operation")
    raise
```

### Custom Exception Classes

```python
class BookingError(Exception):
    """Base exception for booking operations"""
    pass

class FlightUnavailable(BookingError):
    """Raised when requested flight is not available"""
    def __init__(self, flight_id: str, date: str):
        self.flight_id = flight_id
        self.date = date
        super().__init__(f"Flight {flight_id} not available for {date}")

# Usage
if not flight.available:
    raise FlightUnavailable(flight.id, departure_date)
```

---

## Security Best Practices

### Input Sanitization

**Trust nothing from users:**

```python
from pydantic import validator

# ALWAYS validate through Pydantic
class SearchRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    destination: str = Field(min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    date: datetime = Field(gt=datetime.now())

class SearchQuery(BaseModel):
    term: str = Field(min_length=1, max_length=100)

    @validator('term')
    @classmethod
    def sanitize_search(cls, v: str) -> str:
        # Remove potential MongoDB operators
        dangerous = ['$', '{', '}']
        for char in dangerous:
            v = v.replace(char, '')
        return v.strip()
```

### Password Security

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor
)

# Never store plain passwords
def create_user(email: str, password: str) -> User:
    password_hash = pwd_context.hash(password)
    return User(email=email, password_hash=password_hash)

# Verify passwords safely
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### JWT Token Security

```python
from jose import jwt
from datetime import timedelta

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

### Secrets Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Load from environment
    database_url: str
    secret_key: str
    stripe_api_key: str

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }

# Never hardcode secrets
# Wrong: api_key = "sk_test_abc123"
# Correct:
settings = Settings()
api_key = settings.stripe_api_key
```

### MongoDB Injection Prevention

```python
# Wrong - string interpolation
query = f'{{"username": "{user_input}"}}'
result = db.users.find_one(json.loads(query))

# Correct - parameterized
result = db.users.find_one({"username": user_input})

# WRONG - MongoDB injection vulnerability
async def bad_search(username: str):
    return await db.users.find_one({"username": username})  # If username is {"$ne": null}

# CORRECT - Type-safe with Pydantic
class UserSearch(BaseModel):
    username: str = Field(min_length=1, max_length=50)

async def good_search(search: UserSearch):
    return await db.users.find_one({"username": search.username})
```

---

## Testing Standards

### Test Structure: Arrange-Act-Assert

```python
@pytest.mark.asyncio
async def test_create_booking():
    # Arrange - set up test data
    booking_data = {
        "passenger_name": "John Doe",
        "flight_number": "AA123"
    }

    # Act - perform the action
    response = await client.post("/bookings/", json=booking_data)

    # Assert - verify results
    assert response.status_code == 201
    assert response.json()["passenger_name"] == "John Doe"
```

### Test Naming

```python
# Good - describes what's being tested
def test_user_creation_with_valid_email_succeeds():
def test_payment_with_insufficient_funds_raises_error():
def test_booking_cancellation_refunds_amount():

# Bad - vague
def test_user():
def test_payment():
def test_cancel():
```

### Mocking External Dependencies

```python
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
@patch("app.services.stripe_client")
async def test_payment_processing(mock_stripe: MagicMock):
    # Configure mock
    mock_stripe.create_payment_intent.return_value = {
        "id": "pi_123",
        "status": "succeeded"
    }

    # Test
    result = await process_payment(amount=1000)

    # Verify
    assert result["status"] == "succeeded"
    mock_stripe.create_payment_intent.assert_called_once_with(
        amount=1000,
        currency="usd"
    )
```

### Mock External APIs with AsyncMock

```python
@pytest.mark.asyncio
@patch("app.services.flight_client.search_flights")
async def test_search(mock_search: AsyncMock, client: AsyncClient):
    mock_search.return_value = {"flights": [{"number": "AA123"}]}

    response = await client.get("/flights?origin=JFK&dest=LAX")

    assert response.status_code == 200
    assert len(response.json()["flights"]) == 1
    mock_search.assert_called_once_with("JFK", "LAX")
```

### Test Coverage Goals

- **Minimum:** 80% line coverage for new code
- **Critical paths:** 100% coverage (authentication, payments, bookings)
- **Test types:**
  - Unit tests: Fast, isolated, no external dependencies
  - Integration tests: Test multiple components together
  - E2E tests: Test user workflows

```bash
# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Fail if below threshold
pytest --cov=app --cov-fail-under=80
```

---

## Functions & Methods

### Single Responsibility

Each function should do one thing well:

```python
# Good - single responsibility
def validate_email(email: str) -> bool:
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None

def create_user(email: str, password: str) -> User:
    if not validate_email(email):
        raise ValueError("Invalid email")
    hashed = hash_password(password)
    return User(email=email, password=hashed)

# Bad - doing too much
def create_user(email: str, password: str) -> User:
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise ValueError("Invalid email")
    hashed = hashlib.sha256(password.encode()).hexdigest()
    user = User(email=email, password=hashed)
    send_welcome_email(email)  # Side effect!
    log_user_creation(user)     # Another side effect!
    return user
```

### Parameter Limits

Limit function parameters to 5 or fewer. More suggests the function is doing too much or needs a data class:

```python
# Bad - too many parameters
def create_booking(
    user_id: str,
    flight_number: str,
    departure_date: str,
    return_date: str,
    passenger_count: int,
    seat_class: str,
    meal_preference: str
) -> Booking:
    pass

# Good - use a data class
@dataclass
class BookingRequest:
    user_id: str
    flight_number: str
    departure_date: str
    return_date: str
    passenger_count: int
    seat_class: str
    meal_preference: str

def create_booking(request: BookingRequest) -> Booking:
    pass
```

### Return Early

Reduce nesting by returning early:

```python
# Good
def process_order(order: Order) -> dict:
    if not order.is_valid():
        return {"error": "Invalid order"}

    if not order.in_stock():
        return {"error": "Out of stock"}

    payment = process_payment(order)
    return {"success": True, "payment_id": payment.id}

# Bad - excessive nesting
def process_order(order: Order) -> dict:
    if order.is_valid():
        if order.in_stock():
            payment = process_payment(order)
            return {"success": True, "payment_id": payment.id}
        else:
            return {"error": "Out of stock"}
    else:
        return {"error": "Invalid order"}
```

### Default Arguments

Avoid mutable default arguments:

```python
# Wrong - mutable default
def add_item(item: str, items: list = []) -> list:
    items.append(item)
    return items

# Correct
def add_item(item: str, items: list | None = None) -> list:
    if items is None:
        items = []
    items.append(item)
    return items
```

---

## Classes & Objects

### Class Design Principles

**Cohesion:** Related data and behavior belong together.
**Encapsulation:** Hide implementation details.
**Composition:** Favor composition over inheritance.

### Properties vs Methods

Use properties for attributes, methods for actions:

```python
class User:
    def __init__(self, first_name: str, last_name: str):
        self._first_name = first_name
        self._last_name = last_name

    # Property - behaves like an attribute
    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    # Method - performs an action
    def send_notification(self, message: str) -> None:
        print(f"Notifying {self.full_name}: {message}")
```

### Dataclasses for Data

Use dataclasses for simple data containers:

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)  # Immutable
class Point:
    x: float
    y: float

    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

@dataclass
class User:
    id: str
    email: str
    roles: list[str] = field(default_factory=list)
```

### Class vs Module Functions

```python
# Use a class when you need state
class PaymentProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = stripe.StripeClient(api_key)

    def process(self, amount: int) -> dict:
        return self.client.charges.create(amount=amount)

# Use module functions when stateless
def calculate_tax(amount: float, rate: float) -> float:
    return amount * rate

def format_currency(amount: float) -> str:
    return f"${amount:.2f}"
```

---

## Logging & Monitoring

### Structured Logging

Use structured logging for easier querying:

```python
import structlog

logger = structlog.get_logger()

# Good - structured
logger.info(
    "payment_processed",
    payment_id="pi_123",
    amount=1000,
    currency="usd",
    user_id="user_456"
)

# Bad - string interpolation
logger.info(f"Processed payment pi_123 for $10.00 by user_456")
```

### Log Levels

- **DEBUG:** Detailed diagnostic information
- **INFO:** General informational messages
- **WARNING:** Warning messages for potentially harmful situations
- **ERROR:** Error events that might still allow the application to continue
- **CRITICAL:** Serious errors that may prevent the application from continuing

```python
# Debug - detailed diagnostic info
logger.debug("Starting flight search", origin="JFK", destination="LAX")

# Info - normal operations
logger.info("User registered", user_id=user.id)

# Warning - unexpected but recoverable
logger.warning("Cache miss", key=cache_key)

# Error - operation failed
logger.error("Payment failed", payment_id=payment.id, error=str(e))

# Critical - system is unusable
logger.critical("Database connection lost", error=str(e))
```

### Never Log Sensitive Data

```python
# Wrong - logs sensitive data
logger.info(f"User login: {email}, password: {password}")
logger.info(f"Payment: card={card_number}")

# Correct - mask or exclude sensitive data
logger.info("User login attempt", email=email)  # No password
logger.info("Payment processed", last_4=card_number[-4:])
```

---

## Performance

### Database Query Optimization

```python
# Bad - N+1 query problem
async def get_users_with_bookings():
    users = await db.users.find().to_list(100)
    for user in users:
        # N additional queries!
        user["bookings"] = await db.bookings.find(
            {"user_id": user["_id"]}
        ).to_list(None)
    return users

# Good - single aggregation query
async def get_users_with_bookings():
    pipeline = [
        {
            "$lookup": {
                "from": "bookings",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "bookings"
            }
        }
    ]
    return await db.users.aggregate(pipeline).to_list(100)
```

### Caching

```python
from functools import lru_cache
import asyncio

# Sync caching
@lru_cache(maxsize=128)
def get_airport_info(code: str) -> dict:
    # Expensive operation cached
    return load_airport_data(code)

# Async caching (custom implementation)
_cache: dict[str, tuple[Any, float]] = {}
CACHE_TTL = 300  # 5 minutes

async def get_flight_results(origin: str, destination: str) -> list:
    cache_key = f"{origin}:{destination}"

    if cache_key in _cache:
        result, timestamp = _cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return result

    result = await flight_api.search(origin, destination)
    _cache[cache_key] = (result, time.time())
    return result
```

### Batch Operations

```python
# Bad - one at a time
for user_id in user_ids:
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"last_login": now}}
    )

# Good - bulk update
await db.users.update_many(
    {"_id": {"$in": user_ids}},
    {"$set": {"last_login": now}}
)
```

---

## Documentation

### When to Comment

**DO comment:**
- Why, not what: Business rules, gotchas, workarounds
- Complexity: Non-obvious algorithms or optimizations
- External constraints: API limits, rate limiting
- TODOs: Temporary solutions or future improvements

```python
# Good comments
def calculate_price(base: float, user: User) -> float:
    # Business rule: Premium users get 20% discount
    if user.is_premium:
        base *= 0.8

    # HACK: FlightLogic API sometimes returns prices in cents
    # TODO: Remove when API v2 is deployed (ETA: Q2 2025)
    if base > 10000:
        base /= 100

    # Cost warning: OpenAI call costs €0.03 per request
    response = await openai.create_completion(...)

    return base
```

**DON'T comment:**
- Obvious code
- Redundant information
- Outdated information

```python
# Bad comments
# Increment counter  ❌
counter += 1

# Create a user  ❌
user = User(email=email)

# This function adds two numbers  ❌
def add(a: int, b: int) -> int:
    return a + b
```

### Docstrings

Use for public APIs and complex functions:

```python
def calculate_booking_total(
    base_fare: float,
    passengers: int,
    taxes: dict[str, float],
    discount: float | None = None
) -> float:
    """Calculate total booking price including all fees.

    Args:
        base_fare: Base fare per passenger in USD
        passengers: Number of passengers
        taxes: Dict of tax types and amounts
        discount: Optional discount percentage (0.0 to 1.0)

    Returns:
        Total price after taxes and discounts

    Raises:
        ValueError: If discount is outside valid range

    Example:
        >>> calculate_booking_total(
        ...     base_fare=100.0,
        ...     passengers=2,
        ...     taxes={"vat": 0.2},
        ...     discount=0.1
        ... )
        216.0
    """
    if discount and not 0.0 <= discount <= 1.0:
        raise ValueError("Discount must be between 0 and 1")

    subtotal = base_fare * passengers
    for tax_amount in taxes.values():
        subtotal += tax_amount

    if discount:
        subtotal *= (1 - discount)

    return round(subtotal, 2)
```

### FastAPI Endpoint Documentation

For FastAPI endpoints, the first line becomes API documentation:

```python
@app.post("/bookings/", response_model=BookingResponse)
async def create_booking(booking: BookingCreate):
    """
    Create a new flight booking.

    Validates passenger information, checks flight availability,
    and creates a pending booking. Payment must be completed
    separately via the /payments/ endpoint.
    """
    return await bookings_service.create(booking)
```

---

## Tool Configuration

### Ruff: Linting and Formatting

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code (replaces Black)
ruff format .
```

**Key Rules:**
- `FAST`: FastAPI-specific patterns
- `ASYNC`: Async/await safety (CRITICAL)
- `B008`: Disabled for FastAPI `Depends()` pattern
- `S`: Security checks

### MyPy: Type Checking

```bash
# Run type checking
mypy app/
```

**Critical Configuration:**
- `plugins = ["pydantic.mypy"]` - Required for Pydantic v2
- `strict = true` - Comprehensive checking
- `disallow_untyped_defs = true` - All functions need types

### Bandit: Security Scanning

```bash
# Run security scan
bandit -r app/ -ll -c pyproject.toml
```

### Pre-commit Hooks

Fast checks on commit, thorough checks on push:

```bash
# Install hooks
pre-commit install
pre-commit install --hook-type pre-push

# Run manually
pre-commit run --all-files
```

---

## Code Review Checklist

Before submitting code for review, verify:

**Functionality:**
- [ ] Code does what it's supposed to do
- [ ] Edge cases are handled
- [ ] Error conditions are tested

**Code Quality:**
- [ ] Type hints on all public functions
- [ ] No magic numbers or strings (use constants)
- [ ] Functions have single responsibility
- [ ] No code duplication
- [ ] No blocking operations in async functions

**Testing:**
- [ ] Unit tests added for new functionality
- [ ] Tests cover success and failure paths
- [ ] All tests pass locally
- [ ] Coverage meets minimum requirements (80%)

**Security:**
- [ ] User input is validated (Pydantic models)
- [ ] No hardcoded secrets
- [ ] Sensitive data not logged
- [ ] Database queries are type-safe

**Documentation:**
- [ ] Complex logic has explanatory comments
- [ ] Public APIs have docstrings
- [ ] CLAUDE.md updated if needed

**Automated Enforcement:**
- [ ] Ruff catches style violations
- [ ] MyPy catches type errors
- [ ] Bandit catches security issues
- [ ] Pre-commit blocks commits with critical issues
- [ ] CI/CD pipeline passes

---

## Common Patterns

### Configuration Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str
    SECRET_KEY: str
    ENVIRONMENT: Literal["development", "staging", "production"]

    class Config:
        env_file = ".env"

settings = Settings()
```

### Database Connection

⚠️ **DEPRECATION NOTICE**: Motor (async MongoDB driver) is deprecated as of May 2025. Plan migration to PyMongo async by Q2 2026. See `backend_python/CLAUDE.md` for migration timeline.

```python
from motor.motor_asyncio import AsyncIOMotorClient

async def connect_to_mongo():
    app.state.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
    app.state.mongodb = app.state.mongodb_client[settings.DATABASE_NAME]

async def close_mongo_connection():
    app.state.mongodb_client.close()
```

### Dependency Injection

```python
from typing import Annotated
from fastapi import Depends

async def get_database():
    return app.state.mongodb

async def get_current_user(
    token: Annotated[str, Depends(verify_token)],
    db = Depends(get_database)
) -> dict:
    user = await db.users.find_one({"_id": token["user_id"]})
    if not user:
        raise HTTPException(401, "User not found")
    return user

@app.get("/profile")
async def get_profile(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    return current_user
```

---

## Additional Resources

**Python:**
- [PEP 8 – Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

**FastAPI:**
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/)

**Testing:**
- [Pytest Documentation](https://docs.pytest.org/)
- [Test Driven Development Guide](https://testdriven.io/)

---

**Remember:** These standards exist to prevent bugs, improve security, and make the codebase maintainable. When in doubt, prioritize clarity and safety over brevity.

**Questions?** See `backend_python/CLAUDE.md` for quick reference patterns or create a GitHub issue with label `coding-standards`.
