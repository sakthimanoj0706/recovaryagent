"""
Strongly typed models for RecoverAI Payment Gateway integration.
Defines provider-independent schemas for actions, status checks, and execution results.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from state_engine.models import Event


class GatewayActionType(str, Enum):
    """Supported gateway operation types."""
    PAYMENT_LINK = "PAYMENT_LINK"
    RETRY = "RETRY"
    REMINDER = "REMINDER"
    STATUS_CHECK = "STATUS_CHECK"
    CANCEL = "CANCEL"


class GatewayActionStatus(str, Enum):
    """Status outcomes from gateway operations."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    TIMEOUT = "TIMEOUT"


class GatewayActionResult(BaseModel):
    """
    Standardized result returned by any PaymentGateway implementation.
    """
    model_config = ConfigDict(extra="allow")

    execution_id: str = Field(description="Unique idempotency ID for this execution")
    payment_id: str = Field(description="Target payment transaction ID")
    order_id: Optional[str] = Field(default=None, description="Associated order identifier")
    action: str = Field(description="Action executed e.g. PAYMENT_LINK, RETRY, REMINDER")
    status: GatewayActionStatus = Field(description="Execution status outcome")
    provider: str = Field(default="mock", description="Payment gateway provider e.g. mock, razorpay")
    simulation: bool = Field(default=True, description="Strictly true for mock and sandbox environments")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = Field(default="", description="Provider response message or error detail")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific response metadata")
    generated_events: List[Event] = Field(default_factory=list, description="Synthetic lifecycle events produced")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "action": self.action,
            "status": self.status.value if isinstance(self.status, GatewayActionStatus) else str(self.status),
            "provider": self.provider,
            "simulation": self.simulation,
            "timestamp": self.timestamp,
            "message": self.message,
            "metadata": self.metadata,
            "generated_events": [e.model_dump() for e in self.generated_events],
        }


class PaymentStatusResult(BaseModel):
    """
    Status report from querying a gateway for payment status.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    status: str
    amount: float
    currency: str = "INR"
    captured: bool = False
    provider: str = "mock"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: List[Event] = Field(default_factory=list)
