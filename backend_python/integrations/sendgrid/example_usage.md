# SendGrid Adapter Pattern Uitleg

## Hoe het werkt

De adapter pattern zorgt voor een schone scheiding tussen:
- **Domain models** (`app/domains/email/schemas.py`) - Wat de applicatie gebruikt
- **SendGrid DTOs** (`integrations/sendgrid/dto.py`) - Wat SendGrid API verwacht

## Flow Diagram

```
Application Layer (EmailService)
    ↓
    EmailMessage (domain model)
    ↓
SendGrid Client
    ↓
    SendGridAdapter.to_sendgrid_message()
    ↓
    SendGridEmailMessage (DTO)
    ↓
SendGrid API
    ↓
    Response
    ↓
    SendGridAdapter.create_success_result()
    ↓
    EmailResult (domain model)
    ↓
Application Layer
```

## Code Flow

### 1. Applicatie stuurt email (domain model)
```python
# In EmailService
message = EmailMessage(
    to_email="user@example.com",
    subject="Welcome",
    html_content="<h1>Welcome!</h1>"
)
result = sendgrid_client.send_email(message)
```

### 2. SendGrid client ontvangt domain model
```python
def send_email(self, message: EmailMessage) -> EmailResult:
    # Convert domain → DTO
    sendgrid_message = SendGridAdapter.to_sendgrid_message(message)

    # Use DTO for API call
    mail = Mail(
        to_emails=sendgrid_message.to_email,
        subject=sendgrid_message.subject,
        ...
    )
```

### 3. Response wordt terug geconverteerd
```python
    # API response → domain model
    if success:
        return SendGridAdapter.create_success_result(
            status_code=response.status_code,
            message_id=response.headers.get("X-Message-Id")
        )
    else:
        return SendGridAdapter.create_error_result(
            f"Failed: {response.status_code}"
        )
```

## Voordelen

1. **Ontkoppeling**: Applicatie kent SendGrid API details niet
2. **Flexibiliteit**: Makkelijk wisselen naar andere email provider
3. **Type Safety**: Duidelijke contracts tussen lagen
4. **Testbaarheid**: Mock de adapter voor unit tests
5. **Evolutie**: Domain en API kunnen onafhankelijk evolueren

## Vergelijk met FlightLogic

Dit is exact hetzelfde patroon als bij FlightLogic:
- `flightlogic/dto.py` - FlightLogic API structuren
- `flightlogic/adapter.py` - Conversie logic
- `domains/flight/schemas.py` - Business models

## Wanneer is dit nuttig?

In dit geval zijn de SendGrid en domain models bijna identiek, maar het patroon wordt waardevol wanneer:

1. **API wijzigt**: SendGrid past hun API aan → alleen adapter aanpassen
2. **Business needs veranderen**: Extra velden nodig → domain model uitbreiden
3. **Meerdere providers**: Gmail, Mailgun, etc → elke provider eigen adapter
4. **API quirks**: Provider-specifieke formatting → adapter handelt dit af

Bijvoorbeeld, als SendGrid later vereist dat subjects max 78 chars zijn:
```python
# In adapter
def to_sendgrid_message(domain_message: EmailMessage):
    return SendGridEmailMessage(
        subject=domain_message.subject[:78],  # Truncate for API
        ...
    )
```

De applicatie hoeft hier niets van te weten!
