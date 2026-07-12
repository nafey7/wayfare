"""Revolut Merchant API client.

Handles HTTP requests to Revolut Merchant API for order creation, validation,
refunds, and payouts.
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RevolutClient:
    """Client for Revolut Merchant API operations."""

    def __init__(self) -> None:
        """Initialize Revolut client with API configuration."""
        # Revolut Merchant API base URL from environment variable
        # Config handles defaults based on ENVIRONMENT
        self.base_url = settings.REVOLUT_API_BASE_URL

        self.api_key = settings.REVOLUT_API_KEY
        if not self.api_key:
            logger.warning("REVOLUT_API_KEY not configured")

        # Standard timeout for API requests
        self.timeout = httpx.Timeout(30.0)
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for Revolut API requests.

        Returns:
            Headers dictionary with authorization and API version
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Revolut-Api-Version": "2025-10-16",
        }

    async def create_order(
        self,
        amount: int,
        currency: str,
        customer: dict[str, str] | None = None,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        industry_type: str | None = None,
        booking_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Revolut order.

        Args:
            amount: Order amount in minor units (cents)
            currency: Currency code (ISO 4217, e.g., "USD", "EUR")
            customer: Customer object with email and full_name (optional)
            description: Order description (optional)
            metadata: Custom metadata (optional)
            industry_type: Industry type for industry_data (e.g., "airline", "lodging") - required for certain industries

        Returns:
            Order object with id, public_id, checkout_url, etc.

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/orders"
        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency.upper(),
        }

        if customer:
            payload["customer"] = customer
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata

        # Add industry_data if industry_type is provided
        # Required for airlines, hotels, car rentals, etc.
        if industry_type:
            industry_data: dict[str, Any] = {
                "type": industry_type,
            }
            # For airline/lodging orders, booking_id identifies the booking
            if booking_id and industry_type in ("airline", "lodging"):
                industry_data["booking_id"] = booking_id
            payload["industry_data"] = industry_data

        self.logger.info(f"Creating Revolut order: {amount} {currency}")
        if industry_type:
            self.logger.info(f"  Industry type: {industry_type}")
            if booking_id:
                self.logger.info(f"  Booking ID: {booking_id}")

        # Log the full payload for debugging (excluding sensitive data)
        self.logger.debug(f"Order creation payload: {payload}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            order_data = response.json()

        # Log the FULL direct response from Revolut API (for debugging)
        self.logger.info("=" * 80)
        self.logger.info("📦 REVOLUT API DIRECT RESPONSE (Create Order):")
        self.logger.info(f"Full response: {order_data}")
        self.logger.info("=" * 80)

        order_id = order_data.get("id")
        token = order_data.get("token")
        order_state = order_data.get("state")
        self.logger.info(f"✅ Revolut order created: {order_id}")
        self.logger.info(f"  Token: {token if token else 'MISSING'}")
        self.logger.info(f"  State: {order_state}")

        # Log full response for debugging (excluding sensitive data)
        self.logger.debug(
            f"Revolut order response keys: {list(order_data.keys())}, "
            f"has checkout_url: {'checkout_url' in order_data}, "
            f"has token: {'token' in order_data}, "
            f"has industry_data: {'industry_data' in order_data}, "
            f"state: {order_state}"
        )

        # Log industry_data if present
        if "industry_data" in order_data:
            self.logger.debug(f"  Industry data: {order_data.get('industry_data')}")

        # Verify token is present (critical for widget initialization)
        if not token:
            self.logger.error("  ⚠️  Token missing from Revolut API response!")
            self.logger.error(f"  Available keys: {list(order_data.keys())}")
        else:
            self.logger.info(f"  ✅ Token extracted successfully: {token}")

        # Warn if order state is not pending (might indicate an issue)
        if order_state and order_state != "pending":
            self.logger.warning(
                f"  ⚠️  Order state is '{order_state}' (expected 'pending' for new orders)"
            )

        return order_data

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Retrieve a Revolut order by ID.

        Args:
            order_id: Revolut order ID (public_id or internal id)

        Returns:
            Order object with current status and details

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/orders/{order_id}"

        self.logger.info(f"Retrieving Revolut order: {order_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel a Revolut order (e.g. pending checkout not completed).

        Merchant API: POST /orders/{order_id}/cancel for orders that can still be voided.

        Args:
            order_id: Revolut order ID

        Returns:
            Order object including updated state (typically cancelled)

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/orders/{order_id}/cancel"
        self.logger.info(f"Cancelling Revolut order: {order_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

        self.logger.info(
            f"✅ Revolut order cancelled: {order_id} (state={data.get('state')})"
        )
        return data

    async def create_refund(
        self,
        order_id: str,
        amount: int | None = None,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a refund for a Revolut order.

        Args:
            order_id: Revolut order ID to refund
            amount: Refund amount in minor units (optional, defaults to full refund)
            description: Refund description (optional)
            metadata: Custom metadata (optional)

        Returns:
            Refund object with id, amount, status, etc.

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/refunds"
        payload: dict[str, Any] = {
            "order_id": order_id,
        }

        if amount:
            payload["amount"] = amount
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata

        self.logger.info(f"Creating Revolut refund for order: {order_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            refund_data = response.json()

        self.logger.info(f"✅ Revolut refund created: {refund_data.get('id')}")
        return refund_data

    async def create_payout(
        self,
        amount: int,
        currency: str,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a payout to a merchant account.

        Args:
            amount: Payout amount in minor units (cents)
            currency: Currency code (ISO 4217)
            description: Payout description (optional)
            metadata: Custom metadata (optional)

        Returns:
            Payout object with id, amount, status, etc.

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/payouts"
        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency.upper(),
        }

        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata

        self.logger.info(f"Creating Revolut payout: {amount} {currency}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            payout_data = response.json()

        self.logger.info(f"✅ Revolut payout created: {payout_data.get('id')}")
        return payout_data
