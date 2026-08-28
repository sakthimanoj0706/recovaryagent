"""
Recovery Firewall for RecoverAI.

Enforces deterministic hard safety boundaries (FIREWALL-001 through FIREWALL-010)
on all agent proposals before any execution is permitted.
"""

from typing import Optional, List, Dict, Any
from .models import RecoveryAction, FirewallDecision, FirewallResult, RecoveryContext, RecoveryPlan


HARD_DECLINE_CODES = {"CARD_BLOCKED", "CARD_EXPIRED", "BAD_VPA", "BANK_DECLINE", "USER_CANCELLED"}


class RecoveryFirewall:
    """
    Deterministic safety firewall gating all proposed recovery actions.
    The LLM is an ADVISOR; the Recovery Firewall is the absolute AUTHORITY.
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def validate_action(
        self,
        context: RecoveryContext,
        plan: Optional[RecoveryPlan] = None,
        proposed_action: Optional[RecoveryAction] = None,
        llm_valid: bool = True,
    ) -> FirewallResult:
        """
        Evaluate proposed action against all hard safety rules in sequence.
        """
        # -----------------------------------------------------------------
        # FIREWALL-010: Invalid LLM Output / Planning Failure
        # -----------------------------------------------------------------
        if not llm_valid or (plan is None and proposed_action is None):
            return FirewallResult(
                status=FirewallDecision.ESCALATE,
                action=RecoveryAction.ESCALATE,
                rule_id="FIREWALL-010",
                reason="Invalid LLM output or planning failure. Escalating to human operations.",
            )

        action = proposed_action or (plan.action if plan else RecoveryAction.ESCALATE)
        fin_state = str(context.financial_state).upper()
        env = context.expected_net_value if context.expected_net_value is not None else -1.0
        hardness = (context.hardness or "soft").lower()
        err_code = (context.failure_reason or "").upper()
        attempts = max(context.previous_attempts, context.retry_count)
        prev_actions = [str(a).upper() for a in context.previous_actions]

        # -----------------------------------------------------------------
        # FIREWALL-006: State is ALREADY_RECOVERED
        # -----------------------------------------------------------------
        if fin_state == "ALREADY_RECOVERED":
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-006",
                reason="Financial state is ALREADY_RECOVERED. All recovery actions blocked.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-007: State is UNCERTAIN
        # -----------------------------------------------------------------
        if fin_state == "UNCERTAIN":
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.WAIT,
                rule_id="FIREWALL-007",
                reason="Financial state is UNCERTAIN. Awaiting asynchronous payment confirmation.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-008: State is EXCEPTION or conflicting
        # -----------------------------------------------------------------
        if fin_state == "EXCEPTION":
            return FirewallResult(
                status=FirewallDecision.ESCALATE,
                action=RecoveryAction.ESCALATE,
                rule_id="FIREWALL-008",
                reason="Conflicting financial evidence / EXCEPTION state. Escalating to human operations.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-001: State is not VERIFIED_LOST
        # -----------------------------------------------------------------
        if fin_state != "VERIFIED_LOST":
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-001",
                reason=f"Financial state '{fin_state}' does not permit recovery.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-002: Expected Net Value <= 0
        # -----------------------------------------------------------------
        if context.expected_net_value is not None and context.expected_net_value <= 0.0:
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-002",
                reason=f"Recovery is not economically worthwhile (Expected Net Value: Rs. {context.expected_net_value:,.2f} <= 0).",
            )


        # -----------------------------------------------------------------
        # FIREWALL-003: Recovery Decision check (Action is STOP)
        # -----------------------------------------------------------------
        if action == RecoveryAction.STOP:
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-003",
                reason="Recovery decision is not worthwhile / STOP requested.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-004: Hard decline + RETRY
        # -----------------------------------------------------------------
        if action == RecoveryAction.RETRY and (hardness == "hard" or err_code in HARD_DECLINE_CODES):
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.ESCALATE,
                rule_id="FIREWALL-004",
                reason=f"Hard decline confirmed ({err_code} / {hardness}). Automated RETRY is strictly prohibited.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-005: Maximum retry limit reached
        # -----------------------------------------------------------------
        if action == RecoveryAction.RETRY and attempts >= self.max_retries:
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-005",
                reason=f"Maximum retry limit reached ({attempts} >= {self.max_retries}). Halting automated retries.",
            )

        # -----------------------------------------------------------------
        # FIREWALL-009: Duplicate action check
        # -----------------------------------------------------------------
        if action.value.upper() in prev_actions:
            return FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-009",
                reason=f"Duplicate recovery action '{action.value}' blocked for payment {context.payment_id}.",
            )

        # -----------------------------------------------------------------
        # ACTION APPROVED
        # -----------------------------------------------------------------
        return FirewallResult(
            status=FirewallDecision.APPROVED,
            action=action,
            rule_id=None,
            reason="Action passed all deterministic firewall policies and economic thresholds.",
        )

    def evaluate_plan(
        self,
        financial_state: Any,
        expected_net_value: Optional[float],
        recommendation: Optional[RecoveryPlan],
        context: Optional[RecoveryContext] = None,
    ) -> FirewallResult:
        """Convenience method wrapping validate_action for orchestrators."""
        if context is None:
            state_val = financial_state.value if hasattr(financial_state, "value") else str(financial_state)
            pid = getattr(recommendation, "payment_id", "unknown") if recommendation else "unknown"
            context = RecoveryContext(
                payment_id=pid,
                amount=0.0,
                financial_state=state_val,
                expected_net_value=expected_net_value,
            )
        return self.validate_action(
            context=context,
            plan=recommendation,
            proposed_action=recommendation.action if recommendation else None,
            llm_valid=recommendation is not None,
        )

