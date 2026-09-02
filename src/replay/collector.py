"""
Candidate Action Matrix Collector & Economic Evaluator for RecoverAI Replay (Step 13).

Evaluates all 5 candidate actions (RETRY, PAYMENT_LINK, REMINDER, ESCALATE, STOP) side-by-side
using actual mathematical unit economics, PolicyEngine rule checks, and RecoveryFirewall gates.
"""

from typing import List, Dict, Any, Optional
from benchmark.models import CostModelConfig
from agent.models import (
    RecoveryAction,
    RecoveryPriority,
    RecoveryPlan,
    RecoveryContext,
    FirewallDecision,
)
from agent.policy import PolicyEngine, get_failure_policy
from agent.firewall import RecoveryFirewall
from .models import ActionCandidateEvaluation


class CandidateMatrixEvaluator:
    """
    Evaluates candidate actions side-by-side to generate transparent, auditable decision matrices.
    """

    HARD_DECLINE_CODES = {"CARD_BLOCKED", "CARD_EXPIRED", "EXPIRED_CARD", "BAD_VPA", "INVALID_ACCOUNT"}

    @classmethod
    def evaluate_all_candidates(
        cls,
        payment_id: str,
        amount: float,
        base_probability: float,
        failure_code: str,
        hardness: str,
        retry_count: int,
        previous_actions: List[str],
        costs: CostModelConfig,
        policy_engine: PolicyEngine,
        firewall: RecoveryFirewall,
        financial_state: str,
        customer_segment: str = "standard",
    ) -> List[ActionCandidateEvaluation]:
        clean_code = (failure_code or "UNKNOWN").upper().strip()
        is_hard = (hardness.lower() == "hard") or (clean_code in cls.HARD_DECLINE_CODES)
        prev_upper = [a.upper().strip() for a in previous_actions]

        results: List[ActionCandidateEvaluation] = []

        # ---------------------------------------------------------------------
        # 1. Candidate: RETRY
        # ---------------------------------------------------------------------
        p_retry = 0.0 if is_hard else (base_probability * 0.95)
        exp_gross_retry = amount * p_retry
        cost_retry = costs.gateway_attempt_cost
        risk_retry = costs.hard_decline_penalty_cost if is_hard else 0.0
        env_retry = exp_gross_retry - cost_retry - risk_retry

        # Context
        ctx_retry = RecoveryContext(
            payment_id=payment_id,
            amount=amount,
            financial_state=financial_state,
            failure_code=clean_code,
            hardness=hardness,
            recovery_probability=p_retry,
            expected_net_value=env_retry,
            retry_count=retry_count,
            previous_actions=previous_actions,
            customer_segment=customer_segment,
        )

        # Policy check
        pol_retry_ok, pol_retry_status, pol_retry_rsn = policy_engine.validate_action_policy(
            context=ctx_retry,
            action="RETRY",
            previous_actions=previous_actions,
            retry_count=retry_count,
        )

        # Firewall check
        plan_retry = RecoveryPlan(
            payment_id=payment_id,
            action=RecoveryAction.RETRY,
            priority=RecoveryPriority.HIGH,
            reason="Candidate retry evaluation",
            confidence=p_retry,
        )
        fw_retry = firewall.validate_action(ctx_retry, plan_retry)
        fw_retry_status = "ALLOW" if fw_retry.status == FirewallDecision.APPROVED else "BLOCK"

        retry_eligible = pol_retry_ok and (fw_retry.status == FirewallDecision.APPROVED) and (env_retry > 0)
        results.append(
            ActionCandidateEvaluation(
                action="RETRY",
                eligible=retry_eligible,
                recovery_probability=round(p_retry, 4),
                recoverable_amount=round(amount, 2),
                expected_gross=round(exp_gross_retry, 2),
                action_cost=round(cost_retry, 2),
                expected_risk_loss=round(risk_retry, 2),
                expected_net_value=round(env_retry, 2),
                policy_status="ALLOW" if pol_retry_ok else "REJECT",
                firewall_status=fw_retry_status,
                selected=False,  # updated by selector
                reason=(
                    f"Automated gateway retry with ENV Rs. {env_retry:,.2f}."
                    if retry_eligible
                    else (fw_retry.reason if fw_retry.status != FirewallDecision.APPROVED else pol_retry_rsn)
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 2. Candidate: PAYMENT_LINK
        # ---------------------------------------------------------------------
        p_link = base_probability * 1.0
        exp_gross_link = amount * p_link
        cost_link = costs.payment_link_cost + costs.customer_contact_cost
        risk_link = 0.0
        env_link = exp_gross_link - cost_link

        ctx_link = RecoveryContext(
            payment_id=payment_id,
            amount=amount,
            financial_state=financial_state,
            failure_code=clean_code,
            hardness=hardness,
            recovery_probability=p_link,
            expected_net_value=env_link,
            retry_count=retry_count,
            previous_actions=previous_actions,
            customer_segment=customer_segment,
        )

        pol_link_ok, pol_link_status, pol_link_rsn = policy_engine.validate_action_policy(
            context=ctx_link,
            action="PAYMENT_LINK",
            previous_actions=previous_actions,
            retry_count=retry_count,
        )

        plan_link = RecoveryPlan(
            payment_id=payment_id,
            action=RecoveryAction.PAYMENT_LINK,
            priority=RecoveryPriority.HIGH if amount > 5000 else RecoveryPriority.MEDIUM,
            reason="Candidate payment link evaluation",
            confidence=p_link,
        )
        fw_link = firewall.validate_action(ctx_link, plan_link)
        fw_link_status = "ALLOW" if fw_link.status == FirewallDecision.APPROVED else "BLOCK"

        link_eligible = pol_link_ok and (fw_link.status == FirewallDecision.APPROVED) and (env_link > 0)
        results.append(
            ActionCandidateEvaluation(
                action="PAYMENT_LINK",
                eligible=link_eligible,
                recovery_probability=round(p_link, 4),
                recoverable_amount=round(amount, 2),
                expected_gross=round(exp_gross_link, 2),
                action_cost=round(cost_link, 2),
                expected_risk_loss=round(risk_link, 2),
                expected_net_value=round(env_link, 2),
                policy_status="ALLOW" if pol_link_ok else "REJECT",
                firewall_status=fw_link_status,
                selected=False,
                reason=(
                    f"Fresh checkout session with ENV Rs. {env_link:,.2f}."
                    if link_eligible
                    else (fw_link.reason if fw_link.status != FirewallDecision.APPROVED else pol_link_rsn)
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 3. Candidate: REMINDER
        # ---------------------------------------------------------------------
        p_rem = base_probability * 0.70
        exp_gross_rem = amount * p_rem
        cost_rem = costs.customer_contact_cost
        risk_rem = 0.0
        env_rem = exp_gross_rem - cost_rem

        ctx_rem = RecoveryContext(
            payment_id=payment_id,
            amount=amount,
            financial_state=financial_state,
            failure_code=clean_code,
            hardness=hardness,
            recovery_probability=p_rem,
            expected_net_value=env_rem,
            retry_count=retry_count,
            previous_actions=previous_actions,
            customer_segment=customer_segment,
        )

        pol_rem_ok, pol_rem_status, pol_rem_rsn = policy_engine.validate_action_policy(
            context=ctx_rem,
            action="REMINDER",
            previous_actions=previous_actions,
            retry_count=retry_count,
        )

        plan_rem = RecoveryPlan(
            payment_id=payment_id,
            action=RecoveryAction.REMINDER,
            priority=RecoveryPriority.MEDIUM,
            reason="Candidate reminder evaluation",
            confidence=p_rem,
        )
        fw_rem = firewall.validate_action(ctx_rem, plan_rem)
        fw_rem_status = "ALLOW" if fw_rem.status == FirewallDecision.APPROVED else "BLOCK"

        rem_eligible = pol_rem_ok and (fw_rem.status == FirewallDecision.APPROVED) and (env_rem > 0)
        results.append(
            ActionCandidateEvaluation(
                action="REMINDER",
                eligible=rem_eligible,
                recovery_probability=round(p_rem, 4),
                recoverable_amount=round(amount, 2),
                expected_gross=round(exp_gross_rem, 2),
                action_cost=round(cost_rem, 2),
                expected_risk_loss=round(risk_rem, 2),
                expected_net_value=round(env_rem, 2),
                policy_status="ALLOW" if pol_rem_ok else "REJECT",
                firewall_status=fw_rem_status,
                selected=False,
                reason=(
                    f"Customer notification with ENV Rs. {env_rem:,.2f}."
                    if rem_eligible
                    else (fw_rem.reason if fw_rem.status != FirewallDecision.APPROVED else pol_rem_rsn)
                ),
            )
        )


        # ---------------------------------------------------------------------
        # 4. Candidate: ESCALATE
        # ---------------------------------------------------------------------
        cost_esc = costs.manual_escalation_cost
        env_esc = -cost_esc
        results.append(
            ActionCandidateEvaluation(
                action="ESCALATE",
                eligible=True,
                recovery_probability=0.0,
                recoverable_amount=round(amount, 2),
                expected_gross=0.0,
                action_cost=round(cost_esc, 2),
                expected_risk_loss=0.0,
                expected_net_value=round(env_esc, 2),
                policy_status="ALLOW",
                firewall_status="ALLOW",
                selected=False,
                reason=f"Escalate to manual reconciliation queue (Operations cost Rs. {cost_esc:,.2f}).",
            )
        )

        # ---------------------------------------------------------------------
        # 5. Candidate: STOP
        # ---------------------------------------------------------------------
        results.append(
            ActionCandidateEvaluation(
                action="STOP",
                eligible=True,
                recovery_probability=0.0,
                recoverable_amount=round(amount, 2),
                expected_gross=0.0,
                action_cost=0.0,
                expected_risk_loss=0.0,
                expected_net_value=0.0,
                policy_status="ALLOW",
                firewall_status="ALLOW",
                selected=False,
                reason="Withhold recovery pursuit with zero operating loss and zero risk.",
            )
        )

        return results
