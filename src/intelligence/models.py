from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class FailureType(str, Enum):
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    HARD_DECLINE = "HARD_DECLINE"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    EXPIRED_PAYMENT_METHOD = "EXPIRED_PAYMENT_METHOD"
    CUSTOMER_ABANDONMENT = "CUSTOMER_ABANDONMENT"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    ALREADY_CAPTURED = "ALREADY_CAPTURED"
    ALREADY_REFUNDED = "ALREADY_REFUNDED"
    PARTIAL_CAPTURE = "PARTIAL_CAPTURE"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    CONFLICTING_STATE = "CONFLICTING_STATE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"

class FailureClassification(BaseModel):
    failure_type: FailureType
    confidence: float
    reason: str
    is_recoverable: bool

class CandidateAction(BaseModel):
    action: str
    is_eligible: bool
    expected_recovery_probability: float
    expected_gross_recovery: float
    operational_cost: float
    risk_penalty: float
    expected_net_value: float
    explanation: str
    rejection_reason: Optional[str] = None

class LLMRecommendation(BaseModel):
    recommended_action: str = Field(..., description="The action to take, e.g., RETRY, PAYMENT_LINK, REMINDER, ESCALATE, STOP")
    reason: str = Field(..., description="The reason for this recommendation")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")

class EvaluationResult(BaseModel):
    llm_recommendation: str
    deterministic_best_action: str
    agreement: bool
    economic_delta: float
    safety_status: str

class IntelligentDecision(BaseModel):
    payment_id: str
    classification: FailureClassification
    candidates: List[CandidateAction]
    deterministic_best_action: CandidateAction
    llm_recommendation: Optional[LLMRecommendation] = None
    evaluation: Optional[EvaluationResult] = None
    selected_action: str
    selection_reason: str
