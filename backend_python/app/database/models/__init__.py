"""MongoDB models for Voya application.

Domain types should be imported from their respective domains where possible.
Exports are lazy (PEP 562) so importing one model module does not execute every
other model module (e.g. ``transaction`` pulls payment/email/jinja2).

If code must rely on import-time side effects from a specific model submodule,
import that submodule directly instead of going through this package—lazy
attributes do not execute sibling modules until accessed.
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORT_CLASSES: dict[str, tuple[str, str]] = {
    "BookingEventModel": ("app.database.models.booking_event", "BookingEventModel"),
    "ChatsPythonModel": ("app.database.models.chats_python", "ChatsPythonModel"),
    "SessionModel": ("app.database.models.session", "SessionModel"),
    "TransactionModel": ("app.database.models.transaction", "TransactionModel"),
    "UserModel": ("app.database.models.user", "UserModel"),
}


def __getattr__(name: str) -> Any:
    if name in _EXPORT_CLASSES:
        mod_path, cls_name = _EXPORT_CLASSES[name]
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)
    if name == "PyObjectId":
        from app.database.types import PyObjectId

        return PyObjectId
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BookingEventModel",
    "ChatsPythonModel",
    "PyObjectId",
    "SessionModel",
    "TransactionModel",
    "UserModel",
]
