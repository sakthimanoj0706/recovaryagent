"""
Deterministic Custom Recovery Policy and Evaluation Engine for RecoverAI Policy Lab (Step 12).

Guarantees:
- Transparent Expected Economic Value calculation:
    EV(action) = P(recovery | context, action) * recoverable_amount - action_cost - expected_risk_loss
- Strictly adheres to deterministic safety rails:
    FinancialStateEngine -> Policy -> RecoveryFirewall -> Executor -> Verifier -> Audit
- Never bypasses RecoveryFirewall or executes unauthorized actions.
"""

import random
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

from state_engine.engine import FinancialStateEngine
from state_engine.models import FinancialState, PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from recovery.features import extract_payment_features
from agent.models import RecoveryAction, RecoveryPriority, RecoveryPlan, RecoveryContext, FirewallDecision
from agent.firewall import RecoveryFirewall
from execution.executor import ActionExecutor
from execution.simulator import SyntheticSimulationEngine
from execution.verifier import RecoveryVerifier
from execution.outcome import determine_final_outcome, FinalOutcome
from benchmark.generator import SyntheticLifecycle
from benchmark.strategies import ExecutionResult
from benchmark.models import CostModelConfig
from .models import EconomicEnvironment, CustomRecoveryPolicy, ActionExplanation


class CustomPolicyEvaluator:
    """
    Evaluates custom merchant policies and calculates transparent Expected Economic Value.
    """

    HARD_DECLINE_CODES = {"CARD_BLOCKED", "CARD_EXPIRED", "EXPIRED_CARD", "BAD_VPA", "INVALID_ACCOUNT"}

    @classmethod
    def evaluate_expected_values(
        cls,
        amount: float,
        base_probability: float,
        failure_code: str,
        hardness: str,
        retry_count: int,
        previous_actions: List[str],
        env: EconomicEnvironment,
        policy: CustomRecoveryPolicy,
    ) -> Tuple[RecoveryAction, RecoveryPriority, str, float, List[ActionExplanation]]:
        """
        Evaluate permitted recovery actions and compute transparent expected value.
        """
        explanations: List[ActionExplanation] = []
        clean_code = failure_code.upper().strip()
        is_hard = (hardness.lower() == "hard") or (clean_code in cls.HARD_DECLINE_CODES)
        prev_upper = [a.upper().strip() for a in previous_actions]

        # Multiplier bounded to sensible conversion range [0.01, 0.99]
        eff_prob = min(0.99, max(0.01, base_probability * env.recovery_probability_multiplier))

        # Risk tolerance scaling
        risk_weight = 1.0
        if policy.risk_tolerance == "LOW" or env.risk_tolerance == "LOW":
            risk_weight = 1.5
        elif policy.risk_tolerance == "HIGH" or env.risk_tolerance == "HIGH":
            risk_weight = 0.5

        # ---------------------------------------------------------------------
        # 1. Evaluate RETRY
        # ---------------------------------------------------------------------
        retry_permitted = (
            policy.enable_retry
            and not is_hard
            and (retry_count < policy.max_retries)
            and (retry_count < env.max_retries)
            and ("RETRY" not in prev_upper)
        )
        if retry_permitted:
            p_retry = eff_prob * 0.95
            exp_gross_retry = amount * p_retry
            cost_retry = env.retry_cost
            risk_retry = 0.0
            env_retry = exp_gross_retry - cost_retry - (risk_retry * risk_weight)
            dec_retry = "RECOVERY_WORTHWHILE" if env_retry > policy.min_expected_net_value else "NEGATIVE_EV"
            rsn_retry = f"Automated gateway retry with expected net value Rs. {env_retry:,.2f}"
        else:
            p_retry = 0.0
            exp_gross_retry = 0.0
            cost_retry = env.retry_cost
            risk_retry = env.scheme_penalty if is_hard else 0.0
            env_retry = -cost_retry - risk_retry
            dec_retry = "BLOCKED"
            if is_hard:
                rsn_retry = f"Hard decline policy prohibits RETRY for '{clean_code}'"
            elif retry_count >= policy.max_retries:
                rsn_retry = f"Retry count ceiling ({policy.max_retries}) reached"
            elif not policy.enable_retry:
                rsn_retry = "Automated retry disabled by policy configuration"
            else:
                rsn_retry = "Duplicate retry action prevented"

        explanations.append(
            ActionExplanation(
                action="RETRY",
                probability=round(p_retry, 4),
                expected_gross=round(exp_gross_retry, 2),
                action_cost=round(cost_retry, 2),
                expected_risk=round(risk_retry, 2),
                expected_net_value=round(env_retry, 2),
                decision=dec_retry,
                reason=rsn_retry,
            )
        )

        # ---------------------------------------------------------------------
        # 2. Evaluate PAYMENT_LINK
        # ---------------------------------------------------------------------
        link_permitted = policy.enable_payment_link and ("PAYMENT_LINK" not in prev_upper)
        if link_permitted:
            p_link = eff_prob * 1.0
            exp_gross_link = amount * p_link
            cost_link = env.payment_link_cost + env.customer_contact_cost
            risk_link = 0.0
            env_link = exp_gross_link - cost_link
            dec_link = "RECOVERY_WORTHWHILE" if env_link > policy.min_expected_net_value else "NEGATIVE_EV"
            rsn_link = f"Fresh payment checkout session with expected net value Rs. {env_link:,.2f}"
        else:
            p_link = 0.0
            exp_gross_link = 0.0
            cost_link = env.payment_link_cost + env.customer_contact_cost
            risk_link = 0.0
            env_link = -cost_link
            dec_link = "BLOCKED"
            rsn_link = "Payment link disabled or already attempted"

        explanations.append(
            ActionExplanation(
                action="PAYMENT_LINK",
                probability=round(p_link, 4),
                expected_gross=round(exp_gross_link, 2),
                action_cost=round(cost_link, 2),
                expected_risk=round(risk_link, 2),
                expected_net_value=round(env_link, 2),
                decision=dec_link,
                reason=rsn_link,
            )
        )

        # ---------------------------------------------------------------------
        # 3. Evaluate REMINDER
        # ---------------------------------------------------------------------
        rem_permitted = policy.enable_reminder and ("REMINDER" not in prev_upper)
        if rem_permitted:
            p_rem = eff_prob * 0.70
            exp_gross_rem = amount * p_rem
            cost_rem = env.customer_contact_cost
            risk_rem = 0.0
            env_rem = exp_gross_rem - cost_rem
            dec_rem = "RECOVERY_WORTHWHILE" if env_rem > policy.min_expected_net_value else "NEGATIVE_EV"
            rsn_rem = f"Gentle customer notification with expected net value Rs. {env_rem:,.2f}"
        else:
            p_rem = 0.0
            exp_gross_rem = 0.0
            cost_rem = env.customer_contact_cost
            risk_rem = 0.0
            env_rem = -cost_rem
            dec_rem = "BLOCKED"
            rsn_rem = "Reminder disabled or already attempted"

        explanations.append(
            ActionExplanation(
                action="REMINDER",
                probability=round(p_rem, 4),
                expected_gross=round(exp_gross_rem, 2),
                action_cost=round(cost_rem, 2),
                expected_risk=round(risk_rem, 2),
                expected_net_value=round(env_rem, 2),
                decision=dec_rem,
                reason=rsn_rem,
            )
        )

        # ---------------------------------------------------------------------
        # 4. Decision Selection based on Policy Rules & Optimal EV
        # ---------------------------------------------------------------------
        # High value override check
        if policy.escalate_on_high_value and amount >= policy.high_value_threshold:
            return (
                RecoveryAction.ESCALATE,
                RecoveryPriority.CRITICAL,
                f"Transaction amount Rs. {amount:,.2f} exceeds high-value threshold Rs. {policy.high_value_threshold:,.2f}. Escalating to VIP operations.",
                0.95,
                explanations,
            )

        # Find best permitted candidate with positive ENV
        candidates: List[Tuple[RecoveryAction, float, str]] = []
        if retry_permitted and env_retry > policy.min_expected_net_value:
            candidates.append((RecoveryAction.RETRY, env_retry, f"Selected RETRY (Highest positive EV: Rs. {env_retry:,.2f})"))
        if link_permitted and env_link > policy.min_expected_net_value:
            candidates.append((RecoveryAction.PAYMENT_LINK, env_link, f"Selected PAYMENT_LINK (Highest positive EV: Rs. {env_link:,.2f})"))
        if rem_permitted and env_rem > policy.min_expected_net_value:
            candidates.append((RecoveryAction.REMINDER, env_rem, f"Selected REMINDER (Positive EV: Rs. {env_rem:,.2f})"))

        if candidates:
            # Sort by ENV descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            chosen_action, best_ev, reason_str = candidates[0]
            priority = RecoveryPriority.HIGH if best_ev > 500.0 else RecoveryPriority.MEDIUM
            return (chosen_action, priority, reason_str, eff_prob, explanations)

        # Hard decline fallback: if payment link is permitted & positive, use it, else stop
        if is_hard:
            return (
                RecoveryAction.STOP,
                RecoveryPriority.LOW,
                f"Hard decline '{clean_code}' cannot be automated safely. Recovery withheld.",
                eff_prob,
                explanations,
            )

        # All actions have non-positive EV or are exhausted
        return (
            RecoveryAction.STOP,
            RecoveryPriority.LOW,
            "Expected net economic value is non-positive or all recovery channels exhausted. Recovery withheld.",
            eff_prob,
            explanations,
        )


class CustomRecoveryStrategy:
    """
    Executes synthetic payment lifecycles under a CustomRecoveryPolicy within full financial safety rails.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.state_engine = FinancialStateEngine()
        self.prob_model = RecoveryProbabilityModel(random_state=seed)
        
        # Train baseline model on calibrated dataset
        train_df = pd.DataFrame([
            {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
            {"amount": 5000.0, "method": "card", "customer_segment": "returning", "error_code": "TIMEOUT", "hardness": "soft"},
            {"amount": 25000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "INSUFFICIENT_FUNDS", "hardness": "soft"},
            {"amount": 15000.0, "method": "upi", "customer_segment": "returning", "error_code": "BANK_TIMEOUT", "hardness": "soft"},
            {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"},
            {"amount": 500.0, "method": "upi", "customer_segment": "new", "error_code": "BAD_VPA", "hardness": "hard"},
            {"amount": 2000.0, "method": "netbanking", "customer_segment": "new", "error_code": "USER_CANCELLED", "hardness": "hard"},
            {"amount": 12000.0, "method": "card", "customer_segment": "standard", "error_code": "CARD_EXPIRED", "hardness": "hard"},
        ])
        y_train = pd.Series([1, 1, 1, 1, 0, 0, 0, 0])
        self.prob_model.train(train_df, y_train)

        self.firewall = RecoveryFirewall()
        self.simulator = SyntheticSimulationEngine(simulation_seed=seed)
        self.executor = ActionExecutor(simulator=self.simulator)
        self.verifier = RecoveryVerifier(state_engine=self.state_engine)

    def execute_lifecycle(
        self,
        lifecycle: SyntheticLifecycle,
        env: EconomicEnvironment,
        policy: CustomRecoveryPolicy,
    ) -> ExecutionResult:
        res = ExecutionResult()
        payment = lifecycle.payment
        amount = payment.amount
        events = lifecycle.events
        order_events = lifecycle.order_events

        # -----------------------------------------------------------------
        # 1. PROVE: Financial State Engine evaluation
        # -----------------------------------------------------------------
        state_eval = self.state_engine.evaluate_payment(payment, events, order_events)
        fin_state = state_eval.state

        # Case: Clean Success or Already Recovered (Late-Auth / Flip-Flop)
        if fin_state == FinancialState.ALREADY_RECOVERED:
            rec_amt = state_eval.recovered_amount if state_eval.recovered_amount is not None else amount
            out_amt = state_eval.outstanding_amount if state_eval.outstanding_amount is not None else max(0.0, amount - rec_amt)

            if lifecycle.is_refunded:
                res.withheld_amount = amount
                res.already_rec_protected = True
                return res

            if lifecycle.has_late_capture or lifecycle.archetype.value in ("ALREADY_RECOVERED", "DUPLICATE", "OUT_OF_ORDER", "LATE_CAPTURE"):
                res.already_rec_protected = True
                res.recovered_amount = rec_amt
                res.outstanding_amount = out_amt
                return res

            res.recovered_amount = rec_amt
            res.outstanding_amount = out_amt
            return res

        # Case: In-Flight Uncertain State
        if fin_state == FinancialState.UNCERTAIN:
            res.pending_amount = amount
            res.withheld_amount = 0.0
            return res

        # Case: Reconciliation Exception
        if fin_state == FinancialState.EXCEPTION:
            if policy.escalate_on_exception:
                res.escalated_amount = amount
                res.manual_escalations += 1
            else:
                res.withheld_amount = amount
            return res

        # -----------------------------------------------------------------
        # 2. PRIORITIZE: Recovery Intelligence + Custom Policy Decision
        # -----------------------------------------------------------------
        res.is_opportunity = True

        feats = extract_payment_features(payment, events)
        base_prob = float(self.prob_model.predict_probability(feats))

        failure_event = next((e for e in reversed(events) if e.event == "payment.failed"), None)
        err_code = failure_event.error_code if failure_event else "UNKNOWN"
        hardness = failure_event.hardness if failure_event else "soft"

        action, priority, reason, eff_prob, _ = CustomPolicyEvaluator.evaluate_expected_values(
            amount=amount,
            base_probability=base_prob,
            failure_code=err_code,
            hardness=hardness,
            retry_count=0,
            previous_actions=[],
            env=env,
            policy=policy,
        )

        cost_of_recovery = env.payment_link_cost + env.customer_contact_cost
        env_val = (amount * eff_prob) - cost_of_recovery

        if action == RecoveryAction.STOP:
            res.withheld_amount = amount
            res.attempted = False
            return res

        if action == RecoveryAction.ESCALATE:
            res.escalated_amount = amount
            res.manual_escalations += 1
            return res

        # -----------------------------------------------------------------
        # 3. GUARD: Deterministic Recovery Firewall
        # -----------------------------------------------------------------
        ctx = RecoveryContext(
            payment_id=payment.payment_id,
            amount=amount,
            method=payment.method,
            customer_segment=payment.customer_segment or "standard",
            financial_state=fin_state.value,
            recovery_probability=eff_prob,
            expected_net_value=env_val,
            failure_reason=err_code,
            hardness=hardness,
            retry_count=0,
            previous_attempts=0,
            previous_actions=[],
        )

        plan = RecoveryPlan(
            payment_id=payment.payment_id,
            action=action,
            priority=priority,
            reason=reason,
            confidence=eff_prob,
        )

        firewall_verdict = self.firewall.validate_action(context=ctx, plan=plan)
        if firewall_verdict.status != FirewallDecision.APPROVED:
            res.withheld_amount = amount
            if firewall_verdict.rule_id == "FIREWALL-004":
                res.hard_decline_prevented = True
            elif firewall_verdict.rule_id == "FIREWALL-009":
                res.duplicate_prevented = True
            return res

        # -----------------------------------------------------------------
        # 4. ACT: Bounded Gateway Execution (Simulation)
        # -----------------------------------------------------------------
        res.attempted = True
        action_to_exec = firewall_verdict.action or plan.action
        if action_to_exec == RecoveryAction.RETRY:
            res.gateway_retries += 1
        elif action_to_exec == RecoveryAction.PAYMENT_LINK:
            res.payment_links += 1
            res.customer_contacts += 1
        elif action_to_exec == RecoveryAction.REMINDER:
            res.customer_contacts += 1
        elif action_to_exec == RecoveryAction.ESCALATE:
            res.manual_escalations += 1

        customer_actually_pays = (self.rng.random() < lifecycle.true_customer_willingness)
        exec_response = self.executor.execute(
            payment=payment,
            action=action_to_exec,
            force_success=customer_actually_pays,
        )


        # -----------------------------------------------------------------
        # 5. VERIFY: Independent Ledger State Verification
        # -----------------------------------------------------------------
        verif_result = self.verifier.verify(
            payment=payment,
            original_events=events,
            execution_response=exec_response,
            order_events=order_events,
        )

        # -----------------------------------------------------------------
        # 6. OUTCOME: Unified Accounting Determination
        # -----------------------------------------------------------------
        final_outcome, recovered, withheld, _ = determine_final_outcome(
            initial_state=fin_state.value,
            firewall_result=firewall_verdict,
            verification=verif_result,
            amount=amount,
            expected_net_value=env_val,
        )

        if final_outcome == FinalOutcome.RECOVERY_SUCCESS.value:
            res.recovered_amount = recovered
            res.outstanding_amount = max(0.0, amount - recovered)
            res.succeeded = True
        else:
            res.withheld_amount = amount
            res.failed = True

        return res
