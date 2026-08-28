"""
Strongly typed schemas and Pydantic models for the Production-Style Agentic Recovery Orchestrator.
Enforces the fundamental architectural boundary:
The LLM is an ADVISOR; the deterministic engine is the FINANCIAL AUTHORITY.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AgentAction(str, Enum):
    """Strictly allowed agent recovery action space."""
    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    REMINDER = "REMINDER"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"
    STOP = "STOP"

    @classmethod
    def is_valid_action(cls, action_str: str) -> bool:
        try:
            cls(action_str.upper().strip())
            return True
        except (ValueError, AttributeError):
            return False


class AgentStepStage(str, Enum):
    """Discrete stages in the bounded agent recovery loop."""
    OBSERVE = "OBSERVE"
    REASON = "REASON"
    PLAN = "PLAN"
    POLICY_CHECK = "POLICY_CHECK"
    FIREWALL = "FIREWALL"
    ACT = "ACT"
    VERIFY = "VERIFY"
    REPLAN = "REPLAN"
    STOP = "STOP"


class ToolCallRecord(BaseModel):
    """Audit record of a controlled tool invocation."""
    model_config = ConfigDict(extra="allow")

    tool_name: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PolicyCheckRecord(BaseModel):
    """Audit record of a deterministic policy check."""
    model_config = ConfigDict(extra="allow")

    policy_name: str
    rule_id: str
    passed: bool
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentPlanResponse(BaseModel):
    """
    Strictly parsed and validated LLM JSON response.
    If the LLM generates any invalid action or malformed structure,
    it is rejected before touching the execution layer.
    """
    model_config = ConfigDict(extra="ignore")

    action: AgentAction
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reason: str = Field(default="LLM advisory recommendation.")
    requires_verification: bool = Field(default=True)

    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, v: Any) -> AgentAction:
        if isinstance(v, str):
            clean = v.upper().strip()
            if clean in AgentAction._value2member_map_:
                return AgentAction(clean)
        elif isinstance(v, AgentAction):
            return v
        raise ValueError(f"Action '{v}' is not in the allowed action space: {[a.value for a in AgentAction]}")


class AgentStepRecord(BaseModel):
    """Structured telemetry for a single step inside the bounded agent loop."""
    model_config = ConfigDict(extra="allow")

    step_number: int
    stage: str
    observation: Dict[str, Any] = Field(default_factory=dict)
    economic_signal: Optional[str] = None
    agent_proposal: Optional[str] = None
    agent_reason: Optional[str] = None
    confidence: Optional[float] = None
    policy_verdict: Optional[str] = None
    firewall_verdict: Optional[str] = None
    firewall_rule_id: Optional[str] = None
    firewall_reason: Optional[str] = None
    execution_id: Optional[str] = None
    execution_status: Optional[str] = None
    verification_state: Optional[str] = None
    verification_source: Optional[str] = "FINANCIAL STATE ENGINE"
    next_step: Optional[str] = None
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentRunResult(BaseModel):
    """
    Comprehensive, immutable output of an autonomous bounded agent run.
    Contains the full reasoning, tool, policy, firewall, and verification telemetry.
    """
    model_config = ConfigDict(extra="allow")

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:10]}")
    payment_id: str
    order_id: Optional[str] = None
    amount: float
    financial_state: str
    recovery_probability: Optional[float] = None
    expected_net_value: Optional[float] = None
    agent_action: str
    agent_reason: str
    confidence: float = 1.0
    firewall_decision: str
    firewall_rule: Optional[str] = None
    execution_status: str
    verification_state: str
    final_result: str
    steps_taken: List[AgentStepRecord] = Field(default_factory=list)
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    policy_checks: List[PolicyCheckRecord] = Field(default_factory=list)
    audit_reference: Optional[str] = None
    amount_recovered: float = 0.0
    amount_withheld: float = 0.0
    amount_pending: float = 0.0
    amount_escalated: float = 0.0
    iterations: int = 1
    memory_snapshot: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
