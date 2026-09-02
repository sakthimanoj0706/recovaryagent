"""
Razorpay Webhook Signature Validator & Event Normalizer for RecoverAI.

CRITICAL SECURITY RULES:
1. Signature validation uses the EXACT RAW REQUEST BODY — never re-serialized JSON.
2. Invalid signatures → HTTP 400, zero financial state mutation, zero recovery trigger.
3. Metadata/notes fields from Razorpay are UNTRUSTED — they have zero authority
   over FinancialStateEngine, PolicyEngine, or RecoveryFirewall.
4. webhook_secret is NEVER logged.
"""

import os
import hmac
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from ingestion.models import WebhookPayload
from .razorpay_models import RazorpayWebhookEvent, RazorpayPayment

logger = logging.getLogger(__name__)


# Hard-decline error codes that map to "hard" failure hardness
_HARD_DECLINE_CODES = frozenset({
    "CARD_BLOCKED",
    "INVALID_ACCOUNT",
    "EXPIRED_CARD",
    "CARD_EXPIRED",
    "BAD_VPA",
    "FRAUD_SUSPECTED",
    "INSUFFICIENT_FUNDS_BLOCKED",
    "STOLEN_CARD",
    "PICKUP_CARD",
    "RESTRICTED_CARD",
    "TRANSACTION_NOT_PERMITTED",
    "INVALID_CARD",
    "DO_NOT_HONOUR",
})


class RazorpaySignatureError(ValueError):
    """Raised when webhook signature validation fails."""
    pass


class RazorpayWebhookSignatureValidator:
    """
    Validates Razorpay webhook signatures using HMAC-SHA256.

    MUST use the exact raw request bytes — not re-serialized JSON.
    Any intermediate JSON parse/re-serialize will invalidate the signature.
    """

    @staticmethod
    def validate(
        raw_body: bytes,
        signature: str,
        webhook_secret: Optional[str] = None,
    ) -> bool:
        """
        Validate a Razorpay webhook signature.

        Args:
            raw_body: Exact raw request body bytes (before any JSON parsing)
            signature: Value of x-razorpay-signature header
            webhook_secret: Configured webhook secret (default: RAZORPAY_WEBHOOK_SECRET env var)

        Returns:
            True if signature is valid, False otherwise

        Raises:
            RazorpaySignatureError if webhook_secret is not configured
        """
        secret = webhook_secret or os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        if not secret:
            raise RazorpaySignatureError(
                "RAZORPAY_WEBHOOK_SECRET is not configured. "
                "Cannot validate webhook signature. "
                "Set RAZORPAY_WEBHOOK_SECRET in environment variables."
            )

        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected, signature)

        if not is_valid:
            logger.warning(
                "Razorpay webhook signature validation FAILED — event rejected",
                extra={
                    "provider": "razorpay",
                    "signature_valid": False,
                    # NEVER log the expected or provided signature values
                    # NEVER log the webhook_secret
                },
            )

        return is_valid


class RazorpayCheckoutSignatureValidator:
    """
    Validates Razorpay Standard Web Checkout frontend response signatures.
    """
    @staticmethod
    def validate(
        order_id: str,
        payment_id: str,
        signature: str,
        key_secret: Optional[str] = None
    ) -> bool:
        """
        Validate the signature returned by checkout.js:
        HMAC-SHA256(order_id + "|" + payment_id, key_secret)
        """
        if not signature or not order_id or not payment_id:
            return False

        secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        if not secret:
            raise RazorpaySignatureError("RAZORPAY_KEY_SECRET is not configured.")

        payload = f"{order_id}|{payment_id}"
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)


class RazorpayWebhookNormalizer:
    """
    Converts Razorpay webhook events into RecoverAI's internal WebhookPayload model.

    Supported events:
      - payment.failed
      - payment.authorized
      - payment.captured
      - payment.refunded
      - order.paid

    All other events are normalized to a generic INFORMATIONAL event.

    SECURITY: Razorpay notes/metadata is carried through as raw context only.
    It has ZERO authority over FinancialStateEngine, PolicyEngine, or RecoveryFirewall.
    """

    @classmethod
    def normalize(
        cls,
        raw_payload: Dict[str, Any],
        provider_event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        signature_verified: bool = False,
    ) -> WebhookPayload:
        """
        Normalize a raw Razorpay webhook payload into a RecoverAI WebhookPayload.

        Args:
            raw_payload: Parsed JSON from the webhook body
            provider_event_id: Value from x-razorpay-event-id header
            correlation_id: RecoverAI correlation ID for tracing
            signature_verified: Whether HMAC-SHA256 signature was verified

        Returns:
            WebhookPayload ready for ingestion into EventProcessor
        """
        cid = correlation_id or f"rzp_cid_{uuid.uuid4().hex[:10]}"
        event_id = provider_event_id or raw_payload.get("id") or f"rzp_evt_{uuid.uuid4().hex[:10]}"

        try:
            webhook_event = RazorpayWebhookEvent(**raw_payload)
        except Exception as exc:
            logger.warning("Failed to parse Razorpay webhook event — treating as malformed", exc_info=exc)
            return WebhookPayload(
                provider="razorpay",
                event_id=event_id,
                event="webhook.malformed",
                payment_id=f"unknown_{event_id}",
                payload={
                    "raw": raw_payload,
                    "parse_error": str(exc),
                    "correlation_id": cid,
                    "signature_verified": signature_verified,
                    "provider_mode": "test",
                },
            )

        event_type = webhook_event.event
        payment = webhook_event.get_payment()
        order = webhook_event.get_order()

        # Extract core fields from payment entity
        payment_id = ""
        order_id = None
        amount_inr = 0.0
        method = None
        error_code = None
        error_description = None
        hardness = None
        ts = None

        if payment:
            payment_id = payment.id
            order_id = payment.order_id
            amount_inr = payment.amount_inr
            method = payment.method
            error_code = payment.error_code
            error_description = payment.error_description

            if webhook_event.created_at:
                ts = str(webhook_event.created_at)

            # Classify hardness from error codes (if failed event)
            if error_code:
                normalized_code = (error_code or "").upper().replace(" ", "_")
                if normalized_code in _HARD_DECLINE_CODES:
                    hardness = "hard"
                else:
                    hardness = "soft"
        elif order:
            # order.paid event with no payment entity
            order_id = order.id
            amount_inr = order.amount_inr
            payment_id = f"order_{order.id}"
            if webhook_event.created_at:
                ts = str(webhook_event.created_at)

        if not payment_id:
            payment_id = f"rzp_unknown_{event_id[:8]}"

        # Map Razorpay events to RecoverAI canonical events
        internal_event = cls._map_event_name(event_type, payment)

        # SECURITY: Metadata from Razorpay notes is UNTRUSTED.
        # It is preserved for audit but has zero authority over RecoverAI decisions.
        safe_metadata: Dict[str, Any] = {
            "provider": "razorpay",
            "provider_event_id": event_id,
            "provider_event_type": event_type,
            "correlation_id": cid,
            "signature_verified": signature_verified,
            "provider_mode": "test",
            "UNTRUSTED_notes": "Any notes/metadata from Razorpay are informational only "
                               "and have zero authority over RecoverAI financial decisions",
        }

        return WebhookPayload(
            provider="razorpay",
            event_id=event_id,
            event=internal_event,
            payment_id=payment_id,
            order_id=order_id,
            amount=amount_inr,
            method=method,
            error_code=error_code,
            error_description=error_description,
            hardness=hardness,
            ts=ts,
            payload=safe_metadata,
        )

    @staticmethod
    def _map_event_name(razorpay_event: str, payment: Optional[RazorpayPayment] = None) -> str:
        """Map Razorpay event names to RecoverAI canonical event names."""
        mapping: Dict[str, str] = {
            "payment.failed": "payment.failed",
            "payment.authorized": "payment.authorized",
            "payment.captured": "payment.captured",
            "payment.refunded": "payment.refunded",
            "payment.dispute.created": "payment.disputed",
            "payment.dispute.won": "payment.dispute.resolved",
            "payment.dispute.lost": "payment.dispute.lost",
            "order.paid": "payment.captured",  # order.paid implies payment captured
        }
        return mapping.get(razorpay_event, razorpay_event)


def extract_razorpay_event_id(headers: Dict[str, str]) -> Optional[str]:
    """
    Extract the Razorpay event ID from webhook headers.
    Used for idempotency checks.
    """
    # Header names can vary in case
    for key in ("x-razorpay-event-id", "X-Razorpay-Event-Id", "X-RAZORPAY-EVENT-ID"):
        val = headers.get(key)
        if val:
            return val
    return None


def extract_razorpay_signature(headers: Dict[str, str]) -> Optional[str]:
    """
    Extract the Razorpay webhook signature from request headers.
    """
    for key in ("x-razorpay-signature", "X-Razorpay-Signature", "X-RAZORPAY-SIGNATURE"):
        val = headers.get(key)
        if val:
            return val
    return None


__all__ = [
    "RazorpayWebhookSignatureValidator",
    "RazorpayWebhookNormalizer",
    "RazorpaySignatureError",
    "extract_razorpay_event_id",
    "extract_razorpay_signature",
]
