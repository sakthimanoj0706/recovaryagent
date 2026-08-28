"""
Data models and Enums for the RecoverAI Financial State Engine and Recovery Intelligence.
"""

import math
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator


class FinancialState(str, Enum):
    """Canonical financial state of a payment/order."""
    ALREADY_RECOVERED = "ALREADY_RECOVERED"
    VERIFIED_LOST = "VERIFIED_LOST"
    UNCERTAIN = "UNCERTAIN"
    EXCEPTION = "EXCEPTION"


class RecommendedAction(str, Enum):
    """Action recommendation based on the financial state."""
    STOP = "STOP"
    EVALUATE_RECOVERY = "EVALUATE_RECOVERY"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"


class Event(BaseModel):
    """Represents a payment/order lifecycle event."""
    model_config = ConfigDict(extra="allow")

    event: str
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[float] = None
    method: Optional[str] = None
    ts: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    hardness: Optional[str] = None
    late_authorization: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def clean_nan_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: (None if (isinstance(v, float) and math.isnan(v)) else v)
                for k, v in data.items()
            }
        return data


class PaymentRecord(BaseModel):
    """Represents a payment transaction record from database/CSV."""
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    scenario: Optional[str] = None
    ground_truth_state: Optional[str] = None
    amount: Optional[float] = None
    method: Optional[str] = None
    customer_segment: Optional[str] = None
    created_ts: Optional[str] = None
    has_settlement: Optional[bool] = None
    settled_amount: Optional[float] = None
    settlement_matches_order: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def clean_nan_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: (None if (isinstance(v, float) and math.isnan(v)) else v)
                for k, v in data.items()
            }
        return data


class StateEvaluationResult(BaseModel):
    """
    Auditable result of evaluating a payment's financial state.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    state: FinancialState
    recommended_action: RecommendedAction
    reason: str
    evidence_events: List[str] = Field(default_factory=list)
    evaluated_at: str
    rule_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "state": self.state.value if isinstance(self.state, FinancialState) else str(self.state),
            "recommended_action": (
                self.recommended_action.value
                if isinstance(self.recommended_action, RecommendedAction)
                else str(self.recommended_action)
            ),
            "reason": self.reason,
            "evidence_events": self.evidence_events,
            "evaluated_at": self.evaluated_at,
            "rule_id": self.rule_id,
        }
