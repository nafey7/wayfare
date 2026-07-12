"""Email domain validators.

Validation functions specific to email operations.
"""


def validate_email_subject(subject: str) -> bool:
    """Validate email subject length and content.

    Args:
        subject: Email subject to validate

    Returns:
        bool: True if valid, False otherwise

    Rules:
        - Must be non-empty string
        - Length between 1-200 characters (after stripping)
    """
    if not subject or not isinstance(subject, str):
        return False
    subject_stripped = subject.strip()
    return 1 <= len(subject_stripped) <= 200


def validate_recipient_count(recipients: list[str]) -> bool:
    """Validate recipient count and basic format.

    Args:
        recipients: List of recipient email addresses

    Returns:
        bool: True if valid, False otherwise

    Rules:
        - Must be non-empty list
        - Between 1-50 recipients (reasonable limits)
        - Each recipient must contain @ and be at least 5 chars
    """
    if not recipients or not isinstance(recipients, list):
        return False

    # Check count limits
    if not (1 <= len(recipients) <= 50):
        return False

    # Basic format check for each recipient
    for recipient in recipients:
        if not recipient or not isinstance(recipient, str):
            return False
        if "@" not in recipient or len(recipient.strip()) < 5:
            return False

    return True
