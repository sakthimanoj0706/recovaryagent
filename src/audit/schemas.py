"""
Audit schemas and metrics data models for RecoverAI.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class AuditRecord(BaseModel):
    """
    Typed, immutable audit record representation.
    """
    model_config = ConfigDict(extra="allow")

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SystemMetrics(BaseModel):
    """
    Aggregated operational metrics for RecoverAI.
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

    unnecessary_actions_avoided: int = 0
    firewall_blocks: int = 0
    uncertain_cases: int = 0
    exception_cases: int = 0
    max_retry_blocks: int = 0
    duplicate_action_blocks: int = 0
