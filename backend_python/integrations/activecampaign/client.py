"""ActiveCampaign API client for syncing contacts on signup.

Minimal wrapper around the ActiveCampaign v3 Contacts API. Designed to be
fire-and-forget from the caller's perspective: all errors are returned as
a ContactSyncResult rather than raised so the signup flow is never blocked
by a marketing-system outage.

Docs: https://developers.activecampaign.com/reference/create-a-contact-new
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API_TIMEOUT_SECONDS = 5.0
CONTACTS_PATH = "/api/3/contacts"


def _mask_email(email: str) -> str:
    """Mask an email for log output: alice@example.com → a***@example.com.

    Keeps the domain intact (useful for log-based debugging of domain-specific
    delivery issues) while avoiding full-PII retention in CloudWatch.
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    head = local[:1] if local else ""
    return f"{head}***@{domain}"


@dataclass(frozen=True)
class ContactSyncResult:
    """Outcome of a contact-sync attempt.

    success is True when ActiveCampaign accepted the contact (HTTP 2xx) or
    reported it already exists (HTTP 422 duplicate) — from our side both
    mean "the contact is in ActiveCampaign", which is the goal.
    """

    success: bool
    status_code: int | None = None
    error_message: str | None = None


class ActiveCampaignClient:
    """Minimal async client for ActiveCampaign v3 Contacts API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        if not api_url:
            raise ValueError("ActiveCampaign api_url is required")
        if not api_key:
            raise ValueError("ActiveCampaign api_key is required")
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    async def create_contact(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> ContactSyncResult:
        """Create (or no-op sync) a contact in ActiveCampaign.

        Returns a ContactSyncResult rather than raising. 422 duplicates are
        treated as success because the contact is present in AC, which is
        the only thing the caller cares about.
        """
        if not email:
            return ContactSyncResult(success=False, error_message="email is required")

        url = f"{self._api_url}{CONTACTS_PATH}"
        payload: dict[str, dict[str, str]] = {
            "contact": {"email": email},
        }
        if first_name:
            payload["contact"]["firstName"] = first_name
        if last_name:
            payload["contact"]["lastName"] = last_name

        headers = {
            "Api-Token": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            logger.warning(
                f"[ActiveCampaign] Timeout syncing {_mask_email(email)}: {e}"
            )
            return ContactSyncResult(success=False, error_message=f"timeout: {e}")
        except httpx.HTTPError as e:
            logger.warning(
                f"[ActiveCampaign] HTTP error syncing {_mask_email(email)}: {e}"
            )
            return ContactSyncResult(success=False, error_message=f"http error: {e}")

        status = response.status_code
        masked = _mask_email(email)
        if 200 <= status < 300:
            logger.info(f"[ActiveCampaign] Created contact {masked} (status {status})")
            return ContactSyncResult(success=True, status_code=status)

        if status == 422:
            # ActiveCampaign returns 422 when the email already exists.
            # That's fine for our purposes — the contact is there.
            logger.info(
                f"[ActiveCampaign] Contact {masked} already exists (treated as success)"
            )
            return ContactSyncResult(success=True, status_code=status)

        body_preview = response.text[:500] if response.text else ""
        logger.error(
            f"[ActiveCampaign] Unexpected status {status} syncing {masked}: {body_preview}"
        )
        # error_message omits the body because AC echoes back the contact
        # payload (including email) in error responses.
        return ContactSyncResult(
            success=False,
            status_code=status,
            error_message=f"status {status}",
        )


_client_instance: ActiveCampaignClient | None = None
_client_disabled: bool = False


def get_activecampaign_client() -> ActiveCampaignClient | None:
    """Return a lazily-initialised singleton client, or None if not configured.

    When either ACTIVECAMPAIGN_API_URL or ACTIVECAMPAIGN_API_KEY is unset the
    integration is disabled and this function returns None. Callers MUST
    handle None to support dev/test environments without credentials.

    Lifecycle notes:
    - The client is cached for the process lifetime. Rotating the API key
      requires a process restart (ECS task redeploy). This is intentional:
      settings are resolved at first use and do not hot-reload.
    - The disabled state is also cached, so once we've observed missing
      credentials we short-circuit future calls without re-reading settings.
      `_reset_client_for_tests()` clears both caches.
    """
    global _client_instance, _client_disabled

    if _client_instance is not None:
        return _client_instance
    if _client_disabled:
        return None

    api_url = settings.ACTIVECAMPAIGN_API_URL
    api_key = settings.ACTIVECAMPAIGN_API_KEY

    if not api_url or not api_key:
        logger.info(
            "[ActiveCampaign] Integration disabled "
            "(ACTIVECAMPAIGN_API_URL / ACTIVECAMPAIGN_API_KEY not set)"
        )
        _client_disabled = True
        return None

    _client_instance = ActiveCampaignClient(api_url=api_url, api_key=api_key)
    return _client_instance


def _reset_client_for_tests() -> None:
    """Reset the singleton. Intended for unit tests only."""
    global _client_instance, _client_disabled
    _client_instance = None
    _client_disabled = False
