"""
Execution action definitions and data models for RecoverAI.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from agent.models import RecoveryAction


class ActionExecutionRequest(BaseModel):
    """
    Request to execute a recovery action.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    action: RecoveryAction
    amount: float
    reason: str
    channel: Optional[str] = "sms"
    delay_seconds: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionExecutionResponse(BaseModel):
    """
    Structured outcome of a simulated action execution.
    """
    model_config = ConfigDict(extra="allow")

    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:10]}")
    payment_id: str
    order_id: Optional[str] = None
    action: RecoveryAction
    status: str = "SIMULATED"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    simulated_success: bool
    message: str
    generated_events: list = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
