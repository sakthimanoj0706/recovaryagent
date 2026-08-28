"""
Data Models for Real-Time Event Ingestion and Webhook Processing in RecoverAI.
"""

import uuid
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from state_engine.models import Event


class IngestionStatus(str, Enum):
    """Lifecycle status of an ingested event / webhook."""
    PROCESSED = "PROCESSED"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    MALFORMED_EVENT = "MALFORMED_EVENT"
    EXCEPTION = "EXCEPTION"
    FILTERED = "FILTERED"


class WebhookPayload(BaseModel):
    """
    Incoming webhook payload model from payment gateways.
    """
    model_config = ConfigDict(extra="allow")

    provider: str = Field(default="mock", description="Gateway provider identifier")
    event_id: str = Field(description="Unique event ID assigned by the provider")
    event: str = Field(description="Event name e.g. payment.failed, payment.captured")
    payment_id: str = Field(description="Transaction payment identifier")
    order_id: Optional[str] = Field(default=None, description="Merchant order identifier")
    amount: Optional[float] = Field(default=None, description="Transaction amount in INR")
    method: Optional[str] = Field(default=None, description="Payment instrument method e.g. upi, card")
    error_code: Optional[str] = Field(default=None, description="Error code if payment failed")
    error_description: Optional[str] = Field(default=None, description="Descriptive error explanation")
    hardness: Optional[str] = Field(default=None, description="Failure hardness: 'soft' or 'hard'")
    late_authorization: Optional[bool] = Field(default=None, description="Flag for late authorization event")
    ts: Optional[str] = Field(default=None, description="Timestamp of the event in ISO format or unix epoch")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Raw original provider payload preserved for audit")


class IngestedEventRecord(BaseModel):
    """
    Persisted record of an event ingested into the immutable Event Store.
    """
    model_config = ConfigDict(extra="allow")

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:10]}")
    event_id: str
    provider: str
    normalized_event: Event
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_duplicate: bool = False


class IngestionResult(BaseModel):
    """
    Structured outcome of the end-to-end webhook ingestion pipeline.
    """
    model_config = ConfigDict(extra="allow")

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:10]}")
    status: IngestionStatus
    event_id: str
    provider: str
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    normalized_event: Optional[Event] = None
    message: str
    financial_state_before: Optional[str] = None
    financial_state_after: Optional[str] = None
    state_changed: bool = False
    orchestrator_result: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value if isinstance(self.status, IngestionStatus) else str(self.status),
            "event_id": self.event_id,
            "provider": self.provider,
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "normalized_event": self.normalized_event.model_dump() if self.normalized_event else None,
            "message": self.message,
            "financial_state_before": self.financial_state_before,
            "financial_state_after": self.financial_state_after,
            "state_changed": self.state_changed,
            "orchestrator_result": self.orchestrator_result,
            "timestamp": self.timestamp,
        }

