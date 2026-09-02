"""
Strategy Implementations for RecoverAI Economic Benchmark.

Defines:
1. NaiveRecoveryStrategy: Simplistic baseline recovery bot.
2. RecoverAIRecoveryStrategy: Full-pipeline bounded RecoverAI system.
"""

import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import pandas as pd

from state_engine.engine import FinancialStateEngine
from state_engine.models import FinancialState, PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from recovery.features import extract_payment_features
from agent.policy import PolicyEngine, determine_policy_action
from agent.firewall import RecoveryFirewall
from agent.models import RecoveryAction, RecoveryPriority, RecoveryPlan, RecoveryContext, FirewallDecision
from execution.executor import ActionExecutor
from execution.simulator import SyntheticSimulationEngine
from execution.verifier import RecoveryVerifier
from execution.outcome import determine_final_outcome, FinalOutcome
from .generator import SyntheticLifecycle
from .models import CostModelConfig





@dataclass
class ExecutionResult:
    """Internal result tracking for strategy execution on a single lifecycle."""
    recovered_amount: float = 0.0
    withheld_amount: float = 0.0
    pending_amount: float = 0.0
    escalated_amount: float = 0.0
    outstanding_amount: float = 0.0
    is_opportunity: bool = False
    attempted: bool = False
    succeeded: bool = False
    failed: bool = False
    is_unnecessary: bool = False
    is_false_recovery: bool = False
    is_double_charge: bool = False
    is_hard_decline_retried: bool = False
    hard_decline_prevented: bool = False
    duplicate_prevented: bool = False
    already_rec_protected: bool = False
    gateway_retries: int = 0
    payment_links: int = 0
    customer_contacts: int = 0
    manual_escalations: int = 0


class NaiveRecoveryStrategy:
    """
    Baseline naive recovery strategy.
    
    Flaws modeled:
    - Failed webhook = lost payment (ignores late auth / refunds / order successes).
    - Attempts recovery on already-captured payments (causes double-charging).
    - Blindly retries hard declines (CARD_BLOCKED).
    - Ignores unit economics (attempts negative ENV cases).
    - Confuses gateway link dispatch with guaranteed recovery (false recovery claims).
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def execute_lifecycle(self, lifecycle: SyntheticLifecycle, costs: CostModelConfig) -> ExecutionResult:
        res = ExecutionResult()
        payment = lifecycle.payment
        amount = payment.amount
        events = lifecycle.events

        # Identify if any failure event occurred
        has_failed = any(e.event == "payment.failed" for e in events)
        has_captured_initially = any(e.event in ("payment.captured", "payment.partially_captured") for e in events)

        # Baseline: If no failure, assume success, no action needed
        if not has_failed:
            if has_captured_initially:
                res.recovered_amount = lifecycle.ground_truth_collected
                res.outstanding_amount = max(0.0, amount - lifecycle.ground_truth_collected)
            else:
                res.pending_amount = amount
            return res

        # A failure occurred: Naive strategy treats this as a recovery opportunity
        res.is_opportunity = True
        res.attempted = True

        # Flaw 1: Naive ignores late captures or refunds
        if lifecycle.has_late_capture or lifecycle.archetype.value in ("ALREADY_RECOVERED", "DUPLICATE", "OUT_OF_ORDER", "LATE_CAPTURE"):
            # The money was already captured, but naive retries anyway!
            res.is_unnecessary = True
            res.is_double_charge = True
            res.gateway_retries += 1
            # Ground truth was already collected, but double-charge causes customer friction
            res.recovered_amount = amount
            res.failed = False
            res.succeeded = True
            return res

        if lifecycle.is_refunded:
            res.is_unnecessary = True
            res.payment_links += 1
            res.customer_contacts += 1
            res.withheld_amount = amount  # Money is unrecovered
            res.failed = True
            return res

        if lifecycle.is_partial_capture:
            res.is_unnecessary = True
            res.payment_links += 1
            res.recovered_amount = lifecycle.ground_truth_collected
            res.outstanding_amount = max(0.0, amount - lifecycle.ground_truth_collected)
            return res

        # Flaw 2: Naive retries hard declines via gateway
        if lifecycle.is_hard_decline:
            res.is_unnecessary = True
            res.is_hard_decline_retried = True
            res.gateway_retries += 1  # Wasted gateway call
            res.withheld_amount = amount  # Hard decline fails
            res.failed = True
            return res

        # Flaw 3: Naive sends payment links for soft declines and naively claims 100% success
        # In reality, only a fraction of customers actually complete the link (true willingness)
        res.payment_links += 1
        res.customer_contacts += 1
        
        customer_actually_pays = (self.rng.random() < lifecycle.true_customer_willingness)
        if customer_actually_pays:
            res.recovered_amount = amount
            res.succeeded = True
        else:
            # Flaw 4: False Recovery Claim! Naive assumes dispatched link = recovered cash
            res.is_false_recovery = True
            # Naive claims it recovered, but ground truth is unrecovered!
            res.recovered_amount = amount  # Naive books this unearned revenue
            res.succeeded = True

        return res


class RecoverAIRecoveryStrategy:
    """
    RecoverAI Strategy executing the REAL production-style pipeline:
    PROVE -> PRIORITIZE -> PLAN -> GUARD -> ACT -> VERIFY -> AUDIT.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.state_engine = FinancialStateEngine()
        self.prob_model = RecoveryProbabilityModel(random_state=seed)
        # Train on calibrated representative dataset
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

        self.policy_engine = PolicyEngine()
        self.firewall = RecoveryFirewall()
        self.simulator = SyntheticSimulationEngine(simulation_seed=seed)
        self.executor = ActionExecutor(simulator=self.simulator)
        self.verifier = RecoveryVerifier(state_engine=self.state_engine)

    def execute_lifecycle(self, lifecycle: SyntheticLifecycle, costs: CostModelConfig) -> ExecutionResult:
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

        # Case: Clean Success or Already Recovered (Late-Auth / Partial Capture)
        if fin_state == FinancialState.ALREADY_RECOVERED:
            rec_amt = state_eval.recovered_amount if state_eval.recovered_amount is not None else amount
            out_amt = state_eval.outstanding_amount if state_eval.outstanding_amount is not None else max(0.0, amount - rec_amt)
            
            if lifecycle.is_refunded:
                # Refunded payment: Stop recovery
                res.withheld_amount = amount
                res.already_rec_protected = True
                return res

            if lifecycle.has_late_capture or lifecycle.archetype.value in ("ALREADY_RECOVERED", "DUPLICATE", "OUT_OF_ORDER", "LATE_CAPTURE"):
                res.already_rec_protected = True
                # Protected against double charging!
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
            res.escalated_amount = amount
            res.manual_escalations += 1
            return res

        # -----------------------------------------------------------------
        # 2. PRIORITIZE: Recovery Intelligence (Probability & ENV)
        # -----------------------------------------------------------------
        res.is_opportunity = True
        
        feats = extract_payment_features(payment, events)
        prob = float(self.prob_model.predict_probability(feats))
        cost_of_recovery = costs.payment_link_cost + costs.customer_contact_cost
        expected_gross = amount * prob
        env = expected_gross - cost_of_recovery

        # Negative ENV check
        if env <= 0.0:
            res.withheld_amount = amount
            res.attempted = False
            return res


        # -----------------------------------------------------------------
        # 3. PLAN & GUARD: Policy Engine + Recovery Firewall
        # -----------------------------------------------------------------
        # Derive failure code and hardness
        failure_event = next((e for e in reversed(events) if e.event == "payment.failed"), None)
        err_code = failure_event.error_code if failure_event else "UNKNOWN"
        hardness = failure_event.hardness if failure_event else "soft"
        
        ctx = RecoveryContext(
            payment_id=payment.payment_id,
            amount=amount,
            method=payment.method,
            customer_segment=payment.customer_segment or "standard",
            financial_state=fin_state.value,
            recovery_probability=prob,
            expected_net_value=env,
            failure_reason=err_code,
            hardness=hardness,
            retry_count=0,
            previous_attempts=0,
            previous_actions=[],
        )

        act, prio, rsn, conf = determine_policy_action(ctx)
        plan = RecoveryPlan(
            payment_id=payment.payment_id,
            action=act,
            priority=prio,
            reason=rsn,
            confidence=conf,
        )
        firewall_verdict = self.firewall.validate_action(context=ctx, plan=plan)


        if firewall_verdict.status != FirewallDecision.APPROVED:
            # Firewall stopped action
            res.withheld_amount = amount
            if firewall_verdict.rule_id == "FIREWALL-004":
                res.hard_decline_prevented = True
            elif firewall_verdict.rule_id == "FIREWALL-009":
                res.duplicate_prevented = True
            return res

        # -----------------------------------------------------------------
        # 4. ACT: Bounded Action Execution
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

        # Customer conversion based on ground-truth willingness
        customer_actually_pays = (self.rng.random() < lifecycle.true_customer_willingness)
        exec_response = self.executor.execute(
            payment=payment,
            action=action_to_exec,
            force_success=customer_actually_pays,
        )

        # -----------------------------------------------------------------
        # 5. VERIFY: Independent Ledger Verification
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
        final_outcome, recovered, withheld, reason = determine_final_outcome(
            initial_state=fin_state.value,
            firewall_result=firewall_verdict,
            verification=verif_result,
            amount=amount,
            expected_net_value=env,
        )


        if final_outcome == FinalOutcome.RECOVERY_SUCCESS.value:
            res.recovered_amount = recovered
            res.outstanding_amount = max(0.0, amount - recovered)
            res.succeeded = True
        else:
            res.withheld_amount = amount
            res.failed = True

        return res
