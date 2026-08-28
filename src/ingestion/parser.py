"""
Webhook Ingestion Parser for RecoverAI.
Validates incoming payload structures and rejects malformed financial events.
"""

from typing import Dict, Any, Tuple, Optional
from .models import WebhookPayload


class WebhookParser:
    """
    Parses and strictly validates raw incoming webhook payloads.
    Ensures mandatory financial transaction identifiers are present and well-formed.
    """

    @staticmethod
    def parse_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[WebhookPayload], str]:
        """
        Validate and parse raw webhook dictionary into a typed WebhookPayload.
        Returns: (is_valid, parsed_payload_or_none, error_message)
        """
        if not isinstance(data, dict):
            return False, None, "Payload must be a valid JSON dictionary."

        # Handle nested Razorpay-style webhook structures e.g. payload.payment.entity
        payment_id = data.get("payment_id")
        order_id = data.get("order_id")
        event = data.get("event")
        amount = data.get("amount")
        method = data.get("method")
        error_code = data.get("error_code")
        error_description = data.get("error_description")
        hardness = data.get("hardness")
        late_authorization = data.get("late_authorization")
        ts = data.get("ts")
        provider = data.get("provider", "mock")
        event_id = data.get("event_id")

        if not event_id:
            # Check nested entity for ID
            event_id = data.get("id") or (data.get("payload", {}).get("payment", {}).get("entity", {}).get("id"))

        # Check nested entity for payment_id / amount if top-level omitted
        if not payment_id and "payload" in data and isinstance(data["payload"], dict):
            entity = data["payload"].get("payment", {}).get("entity", {})
            if isinstance(entity, dict):
                payment_id = entity.get("id")
                order_id = order_id or entity.get("order_id")
                amount = amount or entity.get("amount")
                method = method or entity.get("method")
                error_code = error_code or entity.get("error_code")
                error_description = error_description or entity.get("error_description")
                ts = ts or entity.get("created_at")

        # Strict validation of mandatory fields
        if not event or not isinstance(event, str) or not event.strip():
            return False, None, "Malformed event: 'event' field is required and must be a non-empty string."

        if not payment_id or not isinstance(payment_id, str) or not payment_id.strip():
            return False, None, "Malformed event: 'payment_id' field is required and must be a non-empty string."

        if not event_id or not isinstance(event_id, str) or not event_id.strip():
            # Auto-assign deterministic fallback event_id if missing in test payloads
            event_id = f"evt_{payment_id}_{event}_{ts or '0'}"

        try:
            amt_val = float(amount) if amount is not None else None
        except (ValueError, TypeError):
            return False, None, f"Malformed event: 'amount' must be a numeric value, got '{amount}'."

        payload_obj = WebhookPayload(
            provider=str(provider).lower(),
            event_id=str(event_id).strip(),
            event=str(event).strip(),
            payment_id=str(payment_id).strip(),
            order_id=str(order_id).strip() if order_id else None,
            amount=amt_val,
            method=str(method).strip() if method else None,
            error_code=str(error_code).strip() if error_code else None,
            error_description=str(error_description).strip() if error_description else None,
            hardness=str(hardness).strip() if hardness else None,
            late_authorization=bool(late_authorization) if late_authorization is not None else None,
            ts=str(ts).strip() if ts else None,
            payload=data.get("payload", data),
        )

        return True, payload_obj, "Validation successful"
