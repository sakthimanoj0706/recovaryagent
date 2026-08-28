"""
Outcome determination and data structures for RecoverAI Closed-Loop Verification.
"""

from enum import Enum
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from .verifier import VerificationResult
from agent.models import FirewallResult, FirewallDecision, RecoveryPlan


class FinalOutcome(str, Enum):
    """Enumeration of final closed-loop execution outcomes."""
    RECOVERY_SUCCESS = "RECOVERY_SUCCESS"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    WAIT = "WAIT"
    RECOVERY_WAITING_ASYNC = "RECOVERY_WAITING_ASYNC"
    ESCALATED_TO_OPERATIONS = "ESCALATED_TO_OPERATIONS"
    NO_ACTION = "NO_ACTION"
    CORRECTLY_WITHHELD = "CORRECTLY_WITHHELD"
    SAFE_STOP = "SAFE_STOP"
    MAX_RETRY_PROTECTION = "MAX_RETRY_PROTECTION"
    DUPLICATE_ACTION_BLOCKED = "DUPLICATE_ACTION_BLOCKED"


class ClosedLoopOutcome(BaseModel):
    """
    Complete end-to-end outcome of a closed-loop recovery evaluation and execution.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    amount: float
    initial_state: str
    recovery_probability: Optional[float] = None
    expected_net_value: Optional[float] = None

    agent_action: Optional[str] = None
    agent_reason: Optional[str] = None
    confidence: float = 1.0

    firewall_decision: str
    firewall_rule: Optional[str] = None
    firewall_reason: Optional[str] = None

    execution_id: Optional[str] = None
    execution_status: str
    execution_message: Optional[str] = None

    verification_state: str
    source_of_truth: str = "FINANCIAL STATE ENGINE"

    final_outcome: str
    amount_recovered: float = 0.0
    amount_withheld: float = 0.0
    amount_pending: float = 0.0
    amount_escalated: float = 0.0
    reason: str

    simulation_flag: bool = True
    retry_count: int = 0
    decision_trace: Optional[Dict[str, Any]] = None


def determine_final_outcome(
    initial_state: str,
    firewall_result: FirewallResult,
    verification: Optional[VerificationResult],
    amount: float,
    expected_net_value: Optional[float] = None,
    duplicate_blocked: bool = False,
    max_retry_blocked: bool = False,
) -> Tuple[str, float, float, str]:
    """
    Evaluate all closed-loop signals to determine the exact outcome, amount recovered, and amount withheld.
    Returns:
        (final_outcome, amount_recovered, amount_withheld, explanation)
    """
    # Case A: Duplicate Action Blocked
    if duplicate_blocked or firewall_result.rule_id == "FIREWALL-009":
        return (
            FinalOutcome.DUPLICATE_ACTION_BLOCKED.value,
            0.0,
            amount,
            f"Duplicate action blocked. Rs. {amount:,.2f} correctly withheld.",
        )

    # Case B: Max Retry Protection
    if max_retry_blocked or firewall_result.rule_id == "FIREWALL-005":
        return (
            FinalOutcome.MAX_RETRY_PROTECTION.value,
            0.0,
            amount,
            f"Maximum retry limit reached. Rs. {amount:,.2f} correctly withheld to avoid gateway spam.",
        )

    # Case C: Conflicting state / EXCEPTION / Firewall ESCALATE
    if (
        initial_state == "EXCEPTION"
        or firewall_result.status == FirewallDecision.ESCALATE
        or firewall_result.rule_id in ["FIREWALL-008", "FIREWALL-010"]
    ):
        return (
            FinalOutcome.ESCALATED_TO_OPERATIONS.value,
            0.0,
            0.0,
            f"Conflicting state or policy exception. Escalated to operations queue. Rs. {amount:,.2f} pending manual reconciliation.",
        )

    # Case D: Payment Already Recovered Initially (FAILED != LOST)
    if initial_state == "ALREADY_RECOVERED" or firewall_result.rule_id == "FIREWALL-006":
        return (
            FinalOutcome.NO_ACTION.value,
            0.0,
            amount,
            f"Payment already recovered. Recovery blocked: Rs. {amount:,.2f} correctly withheld.",
        )

    # Case E: State UNCERTAIN / FIREWALL-007
    if initial_state == "UNCERTAIN" or firewall_result.rule_id == "FIREWALL-007":
        return (
            FinalOutcome.WAIT.value,
            0.0,
            0.0,
            f"Financial state is UNCERTAIN. Awaiting asynchronous clearing confirmation.",
        )


    # Case F: Hard Failure Blocked by Firewall (e.g. CARD_BLOCKED + RETRY)
    if firewall_result.rule_id == "FIREWALL-004":
        return (
            FinalOutcome.SAFE_STOP.value,
            0.0,
            amount,
            f"Hard decline cannot be automatically retried. Rs. {amount:,.2f} correctly withheld.",
        )

    # Case G: Negative Economics / DO_NOT_RECOVER
    if firewall_result.rule_id == "FIREWALL-002" or (expected_net_value is not None and expected_net_value <= 0):
        return (
            FinalOutcome.CORRECTLY_WITHHELD.value,
            0.0,
            amount,
            f"Recovery is economically irrational. Rs. {amount:,.2f} correctly withheld.",
        )

    # Case H: Action was executed and verified
    if verification is not None:
        v_state = verification.verified_financial_state.upper()
        if v_state == "ALREADY_RECOVERED":
            return (
                FinalOutcome.RECOVERY_SUCCESS.value,
                amount,
                0.0,
                f"Financial State Engine confirmed payment captured. Rs. {amount:,.2f} successfully recovered.",
            )
        elif v_state == "UNCERTAIN":
            return (
                FinalOutcome.RECOVERY_WAITING_ASYNC.value,
                0.0,
                0.0,
                f"Payment entered UNCERTAIN / pending state. Awaiting asynchronous confirmation.",
            )
        elif v_state == "EXCEPTION":
            return (
                FinalOutcome.ESCALATED_TO_OPERATIONS.value,
                0.0,
                amount,
                f"Post-action verification triggered EXCEPTION. Escalated to operations.",
            )
        else:  # VERIFIED_LOST
            return (
                FinalOutcome.RECOVERY_FAILED.value,
                0.0,
                0.0,
                f"Action completed but Financial State Engine confirms payment remains VERIFIED_LOST.",
            )

    # Fallback for unhandled stops
    return (
        FinalOutcome.CORRECTLY_WITHHELD.value,
        0.0,
        amount,
        f"Action halted by safety policy. Rs. {amount:,.2f} correctly withheld.",
    )
