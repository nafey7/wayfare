"""Chat domain with AI-powered flight booking"""

from __future__ import annotations

import importlib
from typing import Any

from .enums import MessageSender
from .repository import (
    create_message,
    get_chat_messages,
    get_or_create_chat_conversation,
    get_user_sessions,
)
from .schemas import ChatHistoryResponse, ChatMessage, ChatRequest, ChatResponse

__all__ = [
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatService",
    "MessageSender",
    "chat_service",
    "create_message",
    "get_chat_messages",
    "get_or_create_chat_conversation",
    "get_user_sessions",
]


def __getattr__(name: str) -> Any:
    if name == "service":
        return importlib.import_module(f"{__name__}.service")
    if name == "ChatService":
        from .service import ChatService

        return ChatService
    if name == "chat_service":
        from .service import chat_service

        return chat_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
