from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class FaultType(str, Enum):
    # Provider/Gateway
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    GATEWAY_HTTP_500 = "GATEWAY_HTTP_500"
    GATEWAY_HTTP_401 = "GATEWAY_HTTP_401"
    GATEWAY_MALFORMED_RESPONSE = "GATEWAY_MALFORMED_RESPONSE"
    GATEWAY_DUPLICATE_SUCCESS = "GATEWAY_DUPLICATE_SUCCESS"
    GATEWAY_SUCCESS_LEDGER_UNAVAILABLE = "GATEWAY_SUCCESS_LEDGER_UNAVAILABLE"
    GATEWAY_SUCCESS_VERIFICATION_TIMEOUT = "GATEWAY_SUCCESS_VERIFICATION_TIMEOUT"
    
    # Webhook
    INVALID_WEBHOOK_SIGNATURE = "INVALID_WEBHOOK_SIGNATURE"
    DUPLICATE_WEBHOOK = "DUPLICATE_WEBHOOK"
    OUT_OF_ORDER_WEBHOOK = "OUT_OF_ORDER_WEBHOOK"
    MALFORMED_WEBHOOK = "MALFORMED_WEBHOOK"
    MISSING_WEBHOOK = "MISSING_WEBHOOK"
    
    # Storage / Ledger
    LEDGER_WRITE_FAILURE = "LEDGER_WRITE_FAILURE"
    LEDGER_READ_FAILURE = "LEDGER_READ_FAILURE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    
    # Concurrency
    CONCURRENT_DUPLICATE_EXECUTION = "CONCURRENT_DUPLICATE_EXECUTION"
    
    # Adversarial AI
    HARD_DECLINE_MALICIOUS_RETRY = "HARD_DECLINE_MALICIOUS_RETRY"
    PROMPT_INJECTION_METADATA = "PROMPT_INJECTION_METADATA"
    LLM_INFERIOR_ACTION = "LLM_INFERIOR_ACTION"
    LLM_VIOLATING_ACTION = "LLM_VIOLATING_ACTION"
    
    # Payment States
    PAYMENT_ALREADY_REFUNDED = "PAYMENT_ALREADY_REFUNDED"
    PAYMENT_ALREADY_CAPTURED = "PAYMENT_ALREADY_CAPTURED"
    PARTIAL_CAPTURE = "PARTIAL_CAPTURE"
    CONFLICTING_STATES = "CONFLICTING_STATES"
    STALE_STATE = "STALE_STATE"


class ChaosScenario(BaseModel):
    id: str
    description: str
    fault_type: FaultType
    payment_id: str
    amount: float
    original_error: str
    adversarial_payload: Optional[str] = None

class ChaosResult(BaseModel):
    scenario_id: str
    fault_type: FaultType
    initial_state: str
    advisory_action: Optional[str] = None
    policy_result: Optional[str] = None
    firewall_result: Optional[str] = None
    provider_result: Optional[str] = None
    verification_result: Optional[str] = None
    final_state: str
    recovered_value: float = 0.0
    phantom_revenue: float = 0.0
    duplicate_recovery: float = 0.0
    accounting_imbalance: float = 0.0
    is_pass: bool = False
    error_message: Optional[str] = None
    
    def fingerprint_dict(self) -> Dict[str, Any]:
        """Stable dictionary for hashing. No timestamps or unique IDs except scenario logic."""
        return {
            "fault": self.fault_type.value,
            "final_state": self.final_state,
            "recovered": round(self.recovered_value, 2),
            "phantom": round(self.phantom_revenue, 2),
            "duplicate": round(self.duplicate_recovery, 2),
            "imbalance": round(self.accounting_imbalance, 2),
            "pass": self.is_pass
        }

class ChaosReport(BaseModel):
    total_scenarios: int
    passed: int
    failed: int
    results: List[ChaosResult]
    fingerprint_sha256: str
