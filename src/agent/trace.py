"""
Structured Decision Trace Model for RecoverAI.
Captures the 6-stage bounded lifecycle: PROVE -> PRIORITIZE -> PLAN -> GUARD -> ACT -> VERIFY.
Strictly prohibits storing or exposing private LLM chain-of-thought.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ProveStage(BaseModel):
    financial_state: str
    state_rule_id: Optional[str] = None
    state_reason: str


class PrioritizeStage(BaseModel):
    recovery_probability: Optional[float] = None
    expected_net_value: Optional[float] = None
    economic_decision: str  # "RECOVERY_WORTHWHILE" | "DO_NOT_RECOVER" | "BYPASSED" | "INELIGIBLE"


class PlanStage(BaseModel):
    agent_action: str  # "PAYMENT_LINK" | "RETRY" | "REMINDER" | "ESCALATE" | "STOP" | "BYPASSED"
    agent_reason: str  # Concise explanation only (NO hidden chain-of-thought)
    agent_mode: str = "demo"  # "live" | "demo"


class GuardStage(BaseModel):
    firewall_decision: str  # "APPROVED" | "STOP" | "ESCALATE"
    firewall_rule_id: Optional[str] = None
    firewall_reason: str


class ActStage(BaseModel):
    execution_id: Optional[str] = None
    execution_status: str  # "SIMULATED_SUCCESS" | "SIMULATED_FAILURE" | "BLOCKED_BY_FIREWALL" | "NOT_EXECUTED"


class VerifyStage(BaseModel):
    verification_state: str
    verification_source: str = "FINANCIAL STATE ENGINE"
    final_result: str


class AccountingStage(BaseModel):
    amount_recovered: float = 0.0
    amount_withheld: float = 0.0
    amount_pending: float = 0.0
    amount_escalated: float = 0.0


class AgentDecisionTrace(BaseModel):
    """
    Complete structured decision trace for a single payment recovery lifecycle.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    amount: float

    prove: ProveStage
    prioritize: PrioritizeStage
    plan: PlanStage
    guard: GuardStage
    act: ActStage
    verify: VerifyStage
    accounting: AccountingStage

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "prove": self.prove.model_dump(),
            "prioritize": self.prioritize.model_dump(),
            "plan": self.plan.model_dump(),
            "guard": self.guard.model_dump(),
            "act": self.act.model_dump(),
            "verify": self.verify.model_dump(),
            "accounting": self.accounting.model_dump(),
            "timestamp": self.timestamp,
        }


def build_decision_trace(
    outcome: Any,
    agent_mode: str = "demo",
    state_rule_id: Optional[str] = None,
    state_reason: Optional[str] = None,
) -> AgentDecisionTrace:
    """
    Helper function to build an AgentDecisionTrace from a ClosedLoopOutcome.
    """
    init_state = str(outcome.initial_state)

    # 1. PROVE
    rule_id = state_rule_id or (
        "STATE-RULE-001"
        if init_state == "ALREADY_RECOVERED"
        else (
            "STATE-RULE-004"
            if init_state == "UNCERTAIN"
            else (
                "STATE-RULE-000"
                if init_state == "EXCEPTION"
                else "STATE-RULE-005"
            )
        )
    )
    st_reason = (
        state_reason
        or (
            "Payment initially failed but subsequently authorized/captured."
            if init_state == "ALREADY_RECOVERED"
            else (
                "Payment in-flight or within pending window; awaiting asynchronous confirmation."
                if init_state == "UNCERTAIN"
                else (
                    "Settlement discrepancy or impossible lifecycle transition detected."
                    if init_state == "EXCEPTION"
                    else "Payment failure confirmed unrecovered with terminal failure event."
                )
            )
        )
    )
    prove_stage = ProveStage(
        financial_state=init_state,
        state_rule_id=rule_id,
        state_reason=st_reason,
    )

    # 2. PRIORITIZE
    if init_state != "VERIFIED_LOST":
        econ_dec = "BYPASSED"
        prob = None
        env = None
    elif outcome.expected_net_value is not None and outcome.expected_net_value > 0:
        econ_dec = "RECOVERY_WORTHWHILE"
        prob = outcome.recovery_probability
        env = outcome.expected_net_value
    elif outcome.expected_net_value is not None and outcome.expected_net_value <= 0:
        econ_dec = "DO_NOT_RECOVER"
        prob = outcome.recovery_probability
        env = outcome.expected_net_value
    else:
        econ_dec = "INELIGIBLE"
        prob = outcome.recovery_probability
        env = outcome.expected_net_value

    prioritize_stage = PrioritizeStage(
        recovery_probability=prob,
        expected_net_value=env,
        economic_decision=econ_dec,
    )

    # 3. PLAN
    if init_state != "VERIFIED_LOST":
        plan_action = "BYPASSED"
        plan_reason = f"Financial state is '{init_state}'. Recovery planning not permitted."
    elif outcome.expected_net_value is not None and outcome.expected_net_value <= 0:
        plan_action = "BYPASSED"
        plan_reason = f"Negative expected net value (Rs. {outcome.expected_net_value:,.2f} <= 0). Recovery economically irrational."
    else:
        plan_action = outcome.agent_action or "STOP"
        plan_reason = outcome.agent_reason or "Recovery action planned according to failure policy."

    plan_stage = PlanStage(
        agent_action=plan_action,
        agent_reason=plan_reason,
        agent_mode=agent_mode,
    )

    # 4. GUARD
    guard_stage = GuardStage(
        firewall_decision=outcome.firewall_decision,
        firewall_rule_id=outcome.firewall_rule,
        firewall_reason=outcome.firewall_reason or "Firewall policy evaluated.",
    )

    # 5. ACT
    exec_id = outcome.execution_id
    if exec_id:
        exec_st = outcome.execution_status
    elif outcome.firewall_decision in ["STOP", "ESCALATE"]:
        exec_st = "BLOCKED_BY_FIREWALL"
    else:
        exec_st = "NOT_EXECUTED"

    act_stage = ActStage(
        execution_id=exec_id,
        execution_status=exec_st,
    )

    # 6. VERIFY
    verify_stage = VerifyStage(
        verification_state=outcome.verification_state,
        verification_source=outcome.source_of_truth or "FINANCIAL STATE ENGINE",
        final_result=outcome.final_outcome,
    )

    # 7. ACCOUNTING
    amt = float(outcome.amount)
    f_res = outcome.final_outcome
    pending = amt if f_res == "WAIT" else float(getattr(outcome, "amount_pending", 0.0))
    escalated = amt if f_res == "ESCALATED_TO_OPERATIONS" else float(getattr(outcome, "amount_escalated", 0.0))

    accounting_stage = AccountingStage(
        amount_recovered=float(outcome.amount_recovered),
        amount_withheld=float(outcome.amount_withheld),
        amount_pending=pending,
        amount_escalated=escalated,
    )

    return AgentDecisionTrace(
        payment_id=outcome.payment_id,
        order_id=outcome.order_id,
        amount=amt,
        prove=prove_stage,
        prioritize=prioritize_stage,
        plan=plan_stage,
        guard=guard_stage,
        act=act_stage,
        verify=verify_stage,
        accounting=accounting_stage,
    )
