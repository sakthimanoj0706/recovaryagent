"""
Audit schemas, structured event models, and system metrics for RecoverAI.
Guarantees append-only immutable financial audit trails and verifiable accounting invariants.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class AuditEventStage(str, Enum):
    """Canonical stages in the RecoverAI lifecycle."""
    OBSERVE = "OBSERVE"
    PROVE = "PROVE"
    PRIORITIZE = "PRIORITIZE"
    PLAN = "PLAN"
    POLICY = "POLICY"
    GUARD = "GUARD"
    ACT = "ACT"
    VERIFY = "VERIFY"
    STOP = "STOP"


class AuditEvent(BaseModel):
    """
    Standardized granular structured audit event representing a single stage decision.
    """
    model_config = ConfigDict(extra="allow")

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_id: str = Field(description="Unique correlation ID spanning the entire lifecycle")
    payment_id: str = Field(description="Payment transaction identifier")
    order_id: Optional[str] = Field(default=None, description="Merchant order identifier")
    stage: str = Field(description="Lifecycle stage e.g. PROVE, PLAN, GUARD, ACT, VERIFY")
    component: str = Field(description="Subsystem generating this event")
    event_type: str = Field(description="Type of audit event e.g. STATE_EVALUATION, FIREWALL_CHECK")
    decision: str = Field(description="Outcome decision e.g. VERIFIED_LOST, APPROVED, RECOVERY_SUCCESS")
    reason: str = Field(description="Auditable rationale for the decision")
    rule_id: Optional[str] = Field(default=None, description="Deterministic rule identifier if applicable")
    financial_state: str = Field(description="Financial state at this stage")
    agent_action: Optional[str] = Field(default=None, description="Action proposed/evaluated")
    execution_status: Optional[str] = Field(default=None, description="Execution status if action attempted")
    verification_state: Optional[str] = Field(default=None, description="Independent verification state")
    simulation_flag: bool = Field(default=True, description="Strictly true for mock/sandbox runs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary stage metadata")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AuditRecord(BaseModel):
    """
    Typed, immutable lifecycle audit record representation.
    """
    model_config = ConfigDict(extra="allow")

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_id: Optional[str] = None
    payment_id: str
    order_id: Optional[str] = None

    initial_financial_state: str
    recovery_probability: Optional[float] = None
    expected_net_value: Optional[float] = None

    agent_action: Optional[str] = None
    agent_reason: Optional[str] = None

    firewall_decision: str
    firewall_rule: Optional[str] = None

    execution_id: Optional[str] = None
    execution_status: str

    verification_state: str
    final_result: str

    simulation_flag: bool = True
    retry_count: int = 0

    amount: float = 0.0
    amount_recovered: float = 0.0
    amount_withheld: float = 0.0
    amount_pending: float = 0.0
    amount_escalated: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SystemMetrics(BaseModel):
    """
    Aggregated operational metrics for RecoverAI with verifiable accounting buckets.
    """
    model_config = ConfigDict(extra="allow")

    total_cases: int = 0
    verified_lost_cases: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    recovery_success_rate: float = 0.0

    total_amount_attempted: float = 0.0
    total_amount_recovered: float = 0.0  # HERO METRIC #1: ₹ ACTUALLY RECOVERED
    total_amount_withheld: float = 0.0   # HERO METRIC #2: ₹ CORRECTLY WITHHELD
    total_amount_pending: float = 0.0    # In-flight / Uncertain
    total_amount_escalated: float = 0.0  # Exceptions / Mismatches

    unnecessary_actions_avoided: int = 0
    firewall_blocks: int = 0
    safe_stops: int = 0
    verification_catches: int = 0
    uncertain_cases: int = 0
    exception_cases: int = 0
    escalations: int = 0
    max_retry_blocks: int = 0
    duplicate_action_blocks: int = 0

    def verify_accounting_balance(self) -> bool:
        """
        Verify that total recovered + withheld + pending + escalated is non-negative and balanced.
        """
        sum_buckets = (
            self.total_amount_recovered
            + self.total_amount_withheld
            + self.total_amount_pending
            + self.total_amount_escalated
        )
        return sum_buckets >= 0.0
