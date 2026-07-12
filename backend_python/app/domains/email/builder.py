"""Email builder class - business logic for creating emails.

This file contains the EmailBuilder class that combines content with data to create complete emails.
"""

import hashlib
import logging
import re
import urllib.parse
from collections.abc import Callable
from typing import Any, ClassVar

from app.core.config import settings
from app.domains.common import format_money

from .constants import (
    BUTTON_COLOR_HEX_VALUES,
    DEFAULT_GREETING_WITH_NAME,
    DEFAULT_GREETING_WITHOUT_NAME,
    DEFAULT_TICKET_TIME_LIMIT,
    FRONTEND_URL_LOCAL,
    FRONTEND_URL_PRODUCTION,
)
from .content import (
    ACCOUNT_BANNED_BUTTON_TEXT,
    ACCOUNT_BANNED_CONTENT,
    ACCOUNT_BANNED_SUBJECT,
    ACCOUNT_BANNED_TITLE,
    ACCOUNT_DELETED_BUTTON_TEXT,
    ACCOUNT_DELETED_CONTENT,
    ACCOUNT_DELETED_SUBJECT,
    ACCOUNT_DELETED_TITLE,
    ACCOUNT_REACTIVATED_BUTTON_TEXT,
    ACCOUNT_REACTIVATED_CONTENT,
    ACCOUNT_REACTIVATED_SUBJECT,
    ACCOUNT_REACTIVATED_TITLE,
    ACCOUNT_SUSPENDED_BUTTON_TEXT,
    ACCOUNT_SUSPENDED_CONTENT,
    ACCOUNT_SUSPENDED_SUBJECT,
    ACCOUNT_SUSPENDED_TITLE,
    BOOKING_CANCELLED_BUTTON_TEXT,
    BOOKING_CANCELLED_CONTENT,
    BOOKING_CANCELLED_SUBJECT_TEMPLATE,
    BOOKING_CANCELLED_TITLE,
    BOOKING_CONFIRMATION_FSC_BUTTON_TEXT,
    BOOKING_CONFIRMATION_FSC_CONTENT,
    BOOKING_CONFIRMATION_FSC_SUBJECT_TEMPLATE,
    BOOKING_CONFIRMATION_FSC_TITLE,
    BOOKING_CONFIRMATION_LCC_BUTTON_TEXT,
    BOOKING_CONFIRMATION_LCC_CONTENT,
    BOOKING_CONFIRMATION_LCC_SUBJECT_TEMPLATE,
    BOOKING_CONFIRMATION_LCC_TITLE,
    BOOKING_FAILED_BUTTON_TEXT,
    BOOKING_FAILED_CONTENT,
    BOOKING_FAILED_SUBJECT,
    BOOKING_FAILED_TITLE,
    EMAIL_VERIFIED_BUTTON_TEXT,
    EMAIL_VERIFIED_CONTENT,
    EMAIL_VERIFIED_SUBJECT,
    EMAIL_VERIFIED_TITLE,
    HOTEL_BOOKING_CONFIRMATION_BUTTON_TEXT,
    HOTEL_BOOKING_CONFIRMATION_CONTENT,
    HOTEL_BOOKING_CONFIRMATION_SUBJECT_TEMPLATE,
    HOTEL_BOOKING_CONFIRMATION_TITLE,
    PASSWORD_CHANGED_BUTTON_TEXT,
    PASSWORD_CHANGED_CONTENT,
    PASSWORD_CHANGED_SUBJECT,
    PASSWORD_CHANGED_TITLE,
    PASSWORD_RESET_BUTTON_TEXT,
    PASSWORD_RESET_CONTENT,
    PASSWORD_RESET_SUBJECT,
    PASSWORD_RESET_TITLE,
    PAYMENT_CONFIRMATION_BUTTON_TEXT,
    PAYMENT_CONFIRMATION_CONTENT,
    PAYMENT_CONFIRMATION_SUBJECT_TEMPLATE,
    PAYMENT_CONFIRMATION_TITLE,
    PII_VERIFICATION_OTP_BUTTON_TEXT,
    PII_VERIFICATION_OTP_CONTENT,
    PII_VERIFICATION_OTP_SUBJECT,
    PII_VERIFICATION_OTP_TITLE,
    REGISTRATION_SETUP_BUTTON_TEXT,
    REGISTRATION_SETUP_CONTENT,
    REGISTRATION_SETUP_SUBJECT,
    REGISTRATION_SETUP_TITLE,
    TICKET_CONFIRMATION_BUTTON_TEXT,
    TICKET_CONFIRMATION_CONTENT,
    TICKET_CONFIRMATION_SUBJECT_TEMPLATE,
    TICKET_CONFIRMATION_TITLE,
    WELCOME_BUTTON_TEXT,
    WELCOME_CONTENT,
    WELCOME_SUBJECT,
    WELCOME_TITLE,
)
from .enums import EmailType, UIButtonColor
from .schemas import EmailSpec, RenderedEmail
from .template import EMAIL_BUTTON_SECTION, EMAIL_TEMPLATE_HTML

logger = logging.getLogger(__name__)


# ============================================================
# EMAIL BUILDER CLASS
# ============================================================


class EmailBuilder:
    """Email builder for all email types with business logic."""

    # Template cache
    _template_cache: ClassVar[dict[str, tuple[str, str]]] = {}

    @classmethod
    def build_email(
        cls,
        email_type: EmailType | str,
        recipient_email: str,
        context: dict[str, Any],
        revalidate_response: Any | None = None,
        booking_request: Any | None = None,
        trip_details: Any | None = None,
    ) -> RenderedEmail | None:
        """Build complete email with rendered template.

        This is the main entry point that:
        1. Gets email data from specific builders
        2. Applies the template to create final email

        Args:
            email_type: Type of email to build
            recipient_email: Recipient's email address
            context: Context data for email content
            revalidate_response: Response from fare revalidation with pricing
            booking_request: Original booking request with passenger info

        Returns:
            CompleteEmail with metadata and rendered content, or None if failed
        """
        # Enrich context with fare information from trip_details or revalidate response
        enriched_context = cls._enrich_context_with_fare_info(
            context, revalidate_response, booking_request, trip_details
        )

        # Get email data from appropriate builder
        email_spec = cls._get_email_spec(email_type, recipient_email, enriched_context)
        if not email_spec:
            return None

        # Apply template to create complete email
        return cls._render_email_from_spec(email_spec, enriched_context)

    @classmethod
    def _extract_fare_from_trip_details(
        cls, trip_details: Any
    ) -> dict[str, Any] | None:
        """Extract fare from LCC trip details.

        Args:
            trip_details: Trip details with complete fare breakdown

        Returns:
            Dict with total_fare, currency, tickets_issued or None if extraction fails
        """
        if not trip_details or not hasattr(trip_details, "pricing"):
            return None

        try:
            fare_totals = trip_details.pricing.fare_totals
            if hasattr(fare_totals, "total_fare"):
                total_fare = fare_totals.total_fare
                result = {
                    "total_fare": float(total_fare.amount),
                    "currency": total_fare.currency,
                    "tickets_issued": True,  # Trip details = tickets issued
                }

                logger.info(
                    f"🔗 [Context] Enriched email context from trip_details: "
                    f"{total_fare.amount} {total_fare.currency} (LCC)"
                )
                return result
        except (AttributeError, TypeError) as e:
            logger.warning(
                f"🔗 [Context] Failed to extract fare from trip_details: {e}"
            )

        return None

    @classmethod
    def _try_path(cls, obj: Any, *path_parts: str) -> Any | None:
        """Safely traverse nested attributes.

        Args:
            obj: Object to traverse
            path_parts: Attribute names to traverse (e.g., 'pricing', 'fare_totals', 'total_fare')

        Returns:
            Value at the path or None if any attribute is missing
        """
        current = obj
        for attr in path_parts:
            if not hasattr(current, attr):
                return None
            current = getattr(current, attr)
        return current

    @classmethod
    def _extract_fare_from_revalidate(
        cls, revalidate_response: Any
    ) -> dict[str, Any] | None:
        """Extract fare from GDS revalidate response.

        Args:
            revalidate_response: Response with fare/pricing information

        Returns:
            Dict with total_fare, currency, tickets_issued or None if extraction fails
        """
        if not revalidate_response or not hasattr(
            revalidate_response, "validated_fare_itineraries"
        ):
            return None

        # Debug logging
        logger.info(
            f"🔍 [Context] revalidate_response type: {type(revalidate_response)}"
        )
        if hasattr(revalidate_response, "validated_fare_itineraries"):
            itineraries = revalidate_response.validated_fare_itineraries
            logger.info(
                f"🔍 [Context] validated_fare_itineraries: "
                f"{'empty/None' if not itineraries else f'length {len(itineraries)}'}"
            )

        try:
            itinerary = revalidate_response.validated_fare_itineraries[0]
            logger.info("🔍 [Context] Found itinerary, checking for pricing...")

            # Try standard path: itinerary.updated_pricing.validated_fare_totals.total_fare
            total_fare = cls._try_path(
                itinerary, "updated_pricing", "validated_fare_totals", "total_fare"
            )
            if total_fare:
                result = {
                    "total_fare": float(total_fare.amount),
                    "currency": total_fare.currency,
                    "tickets_issued": False,  # Revalidate = payment pending
                }
                logger.info(
                    f"🔗 [Context] Enriched email context from revalidate_response: "
                    f"{total_fare.amount} {total_fare.currency} (GDS)"
                )
                return result

            # Try legacy path: itinerary.pricing.fare_totals.total_fare
            total_fare = cls._try_path(
                itinerary, "pricing", "fare_totals", "total_fare"
            )
            if total_fare:
                result = {
                    "total_fare": float(total_fare.amount),
                    "currency": total_fare.currency,
                    "tickets_issued": False,
                }
                logger.info(
                    f"🔗 [Context] Enriched email context from legacy revalidate path: "
                    f"{total_fare.amount} {total_fare.currency} (GDS)"
                )
                return result

            # Try direct itinerary.total_fare
            total_fare = cls._try_path(itinerary, "total_fare")
            if total_fare:
                result = {
                    "total_fare": float(total_fare.amount),
                    "currency": total_fare.currency,
                    "tickets_issued": False,
                }
                logger.info(
                    f"🔗 [Context] Found fare via itinerary.total_fare: "
                    f"{total_fare.amount} {total_fare.currency}"
                )
                return result

            # Try fare_details path
            if hasattr(itinerary, "fare_details") and hasattr(
                itinerary.fare_details, "total_fare_amount"
            ):
                total_fare_amount = itinerary.fare_details.total_fare_amount
                currency = getattr(itinerary.fare_details, "currency", "USD")
                result = {
                    "total_fare": float(total_fare_amount),
                    "currency": currency,
                    "tickets_issued": False,
                }
                logger.info(
                    f"🔗 [Context] Found fare via fare_details: "
                    f"{total_fare_amount} {currency}"
                )
                return result

            logger.warning(
                "🔍 [Context] No fare information found in any expected locations"
            )

        except (AttributeError, IndexError, TypeError) as e:
            logger.warning(
                f"🔗 [Context] Failed to extract fare from revalidate_response: {e}"
            )

        return None

    @classmethod
    def _get_fare_fallback(cls, context: dict[str, Any]) -> dict[str, Any]:
        """Return fallback fare data when no fare information is available.

        Args:
            context: Original context that may have tickets_issued set

        Returns:
            Dict with zero fare and default currency (preserves existing currency if present)
        """
        # Preserve existing currency from context (e.g., from Stripe webhook for payment confirmations)
        existing_currency = context.get("currency", "USD")

        fallback = {
            "total_fare": 0.0,
            "currency": existing_currency,
        }

        # Don't override tickets_issued if already set in context
        if "tickets_issued" not in context:
            fallback["tickets_issued"] = False

        logger.warning(
            f"🔗 [Context] No fare information available, using fallback: 0.00 {existing_currency}"
        )

        return fallback

    @classmethod
    def _enrich_context_with_fare_info(
        cls,
        context: dict[str, Any],
        revalidate_response: Any | None = None,
        _booking_request: Any | None = None,
        trip_details: Any | None = None,
    ) -> dict[str, Any]:
        """Enrich context with fare information from trip_details or revalidate response.

        Args:
            context: Original email context
            revalidate_response: Response with fare/pricing information
            booking_request: Original booking request
            trip_details: Trip details with complete fare breakdown (LCC)

        Returns:
            Context enriched with total_fare, currency, and tickets_issued flag
        """
        enriched = context.copy()

        # Priority 1: Extract from trip_details (LCC bookings)
        fare_data = cls._extract_fare_from_trip_details(trip_details)
        if fare_data:
            return {**enriched, **fare_data}

        # Priority 2: Extract from revalidate response (GDS bookings)
        fare_data = cls._extract_fare_from_revalidate(revalidate_response)
        if fare_data:
            return {**enriched, **fare_data}

        # Fallback: no fare data available
        # _get_fare_fallback preserves existing currency from context (e.g., from Stripe webhook)
        fallback_data = cls._get_fare_fallback(enriched)
        return {**enriched, **fallback_data}

    @classmethod
    def _get_email_spec(
        cls,
        email_type: EmailType | str,
        recipient_email: str,
        context: dict[str, Any],
    ) -> EmailSpec | None:
        """Get email data from appropriate builder."""
        # Add recipient email to context for builders that need it
        context_with_email = {**context, "email": recipient_email}

        # Handle both string and enum types
        if isinstance(email_type, str):
            try:
                # Convert string to enum - email types are lowercase in the enum
                email_type = EmailType(email_type.lower())
            except ValueError:
                logger.error(f"Invalid email type: {email_type}")
                return None

        # Get builder and execute
        builders = cls._get_email_builders()
        if email_type in builders:
            # Call the builder method with context
            return builders[email_type](context_with_email)

        return None

    @classmethod
    def _render_email_from_spec(
        cls, email_spec: EmailSpec, context: dict
    ) -> RenderedEmail:
        """Render email template from specification."""
        # Create greeting
        first_name = context.get("first_name")
        greeting = (
            DEFAULT_GREETING_WITH_NAME.format(first_name=first_name)
            if first_name
            else DEFAULT_GREETING_WITHOUT_NAME
        )

        # Render email
        html_content, text_content = cls._render_email(
            title=email_spec.title,
            greeting=greeting,
            body_content=email_spec.body_content,
            button_url=email_spec.button_url,
            button_text=email_spec.button_text,
            button_color=email_spec.button_color,
            footer_text=getattr(
                settings,
                "EMAIL_FOOTER_TEXT",
                "© 2025 Voya AI, Inc. All rights reserved.",
            ),
        )

        return RenderedEmail(
            spec=email_spec,
            rendered_html=html_content,
            rendered_text=text_content,
        )

    # ============================================================
    # RENDERING METHODS
    # ============================================================

    @classmethod
    def _render_email(
        cls,
        title: str,
        greeting: str,
        body_content: str,
        button_text: str,
        button_url: str | None,
        button_color: str,
        footer_text: str | None = None,
    ) -> tuple[str, str]:
        """Render email with template and caching."""

        # Create cache key - use hash of full body_content so variable content (OTP, tokens)
        # produces unique keys. body_content[:50] caused PII OTP emails to share cache and
        # show the first OTP in all subsequent emails. MD5 used for non-security hashing only.
        body_hash = hashlib.md5(
            body_content.encode(), usedforsecurity=False
        ).hexdigest()
        cache_key = f"{title}:{greeting}:{body_hash}:{button_text}:{button_url}"

        logger.info(f"🎨 [Template] Cache key: {cache_key[:100]}...")
        logger.info(f"🎨 [Template] Button URL in template: {button_url}")

        if cache_key not in cls._template_cache:
            logger.info("🎨 [Template] Generating new template (not in cache)")
        else:
            logger.info("🎨 [Template] Using cached template")

        if cache_key not in cls._template_cache:
            # Conditionally include button section based on button_url presence
            button_section_html = ""
            if button_url:
                button_section_html = EMAIL_BUTTON_SECTION.format(
                    button_url=button_url,
                    button_text=button_text,
                )

            # Apply template with conditional button section
            html_content = EMAIL_TEMPLATE_HTML.format(
                title=title,
                greeting=greeting,
                body_content=body_content,
                button_section=button_section_html,
                button_color=button_color,
                footer_text=footer_text,
            )

            # Create text version
            text_lines = [greeting]
            # Parse body_content to extract text (remove HTML tags)
            text_content_lines = (
                re.sub(r"<[^>]+>", "", body_content).strip().split("\n")
            )
            text_lines.extend(
                [line.strip() for line in text_content_lines if line.strip()]
            )
            # Only add button line if URL is provided
            if button_url:
                text_lines.extend(
                    [
                        "",
                        f"{button_text}: {button_url}",
                        "",
                        footer_text or "",
                    ]
                )
            else:
                text_lines.extend(
                    [
                        "",
                        footer_text or "",
                    ]
                )
            text_content = "\n".join(text_lines)

            cls._template_cache[cache_key] = (html_content, text_content)

        return cls._template_cache[cache_key]

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @classmethod
    def _get_base_url(cls) -> str:
        """Get base URL for links."""
        # Use FRONTEND_URL from settings first (respects environment configuration)
        if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
            logger.info(
                f"🔗 [URL] Using FRONTEND_URL from settings: {settings.FRONTEND_URL}"
            )
            return settings.FRONTEND_URL
        # Fallback to environment-specific defaults
        if settings.DEBUG:
            logger.info(f"🔗 [URL] Using DEBUG fallback: {FRONTEND_URL_LOCAL}")
            return FRONTEND_URL_LOCAL
        logger.info(f"🔗 [URL] Using production fallback: {FRONTEND_URL_PRODUCTION}")
        return FRONTEND_URL_PRODUCTION

    @classmethod
    def _get_debug_url(cls, action: str, **params) -> str:
        """Get debug URL for development API tester."""
        base_url = getattr(
            settings, "API_TESTER_BASE_URL", "http://localhost:8000/dev/api-tester.html"
        )
        query_params = f"action={action}"
        for key, value in params.items():
            if value:
                encoded_value = urllib.parse.quote(str(value))
                query_params += f"&{key}={encoded_value}"
        return f"{base_url}?{query_params}"

    @classmethod
    def _get_frontend_url(cls, path: str) -> str:
        """Get frontend URL for production links."""
        return f"{cls._get_base_url()}{path}"

    @classmethod
    def _generate_booking_auth_token(cls, user_id: str) -> str | None:
        """Generate short-lived JWT for email link auth (view tickets / payment).

        12 hours expiry - long enough for users to click email links.

        Returns:
            JWT string or None if generation fails.
        """
        try:
            from datetime import UTC, datetime

            import jwt

            payload = {
                "user_id": user_id,
                "type": "booking_auth",
                "exp": datetime.now(UTC).timestamp() + 43200,  # 12 hours
            }
            return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        except Exception as token_error:
            logger.warning(f"Failed to generate booking token: {token_error}")
            return None

    @classmethod
    def _get_authenticated_frontend_url(
        cls, path: str, user_id: str | None = None
    ) -> str:
        """Frontend-v2 URL with optional auth token for email links.

        Uses _get_frontend_url for base; appends auth_token query param when user_id
        is provided so only the recipient can access the page.
        """
        base = cls._get_frontend_url(path)
        if not user_id:
            return base
        token = cls._generate_booking_auth_token(user_id)
        if not token:
            return base
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}auth_token={token}"

    @classmethod
    def _get_payment_page_url(
        cls, voya_booking_reference: str, user_id: str | None = None
    ) -> str:
        """Get payment page URL for GDS booking confirmation emails.

        Points to frontend-v2 route /flights/payment/<ref> with optional auth token.
        """
        return cls._get_authenticated_frontend_url(
            f"/flights/payment/{voya_booking_reference}", user_id=user_id
        )

    # ============================================================
    # EMAIL BUILDER MAPPING
    # ============================================================

    @classmethod
    def _get_email_builders(
        cls,
    ) -> dict[EmailType, Callable[[dict[str, Any] | None], EmailSpec]]:
        """Mapping of email types to their builders."""
        return {
            # Authentication & Onboarding
            EmailType.WELCOME: cls._build_welcome_email,
            EmailType.EMAIL_VERIFIED: cls._build_email_verified,
            EmailType.REGISTRATION_SETUP: cls._build_registration_setup,
            # Security & Password
            EmailType.PASSWORD_RESET: cls._build_password_reset,
            EmailType.PASSWORD_CHANGED: cls._build_password_changed,
            EmailType.PII_VERIFICATION_OTP: cls._build_pii_verification_otp,
            # Account Management
            EmailType.ACCOUNT_DELETED: cls._build_account_deleted,
            EmailType.ACCOUNT_SUSPENDED: cls._build_account_suspended,
            EmailType.ACCOUNT_BANNED: cls._build_account_banned,
            EmailType.ACCOUNT_REACTIVATED: cls._build_account_reactivated,
            # Booking & Travel
            EmailType.BOOKING_CONFIRMATION: cls._build_booking_confirmation,
            EmailType.PAYMENT_CONFIRMATION: cls._build_payment_confirmation,
            EmailType.TICKET_ISSUED: cls._build_ticket_issued,
            EmailType.BOOKING_CANCELLED: cls._build_booking_cancelled,
        }

    # ============================================================
    # EMAIL BUILDERS - AUTHENTICATION & ONBOARDING
    # ============================================================

    @classmethod
    def _build_welcome_email(cls, _context: dict[str, Any] | None = None) -> EmailSpec:
        """Build welcome email."""
        return EmailSpec(
            subject=WELCOME_SUBJECT,
            title=WELCOME_TITLE,
            body_content=WELCOME_CONTENT,
            button_url=cls._get_frontend_url("/flights/search"),
            button_text=WELCOME_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Welcome",
        )

    @classmethod
    def _build_email_verified(cls, _context: dict[str, Any] | None = None) -> EmailSpec:
        """Build email verified notification."""
        return EmailSpec(
            subject=EMAIL_VERIFIED_SUBJECT,
            title=EMAIL_VERIFIED_TITLE,
            body_content=EMAIL_VERIFIED_CONTENT,
            button_url=cls._get_frontend_url("/profile"),
            button_text=EMAIL_VERIFIED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Email Verified",
        )

    @classmethod
    def _build_registration_setup(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build registration setup email."""
        if not context:
            raise ValueError("Context required for registration setup email")
        setup_token = context.get("setup_token")
        email = context.get("email")

        if not setup_token:
            raise ValueError("setup_token required for registration setup email")
        if not email:
            raise ValueError("email required for registration setup email")

        # Build setup URL - always use frontend URL for better user experience
        base_url = cls._get_base_url()
        encoded_email = urllib.parse.quote(email)
        setup_url = f"{base_url}/complete-registration?token={setup_token}&email={encoded_email}"

        logger.info(f"🔗 [URL] Generated registration setup URL: {setup_url}")
        logger.info(f"🔗 [URL] Base URL: {base_url}")
        logger.info(f"🔗 [URL] Token: {setup_token[:8]}...")

        # Format content with expiry hours (72 hours for registration)
        formatted_content = REGISTRATION_SETUP_CONTENT.format(expiry_hours=72)

        return EmailSpec(
            subject=REGISTRATION_SETUP_SUBJECT,
            title=REGISTRATION_SETUP_TITLE,
            body_content=formatted_content,
            button_url=setup_url,
            button_text=REGISTRATION_SETUP_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Registration",
        )

    # ============================================================
    # EMAIL BUILDERS - SECURITY & PASSWORD
    # ============================================================

    @classmethod
    def _build_password_reset(cls, context: dict[str, Any] | None = None) -> EmailSpec:
        """Build password reset email."""
        if not context:
            raise ValueError("Context required for password reset email")
        reset_token = context.get("reset_token")
        if not reset_token:
            raise ValueError("reset_token required for password reset email")

        # Build reset URL - always use frontend URL for better user experience
        reset_url = cls._get_frontend_url(f"/reset-password?token={reset_token}")

        return EmailSpec(
            subject=PASSWORD_RESET_SUBJECT,
            title=PASSWORD_RESET_TITLE,
            body_content=PASSWORD_RESET_CONTENT,
            button_url=reset_url,
            button_text=PASSWORD_RESET_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.ORANGE.value],
            email_type_name="Password reset",
        )

    @classmethod
    def _build_password_changed(
        cls, _context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build password changed notification."""
        return EmailSpec(
            subject=PASSWORD_CHANGED_SUBJECT,
            title=PASSWORD_CHANGED_TITLE,
            body_content=PASSWORD_CHANGED_CONTENT,
            button_url=cls._get_frontend_url("/support"),
            button_text=PASSWORD_CHANGED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.RED.value],
            email_type_name="Password changed",
        )

    @classmethod
    def _build_pii_verification_otp(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build PII verification OTP email (no button, just code)."""
        if not context or "otp" not in context:
            raise ValueError("Context with otp required for PII verification OTP email")
        otp = context["otp"]
        body_content = PII_VERIFICATION_OTP_CONTENT.format(otp=otp)
        return EmailSpec(
            subject=PII_VERIFICATION_OTP_SUBJECT,
            title=PII_VERIFICATION_OTP_TITLE,
            body_content=body_content,
            button_url=cls._get_frontend_url("/profile"),
            button_text=PII_VERIFICATION_OTP_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="PII Verification OTP",
        )

    # ============================================================
    # EMAIL BUILDERS - ACCOUNT MANAGEMENT
    # ============================================================

    @classmethod
    def _build_account_deleted(
        cls, _context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build account deleted notification."""
        return EmailSpec(
            subject=ACCOUNT_DELETED_SUBJECT,
            title=ACCOUNT_DELETED_TITLE,
            body_content=ACCOUNT_DELETED_CONTENT,
            button_url=cls._get_frontend_url("/"),
            button_text=ACCOUNT_DELETED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GRAY.value],
            email_type_name="Account Deleted",
        )

    @classmethod
    def _build_account_suspended(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build account suspended notification."""
        context = context or {}
        reason = context.get("reason")
        reason_block = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""

        content = ACCOUNT_SUSPENDED_CONTENT.format(reason=reason_block)
        return EmailSpec(
            subject=ACCOUNT_SUSPENDED_SUBJECT,
            title=ACCOUNT_SUSPENDED_TITLE,
            body_content=content,
            button_url=cls._get_frontend_url("/support"),
            button_text=ACCOUNT_SUSPENDED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.YELLOW.value],
            email_type_name="Account Suspended",
        )

    @classmethod
    def _build_account_banned(cls, context: dict[str, Any] | None = None) -> EmailSpec:
        """Build account banned notification."""
        context = context or {}
        reason = context.get("reason")
        reason_block = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""

        content = ACCOUNT_BANNED_CONTENT.format(reason=reason_block)
        return EmailSpec(
            subject=ACCOUNT_BANNED_SUBJECT,
            title=ACCOUNT_BANNED_TITLE,
            body_content=content,
            button_url=cls._get_frontend_url("/support"),
            button_text=ACCOUNT_BANNED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.RED.value],
            email_type_name="Account Banned",
        )

    @classmethod
    def _build_account_reactivated(
        cls, _context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build account reactivated notification."""
        return EmailSpec(
            subject=ACCOUNT_REACTIVATED_SUBJECT,
            title=ACCOUNT_REACTIVATED_TITLE,
            body_content=ACCOUNT_REACTIVATED_CONTENT,
            button_url=cls._get_frontend_url("/flights/search"),
            button_text=ACCOUNT_REACTIVATED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Account Reactivated",
        )

    # ============================================================
    # EMAIL BUILDERS - BOOKING & TRAVEL
    # ============================================================

    @classmethod
    def _build_booking_confirmation(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build booking confirmation email (flights or hotels)."""
        if not context:
            raise ValueError("Context required for booking confirmation email")
        voya_booking_reference = context.get("voya_booking_reference")

        if not voya_booking_reference:
            raise ValueError("voya_booking_reference required for booking confirmation")

        # Check if this is a hotel booking
        booking_details = context.get("booking_details", {})
        is_hotel_booking = (
            "hotel_id" in booking_details or "check_in" in booking_details
        )

        if is_hotel_booking:
            # Hotel booking confirmation
            supplier_confirmation_num = context.get("external_booking_reference", "N/A")
            hotel_name = booking_details.get("hotel_name", "Your Hotel")
            check_in = booking_details.get(
                "check_in", booking_details.get("check_in_date", "N/A")
            )
            check_out = booking_details.get(
                "check_out", booking_details.get("check_out_date", "N/A")
            )

            total_price = format_money(
                booking_details.get("total_price", booking_details.get("NetPrice", 0)),
                booking_details.get("currency", "USD"),
            )

            content = HOTEL_BOOKING_CONFIRMATION_CONTENT.format(
                voya_booking_reference=voya_booking_reference,
                supplier_confirmation_num=supplier_confirmation_num,
                hotel_name=hotel_name,
                check_in_date=check_in,
                check_out_date=check_out,
                total_price=total_price,
            )

            button_url = cls._get_authenticated_frontend_url(
                f"/hotels/bookings/{voya_booking_reference}",
                user_id=context.get("user_id"),
            )

            return EmailSpec(
                subject=HOTEL_BOOKING_CONFIRMATION_SUBJECT_TEMPLATE.format(
                    voya_booking_reference=voya_booking_reference
                ),
                title=HOTEL_BOOKING_CONFIRMATION_TITLE,
                body_content=content,
                button_url=button_url,
                button_text=HOTEL_BOOKING_CONFIRMATION_BUTTON_TEXT,
                button_color=BUTTON_COLOR_HEX_VALUES.get(
                    UIButtonColor.GREEN.value, "#4CAF50"
                ),
                email_type_name="Hotel Booking",
            )

        # Flight booking confirmation
        tickets_issued = context.get("tickets_issued")
        if tickets_issued is None:
            raise ValueError("tickets_issued required for flight booking confirmation")

        # Type narrowing for mypy after validation
        voya_booking_reference = str(voya_booking_reference)

        total_fare = format_money(
            context.get("total_fare"), context.get("currency", "USD")
        )

        if tickets_issued:
            # LCC - Tickets already issued
            cancellation_policy_text = context.get("cancellation_policy_text")

            # Process cancellation policy for email display (similar to ticket issued email)
            cancellation_policy_section = ""
            if cancellation_policy_text:
                # Check if text contains HTML tags
                import re

                html_tag_pattern = re.compile(r"<[^>]+>")
                contains_html = bool(html_tag_pattern.search(cancellation_policy_text))

                if contains_html:
                    # Contains HTML - use as-is
                    formatted_policy = cancellation_policy_text
                else:
                    # Plain text - escape HTML and convert newlines to <br>
                    from html import escape

                    escaped_text = escape(cancellation_policy_text)
                    formatted_policy = escaped_text.replace("\n", "<br>")

                cancellation_policy_section = f"""
<div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
    <h3 style="margin-top: 0; color: #e65100; font-size: 16px;">📋 Cancellation Policy</h3>
    <div style="font-size: 14px; line-height: 1.6; color: #333;">
        {formatted_policy}
    </div>
</div>
"""

            content = BOOKING_CONFIRMATION_LCC_CONTENT.format(
                voya_booking_reference=voya_booking_reference,
                total_fare=total_fare,
                cancellation_policy_section=cancellation_policy_section,
            )
            return EmailSpec(
                subject=BOOKING_CONFIRMATION_LCC_SUBJECT_TEMPLATE.format(
                    voya_booking_reference=voya_booking_reference
                ),
                title=BOOKING_CONFIRMATION_LCC_TITLE,
                body_content=content,
                button_url=cls._get_authenticated_frontend_url(
                    f"/flights/bookings/{voya_booking_reference}",
                    user_id=context.get("user_id"),
                ),
                button_text=BOOKING_CONFIRMATION_LCC_BUTTON_TEXT,
                button_color=BUTTON_COLOR_HEX_VALUES.get(
                    UIButtonColor.GREEN.value, "#4CAF50"
                ),
                email_type_name="Flight Booking",
            )
        # FSC - Booking confirmed, tickets pending
        ticket_time_limit = context.get("ticket_time_limit", DEFAULT_TICKET_TIME_LIMIT)
        user_id = context.get("user_id")  # Get user_id from context for auth token
        content = BOOKING_CONFIRMATION_FSC_CONTENT.format(
            voya_booking_reference=voya_booking_reference,
            total_fare=total_fare,
            ticket_time_limit=ticket_time_limit,
        )
        return EmailSpec(
            subject=BOOKING_CONFIRMATION_FSC_SUBJECT_TEMPLATE.format(
                voya_booking_reference=voya_booking_reference
            ),
            title=BOOKING_CONFIRMATION_FSC_TITLE,
            body_content=content,
            button_url=cls._get_payment_page_url(
                voya_booking_reference, user_id=user_id
            ),
            button_text=BOOKING_CONFIRMATION_FSC_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.BLUE.value],
            email_type_name="Flight Booking",
        )

    @classmethod
    def _build_ticket_issued(cls, context: dict[str, Any] | None = None) -> EmailSpec:
        """Build ticket issued email."""
        if not context:
            raise ValueError("Context required for ticket issued email")

        voya_booking_reference = context.get("voya_booking_reference")
        ticket_numbers = context.get("ticket_numbers", [])
        cancellation_policy_text = context.get("cancellation_policy_text")

        if not voya_booking_reference:
            raise ValueError("voya_booking_reference required for ticket issued email")

        ticket_numbers_text = (
            ", ".join(ticket_numbers) if ticket_numbers else "Available in your booking"
        )

        # Log cancellation policy status
        logger.info(
            f"Building ticket issued email - cancellation_policy_text: {'present' if cancellation_policy_text else 'missing'} "
            f"(length: {len(cancellation_policy_text) if cancellation_policy_text else 0})"
        )

        # Process cancellation policy for email display
        cancellation_policy_section = ""
        if cancellation_policy_text:
            # Check if text contains HTML tags
            import re

            html_tag_pattern = re.compile(r"<[^>]+>")
            contains_html = bool(html_tag_pattern.search(cancellation_policy_text))

            if contains_html:
                # Contains HTML - use as-is
                formatted_policy = cancellation_policy_text
            else:
                # Plain text - escape HTML and convert newlines to <br>
                from html import escape

                escaped_text = escape(cancellation_policy_text)
                formatted_policy = escaped_text.replace("\n", "<br>")

            cancellation_policy_section = f"""
<div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
    <h3 style="margin-top: 0; color: #e65100; font-size: 16px;">📋 Cancellation Policy</h3>
    <div style="font-size: 14px; line-height: 1.6; color: #333;">
        {formatted_policy}
    </div>
</div>
"""

        content = TICKET_CONFIRMATION_CONTENT.format(
            voya_booking_reference=voya_booking_reference,
            ticket_numbers=ticket_numbers_text,
            cancellation_policy_section=cancellation_policy_section,
        )
        return EmailSpec(
            subject=TICKET_CONFIRMATION_SUBJECT_TEMPLATE.format(
                voya_booking_reference=voya_booking_reference
            ),
            title=TICKET_CONFIRMATION_TITLE,
            body_content=content,
            button_url=cls._get_authenticated_frontend_url(
                f"/flights/bookings/{voya_booking_reference}",
                user_id=context.get("user_id"),
            ),
            button_text=TICKET_CONFIRMATION_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Ticket Issued",
        )

    @classmethod
    def _build_booking_failed(cls, context: dict[str, Any] | None = None) -> EmailSpec:
        """Build booking failed email."""
        if not context:
            raise ValueError("Context required for booking failed email")
        external_booking_reference = context.get("external_booking_reference")
        reason = context.get("reason", "Unknown error occurred")

        if not external_booking_reference:
            raise ValueError(
                "external_booking_reference required for booking failed email"
            )

        content = BOOKING_FAILED_CONTENT.format(
            booking_reference=external_booking_reference, reason=reason
        )
        return EmailSpec(
            subject=BOOKING_FAILED_SUBJECT,
            title=BOOKING_FAILED_TITLE,
            body_content=content,
            button_url=cls._get_frontend_url("/flights/search"),
            button_text=BOOKING_FAILED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.ORANGE.value],
            email_type_name="Booking Failed",
        )

    @classmethod
    def _build_payment_confirmation(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build payment confirmation email."""
        if not context:
            raise ValueError("Context required for payment confirmation email")

        voya_booking_reference = context.get("voya_booking_reference")
        amount = context.get("amount", 0)
        currency = context.get("currency", "usd").upper()
        payment_method = context.get("payment_method", "Credit Card")
        transaction_id = context.get("transaction_id", "N/A")

        if not voya_booking_reference:
            raise ValueError(
                "voya_booking_reference required for payment confirmation email"
            )

        # Log currency being used for payment confirmation
        logger.info(
            f"💳 [Payment Confirmation] Using currency: {currency} for amount: {amount} "
            f"(from context: {context.get('currency', 'not found')})"
        )

        # Format amount with currency symbol
        amount_paid = format_money(amount, currency)

        # Check if this is a hotel booking and extract hotel name
        booking_details = context.get("booking_details", {})
        is_hotel_booking = (
            "hotel_id" in booking_details or "check_in" in booking_details
        )
        hotel_name = None
        hotel_name_row = ""
        if is_hotel_booking:
            hotel_name = booking_details.get("hotel_name", "Your Hotel")
            # Only include hotel name row if we have a valid hotel name (not "Your Hotel" fallback)
            if hotel_name and hotel_name != "Your Hotel":
                hotel_name_row = f'<tr><td style="padding: 5px; font-weight: bold;">Hotel:</td><td style="padding: 5px;"><strong>{hotel_name}</strong></td></tr>'

        content = PAYMENT_CONFIRMATION_CONTENT.format(
            voya_booking_reference=voya_booking_reference,
            amount_paid=amount_paid,
            payment_method=payment_method,
            transaction_id=transaction_id,
            hotel_name_row=hotel_name_row,
        )
        return EmailSpec(
            subject=PAYMENT_CONFIRMATION_SUBJECT_TEMPLATE.format(
                voya_booking_reference=voya_booking_reference
            ),
            title=PAYMENT_CONFIRMATION_TITLE,
            body_content=content,
            button_url=cls._get_authenticated_frontend_url(
                f"/flights/bookings/{voya_booking_reference}",
                user_id=context.get("user_id"),
            ),
            button_text=PAYMENT_CONFIRMATION_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.GREEN.value],
            email_type_name="Payment Confirmation",
        )

    @classmethod
    def _build_booking_cancelled(
        cls, context: dict[str, Any] | None = None
    ) -> EmailSpec:
        """Build booking cancelled email."""
        if not context:
            raise ValueError("Context required for booking cancelled email")

        voya_booking_reference = context.get("voya_booking_reference")

        if not voya_booking_reference:
            raise ValueError(
                "voya_booking_reference required for booking cancelled email"
            )

        content = BOOKING_CANCELLED_CONTENT.format(
            voya_booking_reference=voya_booking_reference,
        )
        return EmailSpec(
            subject=BOOKING_CANCELLED_SUBJECT_TEMPLATE.format(
                voya_booking_reference=voya_booking_reference
            ),
            title=BOOKING_CANCELLED_TITLE,
            body_content=content,
            button_url=cls._get_frontend_url("/support"),
            button_text=BOOKING_CANCELLED_BUTTON_TEXT,
            button_color=BUTTON_COLOR_HEX_VALUES[UIButtonColor.RED.value],
            email_type_name="Booking Cancelled",
        )


# ============================================================
# MODULE-LEVEL FUNCTIONS
# ============================================================


def build_email(
    email_type: EmailType | str,
    recipient_email: str,
    context: dict[str, Any],
    revalidate_response: Any | None = None,
    booking_request: Any | None = None,
    trip_details: Any | None = None,
) -> RenderedEmail | None:
    """Build email using EmailBuilder class."""
    return EmailBuilder.build_email(
        email_type,
        recipient_email,
        context,
        revalidate_response=revalidate_response,
        booking_request=booking_request,
        trip_details=trip_details,
    )
