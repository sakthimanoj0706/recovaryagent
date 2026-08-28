"""
Event Normalizer for RecoverAI.
Transforms vendor-specific webhook structures into standardized, UTC-normalized Event models.
"""

from datetime import datetime, timezone
from typing import Optional
from dateutil import parser as date_parser
from state_engine.models import Event
from .models import WebhookPayload


class EventNormalizer:
    """
    Normalizes vendor payloads to the canonical RecoverAI Event schema.
    Guarantees strict ISO-8601 UTC timestamp formatting.
    """

    @staticmethod
    def normalize_timestamp(raw_ts: Optional[str]) -> str:
        """
        Normalize any incoming timestamp (ISO, unix epoch integer, RFC) into UTC ISO-8601 string.
        """
        if not raw_ts:
            return datetime.now(timezone.utc).isoformat()

        # Handle numeric epoch timestamp (seconds or milliseconds)
        try:
            val = float(raw_ts)
            if val > 1e11:  # Milliseconds epoch
                val = val / 1000.0
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError, OverflowError):
            pass

        # Handle string parsing
        try:
            dt = date_parser.parse(str(raw_ts))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @classmethod
    def normalize(cls, payload: WebhookPayload) -> Event:
        """
        Convert a WebhookPayload into a canonical Event model.
        """
        normalized_ts = cls.normalize_timestamp(payload.ts)

        # Standardize hardness classification if not explicitly provided
        hardness = payload.hardness
        if not hardness and payload.error_code:
            code = payload.error_code.upper()
            if code in ["CARD_BLOCKED", "INVALID_ACCOUNT", "EXPIRED_CARD", "CARD_EXPIRED", "BAD_VPA", "FRAUD_SUSPECTED"]:
                hardness = "hard"
            else:
                hardness = "soft"

        return Event(
            event=payload.event,
            payment_id=payload.payment_id,
            order_id=payload.order_id,
            amount=payload.amount,
            method=payload.method,
            error_code=payload.error_code,
            error_description=payload.error_description,
            hardness=hardness,
            late_authorization=payload.late_authorization,
            ts=normalized_ts,
        )
