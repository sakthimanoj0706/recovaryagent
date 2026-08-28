"""
RecoverAI Agentic Recovery Orchestrator.

Implements the bounded 6-stage architecture:
PROVE -> PRIORITIZE -> PLAN -> GUARD -> ACT -> VERIFY

The LLM operates strictly as an ADVISOR with ZERO authority over financial truth,
unit economics, deterministic safety gates, or verification.
"""

from typing import Dict, Any, List, Optional, Set
from state_engine import FinancialStateEngine, PaymentRecord, Event
from recovery.decision import RecoveryDecisionEngine
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from .models import (
    RecoveryAction,
    RecoveryPriority,
    FirewallDecision,
    AgentResultType,
    RecoveryContext,
    AgentRecommendation,
    RecoveryPlan,
    FirewallResult,
    AgentExecutionResult,
)
from .tools import RecoveryToolRegistry
from .planner import AgenticRecoveryPlanner, AgentPlanner
from .policy import validate_agent_recommendation_against_policy
from .firewall import RecoveryFirewall
from .llm import BaseLLMClient
from audit.logger import AuditLogger
from execution.executor import ActionExecutor
from execution.verifier import RecoveryVerifier, VerificationResult
from execution.outcome import ClosedLoopOutcome, determine_final_outcome, FinalOutcome
from .trace import AgentDecisionTrace, build_decision_trace



class RecoverAIOrchestrator:
    """
    Core Agentic Recovery Orchestrator for RecoverAI.
    Coordinates Financial State Engine, Recovery Intelligence, Agentic Planner,
    Recovery Firewall, Action Executor, and State Verifier.
    """

    def __init__(
        self,
        tools: Optional[RecoveryToolRegistry] = None,
        planner: Optional[AgenticRecoveryPlanner] = None,
        firewall: Optional[RecoveryFirewall] = None,
        executor: Optional[ActionExecutor] = None,
        verifier: Optional[RecoveryVerifier] = None,
        audit_logger: Optional[AuditLogger] = None,
        llm_client: Optional[BaseLLMClient] = None,
        model: Optional[RecoveryProbabilityModel] = None,
        state_engine: Optional[FinancialStateEngine] = None,
    ):
        self.state_engine = state_engine or FinancialStateEngine()
        self.tools = tools or RecoveryToolRegistry(state_engine=self.state_engine, model=model)
        self.planner = planner or AgenticRecoveryPlanner(llm_client=llm_client)
        self.firewall = firewall or RecoveryFirewall(max_retries=3)
        self.executor = executor or ActionExecutor()
        self.verifier = verifier or RecoveryVerifier(state_engine=self.state_engine)
        self.audit_logger = audit_logger or AuditLogger()
        self._action_history: Dict[str, Set[str]] = {}

    def process_payment(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
        post_action_events: Optional[List[Event]] = None,
        override_action: Optional[RecoveryAction] = None,
        force_simulated_success: Optional[bool] = None,
    ) -> ClosedLoopOutcome:
        """
        Execute the bounded 6-stage closed loop for a payment record.
        """
        amt = float(payment.amount) if payment.amount is not None else 0.0
        pid = payment.payment_id

        # ---------------------------------------------------------------------
        # STEP 1: PROVE (Financial State Engine)
        # ---------------------------------------------------------------------
        state_eval = self.state_engine.evaluate_payment(payment, events, order_events)
        initial_state = state_eval.state.value

        # Calculate retry history
        fail_evs = [e for e in events if e.event == "payment.failed"]
        prev_attempts = max(1, len(set(e.payment_id for e in (order_events or events) if e.payment_id)))
        retry_count = len(fail_evs) - 1 if len(fail_evs) > 1 else 0

        # Construct Recovery Context
        context = self.tools.get_recovery_context(payment, events, order_events)
        context.retry_count = retry_count
        context.previous_actions = list(self._action_history.get(pid, set()))

        # Non-lost states: Safety gate halts immediately (LLM is NEVER called)
        if initial_state != "VERIFIED_LOST":
            action = RecoveryAction.STOP if initial_state == "ALREADY_RECOVERED" else (
                RecoveryAction.WAIT if initial_state == "UNCERTAIN" else RecoveryAction.ESCALATE
            )
            recommendation = AgentRecommendation(
                payment_id=pid,
                action=action,
                priority=RecoveryPriority.LOW,
                rationale=f"Payment financial state is '{initial_state}'. Recovery planning not permitted.",
                confidence=1.0,
                expected_net_value=0.0,
            )
            fw_res = self.firewall.validate_action(context, plan=recommendation, proposed_action=action)
            
            final_res, rec_amt, with_amt, expl = determine_final_outcome(
                initial_state=initial_state,
                firewall_result=fw_res,
                verification=None,
                amount=amt,
                expected_net_value=0.0,
            )

            pend_amt = amt if final_res == "WAIT" else 0.0
            esc_amt = amt if final_res == "ESCALATED_TO_OPERATIONS" else 0.0
            agent_mode = getattr(getattr(self.planner, "llm_client", None), "mode", "demo")

            outcome = ClosedLoopOutcome(
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                initial_state=initial_state,
                recovery_probability=None,
                expected_net_value=None,
                agent_action=action.value,
                agent_reason=recommendation.rationale,
                confidence=1.0,
                firewall_decision=fw_res.status.value,
                firewall_rule=fw_res.rule_id,
                firewall_reason=fw_res.reason,
                execution_id=None,
                execution_status="BLOCKED_BY_FIREWALL",
                execution_message="Action blocked by initial state safety gate.",
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_res,
                amount_recovered=rec_amt,
                amount_withheld=with_amt,
                amount_pending=pend_amt,
                amount_escalated=esc_amt,
                reason=expl,
                simulation_flag=True,
                retry_count=retry_count,
            )
            trace = build_decision_trace(outcome, agent_mode=agent_mode, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason)
            outcome.decision_trace = trace.model_dump()
            self.audit_logger.log(outcome)
            return outcome

        # ---------------------------------------------------------------------
        # STEP 2: PRIORITIZE (Recovery Intelligence & Unit Economics)
        # ---------------------------------------------------------------------
        env = context.expected_net_value if context.expected_net_value is not None else -1.0
        prob = context.recovery_probability

        if env <= 0.0:
            recommendation = AgentRecommendation(
                payment_id=pid,
                action=RecoveryAction.STOP,
                priority=RecoveryPriority.LOW,
                rationale=f"Recovery is economically irrational (Expected Net Value: Rs. {env:,.2f} <= 0).",
                confidence=0.95,
                expected_net_value=env,
            )
            fw_res = self.firewall.validate_action(context, plan=recommendation, proposed_action=RecoveryAction.STOP)
            
            final_res, rec_amt, with_amt, expl = determine_final_outcome(
                initial_state=initial_state,
                firewall_result=fw_res,
                verification=None,
                amount=amt,
                expected_net_value=env,
            )

            pend_amt = amt if final_res == "WAIT" else 0.0
            esc_amt = amt if final_res == "ESCALATED_TO_OPERATIONS" else 0.0
            agent_mode = getattr(getattr(self.planner, "llm_client", None), "mode", "demo")

            outcome = ClosedLoopOutcome(
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                initial_state=initial_state,
                recovery_probability=prob,
                expected_net_value=env,
                agent_action=RecoveryAction.STOP.value,
                agent_reason=recommendation.rationale,
                confidence=0.95,
                firewall_decision=fw_res.status.value,
                firewall_rule=fw_res.rule_id,
                firewall_reason=fw_res.reason,
                execution_id=None,
                execution_status="BLOCKED_BY_FIREWALL",
                execution_message="Recovery skipped due to negative expected net value.",
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_res,
                amount_recovered=rec_amt,
                amount_withheld=with_amt,
                amount_pending=pend_amt,
                amount_escalated=esc_amt,
                reason=expl,
                simulation_flag=True,
                retry_count=retry_count,
            )
            trace = build_decision_trace(outcome, agent_mode=agent_mode, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason)
            outcome.decision_trace = trace.model_dump()
            self.audit_logger.log(outcome)
            return outcome

        # ---------------------------------------------------------------------
        # STEP 3: PLAN (Agentic Recovery Planner)
        # ---------------------------------------------------------------------
        llm_valid = True
        recommendation = self.planner.plan_recovery(context)

        if recommendation is None:
            llm_valid = False
            recommendation = AgentRecommendation(
                payment_id=pid,
                action=RecoveryAction.ESCALATE,
                priority=RecoveryPriority.CRITICAL,
                rationale="LLM planner service unavailable. Safe fallback to operations queue.",
                confidence=0.0,
                expected_net_value=env,
            )

        if override_action is not None:
            recommendation.action = override_action

        # Validate recommendation against deterministic policy registry
        is_policy_valid, viol_code, viol_reason = validate_agent_recommendation_against_policy(
            context=context,
            recommendation=recommendation,
        )

        # Check Idempotency
        prior_actions = self._action_history.get(pid, set())
        is_duplicate = recommendation.action.value in prior_actions

        # ---------------------------------------------------------------------
        # STEP 4: GUARD (Deterministic Recovery Firewall)
        # ---------------------------------------------------------------------
        fw_res = self.firewall.validate_action(
            context,
            plan=recommendation,
            proposed_action=recommendation.action,
            llm_valid=llm_valid,
        )

        # If policy registry or firewall rejected, halt execution
        if not is_policy_valid and fw_res.status == FirewallDecision.APPROVED:
            fw_res = FirewallResult(
                status=FirewallDecision.STOP,
                action=recommendation.action,
                rule_id=viol_code or "POLICY_VIOLATION",
                reason=viol_reason or "Recommendation violated failure policy.",
            )

        if fw_res.status != FirewallDecision.APPROVED:
            final_res, rec_amt, with_amt, expl = determine_final_outcome(
                initial_state=initial_state,
                firewall_result=fw_res,
                verification=None,
                amount=amt,
                expected_net_value=env,
                duplicate_blocked=is_duplicate,
                max_retry_blocked=(retry_count >= 3 and recommendation.action == RecoveryAction.RETRY),
            )

            exec_st = "SIMULATED_ESCALATED" if fw_res.status == FirewallDecision.ESCALATE else "BLOCKED_BY_FIREWALL"
            pend_amt = amt if final_res == "WAIT" else 0.0
            esc_amt = amt if final_res == "ESCALATED_TO_OPERATIONS" else 0.0
            agent_mode = getattr(getattr(self.planner, "llm_client", None), "mode", "demo")

            outcome = ClosedLoopOutcome(
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                initial_state=initial_state,
                recovery_probability=prob,
                expected_net_value=env,
                agent_action=recommendation.action.value,
                agent_reason=recommendation.rationale,
                confidence=recommendation.confidence,
                firewall_decision=fw_res.status.value,
                firewall_rule=fw_res.rule_id,
                firewall_reason=fw_res.reason,
                execution_id=None,
                execution_status=exec_st,
                execution_message=fw_res.reason,
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_res,
                amount_recovered=rec_amt,
                amount_withheld=with_amt,
                amount_pending=pend_amt,
                amount_escalated=esc_amt,
                reason=expl,
                simulation_flag=True,
                retry_count=retry_count,
            )
            trace = build_decision_trace(outcome, agent_mode=agent_mode, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason)
            outcome.decision_trace = trace.model_dump()
            self.audit_logger.log(outcome)
            return outcome

        # Record action in idempotency history
        if pid not in self._action_history:
            self._action_history[pid] = set()
        self._action_history[pid].add(recommendation.action.value)

        # ---------------------------------------------------------------------
        # STEP 5: ACT (Simulated Action Executor)
        # ---------------------------------------------------------------------
        exec_res = self.executor.execute(
            plan=recommendation,
            context=context,
            force_success=force_simulated_success,
        )

        if post_action_events:
            exec_res.generated_events = list(post_action_events)
            exec_res.simulated_success = any(e.event in ["payment.authorized", "payment.captured"] for e in post_action_events)

        # ---------------------------------------------------------------------
        # STEP 6: VERIFY (Financial State Engine - "NEVER TRUST THE AGENT")
        # ---------------------------------------------------------------------
        verification = self.verifier.verify(
            payment=payment,
            original_events=events,
            execution_response=exec_res,
            order_events=order_events,
        )

        # Final Outcome Determination & Audit Logging
        final_res, rec_amt, with_amt, expl = determine_final_outcome(
            initial_state=initial_state,
            firewall_result=fw_res,
            verification=verification,
            amount=amt,
            expected_net_value=env,
        )

        pend_amt = amt if final_res == "WAIT" else 0.0
        esc_amt = amt if final_res == "ESCALATED_TO_OPERATIONS" else 0.0
        agent_mode = getattr(getattr(self.planner, "llm_client", None), "mode", "demo")

        outcome = ClosedLoopOutcome(
            payment_id=pid,
            order_id=payment.order_id,
            amount=amt,
            initial_state=initial_state,
            recovery_probability=prob,
            expected_net_value=env,
            agent_action=recommendation.action.value,
            agent_reason=recommendation.rationale,
            confidence=recommendation.confidence,
            firewall_decision=fw_res.status.value,
            firewall_rule=fw_res.rule_id,
            firewall_reason=fw_res.reason,
            execution_id=exec_res.execution_id,
            execution_status="SIMULATED_SUCCESS" if exec_res.simulated_success else "SIMULATED_FAILURE",
            execution_message=exec_res.message,
            verification_state=verification.verified_financial_state,
            source_of_truth="FINANCIAL STATE ENGINE",
            final_outcome=final_res,
            amount_recovered=rec_amt,
            amount_withheld=with_amt,
            amount_pending=pend_amt,
            amount_escalated=esc_amt,
            reason=expl,
            simulation_flag=True,
            retry_count=retry_count + (1 if recommendation.action == RecoveryAction.RETRY else 0),
        )
        trace = build_decision_trace(outcome, agent_mode=agent_mode, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason)
        outcome.decision_trace = trace.model_dump()

        self.audit_logger.log(outcome)
        return outcome

    def get_decision_trace(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> AgentDecisionTrace:
        """
        Evaluate a payment and generate its structured AgentDecisionTrace.
        """
        outcome = self.process_payment(payment, events, order_events)
        agent_mode = getattr(getattr(self.planner, "llm_client", None), "mode", "demo")
        state_eval = self.state_engine.evaluate_payment(payment, events, order_events)
        return build_decision_trace(
            outcome,
            agent_mode=agent_mode,
            state_rule_id=state_eval.rule_id,
            state_reason=state_eval.reason,
        )


    def run_lifecycle(self, payment: PaymentRecord, events: List[Event], **kwargs) -> AgentExecutionResult:
        """
        Legacy adapter method returning AgentExecutionResult.
        """
        outcome = self.process_payment(payment, events, **kwargs)
        
        exec_detail = {
            "status": "SIMULATED",
            "execution_id": outcome.execution_id,
            "message": outcome.execution_message,
        }

        final_str = outcome.final_outcome
        if outcome.verification_state == "VERIFIED_LOST" and outcome.execution_status == "SIMULATED_SUCCESS":
            final_str = "ACTION_DISPATCHED_AWAITING_PAYMENT"

        return AgentExecutionResult(
            payment_id=outcome.payment_id,
            order_id=outcome.order_id,
            financial_state=outcome.initial_state,
            failure_reason=events[-1].error_code if events else None,
            amount=outcome.amount,
            recovery_probability=outcome.recovery_probability,
            expected_net_value=outcome.expected_net_value,
            agent_action=RecoveryAction(outcome.agent_action) if outcome.agent_action else RecoveryAction.STOP,
            agent_reason=outcome.agent_reason or "",
            confidence=outcome.confidence,
            firewall_decision=FirewallDecision(outcome.firewall_decision),
            firewall_rule=outcome.firewall_rule,
            firewall_reason=outcome.firewall_reason or "",
            execution_status=outcome.execution_status,
            execution_detail=exec_detail,
            verification_state=outcome.verification_state,
            final_result=final_str,
        )


# Global standalone helper function
def run_recovery_agent(
    payment: PaymentRecord,
    events: List[Event],
    orchestrator: Optional[RecoverAIOrchestrator] = None,
    **kwargs,
) -> ClosedLoopOutcome:
    """
    Standalone function to run the agentic recovery workflow for a payment.
    """
    orch = orchestrator or RecoverAIOrchestrator()
    return orch.process_payment(payment, events, **kwargs)


# Backward compatibility aliases
RecoveryOrchestrator = RecoverAIOrchestrator
