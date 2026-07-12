"""
Conftest for test_domains directory.

Dependencies:
    The google-genai package is required for imports to work (see requirements.txt).
    If you get ImportError for google modules, update your virtual environment:

        pip install -r requirements.txt

Testing approach:
    Tests mock specific methods (e.g., intent_recognizer.recognize) rather than
    replacing entire packages. This requires google-genai to be installed but
    doesn't make actual API calls during tests.
"""

# No sys.modules manipulation needed - google-genai is a required dependency
# and tests mock at the method level to avoid real API calls.

import pytest


@pytest.fixture(autouse=True)
def _reset_chat_service_dedupe_cache():
    """Reset chat service dedupe cache between tests so reused chat_ids don't collide."""
    from app.domains.chat import service as chat_service_module

    chat_service_module._recent_messages.clear()
    yield
    chat_service_module._recent_messages.clear()
