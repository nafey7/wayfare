"""Chat domain enums"""

from enum import StrEnum


class MessageSender(StrEnum):
    """Message sender types"""

    USER = "USER"
    BOT = "BOT"
    SYSTEM = "SYSTEM"
    AI = "AI"  # Alias for BOT
