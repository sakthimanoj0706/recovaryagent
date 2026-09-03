from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class DriftStatus(str, Enum):
    STABLE = "STABLE"
    WARNING = "WARNING"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class StrategyVersion(BaseModel):
    strategy_id: str
    strategy_name: str
    version: str
    created_at: str
    created_by: str
    status: str
    configuration_hash: str
    evaluation_hash: Optional[str] = None

class RecoveryOutcome(BaseModel):
    decision_id: str
    payment_id: str
    strategy_id: str
    strategy_version: str
    failure_class: str
    
    candidate_action: str
    selected_action: str
    
    expected_recovery: float
    expected_cost: float
    expected_net_value: float
    expected_probability: float
    risk_loss: float
    
    policy_result: str
    firewall_result: str
    execution_result: str
    verification_result: str
    
    actual_recovered_value: float
    actual_cost: float
    actual_net_value: float
    
    recovery_success: bool
    recovery_latency: float
    customer_response: Optional[str] = None
    
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str

class DecisionQualityScore(BaseModel):
    economic_accuracy: float
    recovery_accuracy: float
    cost_accuracy: float
    safety_correctness: float
    verification_correctness: float
    total_score: float

class DriftSignal(BaseModel):
    metric: str
    baseline: float
    current: float
    delta: float
    threshold: float
    status: DriftStatus
