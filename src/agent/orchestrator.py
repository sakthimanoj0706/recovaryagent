"""
RecoverAI Production-Style Agentic Recovery Orchestrator.

SAFETY BOUNDARY:
- Financial Truth: Financial State Engine (AUTHORITY)
- Recovery Intelligence: Logistic Regression + Expected Net Value (PRIORITIZE)
- Agentic Planner: Advisory LLM Layer (PLAN)
- Safety Gates: Deterministic Policy Engine + Recovery Firewall (GUARD)
- Execution: Controlled Simulated Action Executor (ACT)
- Proof of Recovery: Closed-Loop Verification on Financial Ledger (VERIFY)
- Accountability: Immutable Audit Logger

MAX_AGENT_STEPS = 3.
Zero authority for LLMs over financial truth, unit economics, or safety rules.
"""

import uuid
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone

from state_engine import FinancialStateEngine, PaymentRecord, Event, FinancialState
from recovery.decision import RecoveryDecisionEngine
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from audit.logger import AuditLogger
from execution.executor import ActionExecutor
from execution.verifier import RecoveryVerifier, VerificationResult
from execution.outcome import ClosedLoopOutcome, determine_final_outcome, FinalOutcome

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
from .schemas import (
    AgentAction,
    AgentStepStage,
    AgentStepRecord,
    AgentRunResult,
    ToolCallRecord,
    PolicyCheckRecord,
)
from .memory import AgentMemory
from .tools import RecoveryToolRegistry
from .policy import PolicyEngine, get_failure_policy, validate_agent_recommendation_against_policy
from .firewall import RecoveryFirewall
from .planner import AgenticRecoveryPlanner
from .llm import BaseLLMClient
from .trace import AgentDecisionTrace, build_decision_trace




class AgenticRecoveryOrchestrator:
    """
    Production-Style Agentic Recovery Orchestrator.
    Executes a bounded, observable, multi-step recovery loop with strict safety rails.
    """

    MAX_AGENT_STEPS = 3

    def __init__(
        self,
        tools: Optional[RecoveryToolRegistry] = None,
        planner: Optional[AgenticRecoveryPlanner] = None,
        policy_engine: Optional[PolicyEngine] = None,
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
        self.policy_engine = policy_engine or PolicyEngine()
        self.firewall = firewall or RecoveryFirewall(max_retries=3)
        self.executor = executor or ActionExecutor()
        

        self.verifier = verifier or RecoveryVerifier(state_engine=self.state_engine)
        self.audit_logger = audit_logger or AuditLogger()
        from intelligence.service import IntelligentRecoveryService
        self.intelligence_service = IntelligentRecoveryService(model=model, llm_client=llm_client)


        self._action_history: Dict[str, Set[str]] = {}
        self._run_cache: Dict[str, AgentRunResult] = {}

    def run_recovery_agent(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
        force_simulated_success: Optional[bool] = None,
        multi_step_scenario: Optional[bool] = False,
        strategy_mode: str = "INTELLIGENT",
    ) -> AgentRunResult:
        """
        Execute the bounded, observable autonomous agent loop:
        OBSERVE -> REASON -> PLAN -> POLICY CHECK -> FIREWALL -> ACT -> VERIFY -> REPLAN OR STOP
        """
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        pid = payment.payment_id
        amt = float(payment.amount) if payment.amount is not None else 0.0
        fail_evs = [e for e in events if e.event == "payment.failed"]

        init_retries = max(0, len(fail_evs) - 1)
        init_prev_actions = list(self._action_history.get(pid, set()))
        memory = AgentMemory(payment_id=pid, retry_count=init_retries, previous_actions=init_prev_actions)
        steps_taken: List[AgentStepRecord] = []
        all_tool_calls: List[ToolCallRecord] = []
        all_policy_checks: List[PolicyCheckRecord] = []


        # ---------------------------------------------------------------------
        # 1. INITIAL OBSERVATION (State Engine & Recovery Economics)
        # ---------------------------------------------------------------------
        state_info = self.tools.get_financial_state(payment, events, order_events)
        all_tool_calls.extend(self.tools.tool_call_history[-1:])
        financial_state = state_info["financial_state"]

        econ_info = self.tools.get_recovery_economics(payment, events, order_events)
        all_tool_calls.extend(self.tools.tool_call_history[-1:])
        rec_prob = econ_info["recovery_probability"]
        env = econ_info["expected_net_value"]

        # Check state authority policy
        can_proceed, state_verdict, state_reason = self.policy_engine.evaluate_state_policy(financial_state, env)
        all_policy_checks.extend(self.policy_engine.check_history[-1:])

        # Non-lost or non-economic states halt before entering planning iterations
        if not can_proceed:
            final_outcome = (
                "CORRECTLY_WITHHELD"
                if financial_state == "ALREADY_RECOVERED" or (env is not None and env <= 0)
                else "WAIT"
                if financial_state == "UNCERTAIN"
                else "ESCALATED_TO_OPERATIONS"
            )
            withheld = amt if final_outcome == "CORRECTLY_WITHHELD" else 0.0
            pending = amt if final_outcome == "WAIT" else 0.0
            escalated = amt if final_outcome == "ESCALATED_TO_OPERATIONS" else 0.0

            step_rec = AgentStepRecord(
                step_number=1,
                stage="OBSERVE_AND_HALT",
                observation=state_info,
                economic_signal="NEGATIVE_OR_BYPASS" if (env is not None and env <= 0) else "BYPASSED",
                agent_proposal="STOP" if state_verdict == "STOP" else state_verdict,
                agent_reason=state_reason,
                confidence=1.0,
                policy_verdict=state_verdict,
                firewall_verdict="STOP" if state_verdict == "STOP" else "ESCALATE",
                firewall_rule_id="FIREWALL-006" if financial_state == "ALREADY_RECOVERED" else "FIREWALL-002" if (env is not None and env <= 0) else "FIREWALL-007" if financial_state == "UNCERTAIN" else "FIREWALL-000",
                firewall_reason=state_reason,
                execution_status="BLOCKED_BY_FIREWALL",
                verification_state=financial_state,
                next_step="STOP",
                tool_calls=list(self.tools.tool_call_history),
            )
            steps_taken.append(step_rec)

            run_result = AgentRunResult(
                run_id=run_id,
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                financial_state=financial_state,
                recovery_probability=rec_prob,
                expected_net_value=env,
                agent_action="STOP" if state_verdict == "STOP" else state_verdict,
                agent_reason=state_reason,
                confidence=1.0,
                firewall_decision="STOP" if state_verdict == "STOP" else "ESCALATE",
                firewall_rule=step_rec.firewall_rule_id,
                execution_status="BLOCKED_BY_FIREWALL",
                verification_state=financial_state,
                final_result=final_outcome,
                steps_taken=steps_taken,
                steps=[s.model_dump() for s in steps_taken],
                tool_calls=all_tool_calls,
                policy_checks=all_policy_checks,
                amount_recovered=0.0,
                amount_withheld=withheld,
                amount_pending=pending,
                amount_escalated=escalated,
                iterations=1,
                memory_snapshot=memory.to_snapshot(),
            )
            self._run_cache[run_id] = run_result
            return run_result

        # ---------------------------------------------------------------------
        # 2. BOUNDED AUTONOMOUS AGENT RECOVERY LOOP
        # ---------------------------------------------------------------------
        current_events = list(events)
        current_state = financial_state
        last_final_result = "RECOVERY_FAILED"
        last_agent_action = "STOP"
        last_agent_reason = ""
        last_confidence = 1.0
        last_fw_decision = "APPROVED"
        last_fw_rule = None
        last_exec_status = "NOT_EXECUTED"
        last_exec_id = None
        recovered_amt = 0.0
        withheld_amt = 0.0

        for step_idx in range(1, self.MAX_AGENT_STEPS + 1):
            step_tool_calls: List[ToolCallRecord] = []

            # A. OBSERVE
            ctx = self.tools.get_recovery_context(payment, current_events, order_events)
            ctx.previous_actions = memory.previous_actions
            ctx.retry_count = memory.retry_count

            # Filter allowed actions based on memory
            ctx.allowed_actions = [
                a for a in [RecoveryAction.PAYMENT_LINK.value, RecoveryAction.REMINDER.value, RecoveryAction.RETRY.value, RecoveryAction.ESCALATE.value, RecoveryAction.STOP.value]
                if a not in memory.failed_actions
            ]

            
            # B. REASON & C. PLAN (Intelligent Recovery Engine)
            if strategy_mode in ["INTELLIGENT", "DETERMINISTIC"]:
                decision = self.intelligence_service.decide(payment, current_events, memory.retry_count)
                
                # If deterministic mode, override selected action with deterministic best
                if strategy_mode == "DETERMINISTIC":
                    try:
                        action = RecoveryAction(decision.deterministic_best_action.action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = f"DETERMINISTIC MODE: Chose {action.value}."
                    confidence = 1.0
                else:
                    try:
                        action = RecoveryAction(decision.selected_action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = decision.selection_reason
                    confidence = decision.llm_recommendation.confidence if decision.llm_recommendation else 1.0
            else:
                # NAIVE MODE or legacy
                recommendation = self.planner.plan_recovery(ctx)
                if recommendation is None:
                    action = RecoveryAction.ESCALATE
                    reason = "LLM unavailable"
                    confidence = 0.0
                else:
                    action = recommendation.action
                    reason = recommendation.rationale
                    confidence = recommendation.confidence

            last_agent_action = action.value
            last_agent_reason = reason
            last_confidence = confidence


            # Propose action tool record
            prop_tool = self.tools.propose_action(pid, action.value, reason, confidence)
            step_tool_calls.append(self.tools.tool_call_history[-1])

            # D. POLICY CHECK (Deterministic Policy Engine)
            is_valid_space, space_err = self.policy_engine.validate_action_space(action.value)
            all_policy_checks.extend(self.policy_engine.check_history[-1:])

            if not is_valid_space:
                last_fw_decision = "STOP"
                last_fw_rule = "POLICY-000"
                last_final_result = "POLICY_VIOLATION"
                withheld_amt = amt

                step_rec = AgentStepRecord(
                    step_number=step_idx,
                    stage="POLICY_CHECK_FAILED",
                    observation={"financial_state": current_state, "error": space_err},
                    agent_proposal=action.value,
                    agent_reason=reason,
                    confidence=confidence,
                    policy_verdict="REJECTED",
                    firewall_verdict="STOP",
                    firewall_rule_id="POLICY-000",
                    firewall_reason=space_err,
                    execution_status="BLOCKED_BY_POLICY",
                    verification_state=current_state,
                    next_step="STOP",
                    tool_calls=step_tool_calls,
                )
                steps_taken.append(step_rec)
                break

            is_policy_allowed, pol_verdict, pol_reason = self.policy_engine.validate_action_policy(
                context=ctx,
                action=action.value,
                previous_actions=memory.previous_actions,
                retry_count=memory.retry_count,
            )
            all_policy_checks.extend(self.policy_engine.check_history[-1:])

            if not is_policy_allowed:
                last_fw_decision = "STOP"
                last_fw_rule = "FIREWALL-004" if "Hard decline" in pol_reason else "FIREWALL-005" if "Maximum retry" in pol_reason else "FIREWALL-009" if "already been attempted" in pol_reason else "POLICY-VIOLATION"
                last_final_result = (
                    "SAFE_STOP" if "Hard decline" in pol_reason
                    else "MAX_RETRY_PROTECTION" if "Maximum retry" in pol_reason
                    else "DUPLICATE_ACTION_BLOCKED" if "already been attempted" in pol_reason
                    else "SAFE_STOP"
                )
                withheld_amt = amt

                step_rec = AgentStepRecord(
                    step_number=step_idx,
                    stage="POLICY_OR_FIREWALL_BLOCK",
                    observation={"financial_state": current_state, "action": action.value},
                    agent_proposal=action.value,
                    agent_reason=reason,
                    confidence=confidence,
                    policy_verdict=pol_verdict,
                    firewall_verdict="STOP",
                    firewall_rule_id=last_fw_rule,
                    firewall_reason=pol_reason,
                    execution_status="BLOCKED_BY_FIREWALL",
                    verification_state=current_state,
                    next_step="STOP",
                    tool_calls=step_tool_calls,
                )
                steps_taken.append(step_rec)
                memory.record_attempt(step_idx, action.value, "STOP", "BLOCKED_BY_FIREWALL", current_state, last_final_result, pol_reason)
                break

            # E. FIREWALL (Deterministic Safety Gates)
            fw_res = self.firewall.evaluate_plan(
                financial_state=FinancialState(current_state),
                expected_net_value=env,
                recommendation=recommendation,
                context=ctx,
            )

            if fw_res.decision != FirewallDecision.APPROVED:
                last_fw_decision = fw_res.decision.value
                last_fw_rule = fw_res.rule_id
                last_final_result = "SAFE_STOP" if fw_res.decision == FirewallDecision.STOP else "ESCALATED_TO_OPERATIONS"
                withheld_amt = amt if last_final_result == "SAFE_STOP" else 0.0

                step_rec = AgentStepRecord(
                    step_number=step_idx,
                    stage="FIREWALL_BLOCKED",
                    observation={"financial_state": current_state, "action": action.value},
                    agent_proposal=action.value,
                    agent_reason=reason,
                    confidence=confidence,
                    policy_verdict="APPROVED",
                    firewall_verdict=fw_res.decision.value,
                    firewall_rule_id=fw_res.rule_id,
                    firewall_reason=fw_res.reason,
                    execution_status="BLOCKED_BY_FIREWALL",
                    verification_state=current_state,
                    next_step="STOP",
                    tool_calls=step_tool_calls,
                )
                steps_taken.append(step_rec)
                memory.record_attempt(step_idx, action.value, fw_res.decision.value, "BLOCKED_BY_FIREWALL", current_state, last_final_result, fw_res.reason)
                break

            # F. ACT (Controlled Action Execution)
            # In multi_step_scenario: step 1 fails simulated checkout, step 2 succeeds
            step_should_succeed = (
                force_simulated_success
                if force_simulated_success is not None
                else (True if multi_step_scenario and step_idx > 1 else False if multi_step_scenario else True)
            )

            action_enum = RecoveryAction(action.value)
            sim_result = self.executor.execute(
                payment=payment,
                action=action_enum,
                force_success=step_should_succeed,
            )
            last_exec_id = sim_result.execution_id
            last_exec_status = "SIMULATED_SUCCESS" if sim_result.simulated_success else "SIMULATED_FAILURE"


            # G. VERIFY (Independent Ledger Verification)
            new_events = list(current_events) + sim_result.generated_events
            verify_res = self.verifier.verify_post_action(payment, new_events)
            current_state = verify_res.state.value

            ver_tool = self.tools.request_verification(payment, new_events)
            step_tool_calls.append(self.tools.tool_call_history[-1])

            # Evaluate outcome of this attempt
            if current_state == "ALREADY_RECOVERED":
                last_final_result = "RECOVERY_SUCCESS"
                recovered_amt = amt
                withheld_amt = 0.0
                next_step = "STOP_RECOVERED"
            elif current_state == "UNCERTAIN":
                last_final_result = "WAIT"
                next_step = "STOP_UNCERTAIN"
            elif current_state == "EXCEPTION":
                last_final_result = "ESCALATED_TO_OPERATIONS"
                next_step = "STOP_EXCEPTION"
            else:
                last_final_result = "RECOVERY_FAILED"
                next_step = "REPLAN" if (multi_step_scenario and step_idx < self.MAX_AGENT_STEPS) else "STOP_EXHAUSTED"


            step_rec = AgentStepRecord(
                step_number=step_idx,
                stage="ACT_AND_VERIFY",
                observation={"financial_state": current_state, "action": action.value},
                economic_signal="POSITIVE_ENV",
                agent_proposal=action.value,
                agent_reason=reason,
                confidence=confidence,
                policy_verdict="APPROVED",
                firewall_verdict="APPROVED",
                firewall_rule_id=None,
                firewall_reason="All deterministic safety rules passed.",
                execution_id=last_exec_id,
                execution_status=last_exec_status,
                verification_state=current_state,
                verification_source="FINANCIAL STATE ENGINE",
                next_step=next_step,
                tool_calls=step_tool_calls,
            )
            steps_taken.append(step_rec)
            memory.record_attempt(step_idx, action.value, "APPROVED", last_exec_status, current_state, last_final_result, reason)
            all_tool_calls.extend(step_tool_calls)

            # Record in global action history to enforce cross-call idempotency
            if pid not in self._action_history:
                self._action_history[pid] = set()
            self._action_history[pid].add(action.value)

            # Check termination condition
            if current_state == "ALREADY_RECOVERED" or next_step != "REPLAN":
                break

            # Update event stream for replanning
            current_events = new_events

        # Audit Logging
        self.audit_logger.log_execution(
            payment_id=pid,
            order_id=payment.order_id,
            amount=amt,
            initial_financial_state=financial_state,
            recovery_probability=rec_prob,
            expected_net_value=env,
            agent_action=last_agent_action,
            agent_reason=last_agent_reason,
            firewall_decision=last_fw_decision,
            firewall_rule=last_fw_rule,
            execution_id=last_exec_id,
            execution_status=last_exec_status,
            verification_state=current_state,
            final_result=last_final_result,
            retry_count=memory.retry_count,
            amount_recovered=recovered_amt,
            amount_withheld=withheld_amt,
        )

        run_result = AgentRunResult(
            run_id=run_id,
            payment_id=pid,
            order_id=payment.order_id,
            amount=amt,
            financial_state=financial_state,
            recovery_probability=rec_prob,
            expected_net_value=env,
            agent_action=last_agent_action,
            agent_reason=last_agent_reason,
            confidence=last_confidence,
            firewall_decision=last_fw_decision,
            firewall_rule=last_fw_rule,
            execution_status=last_exec_status,
            verification_state=current_state,
            final_result=last_final_result,
            steps_taken=steps_taken,
            steps=[s.model_dump() for s in steps_taken],
            tool_calls=all_tool_calls,
            policy_checks=all_policy_checks,
            audit_reference=f"audit_{pid}_{run_id[:8]}",
            amount_recovered=recovered_amt,
            amount_withheld=withheld_amt,
            amount_pending=amt if last_final_result == "WAIT" else 0.0,
            amount_escalated=amt if last_final_result == "ESCALATED_TO_OPERATIONS" else 0.0,
            iterations=len(steps_taken),
            memory_snapshot=memory.to_snapshot(),
        )

        self._run_cache[run_id] = run_result
        return run_result

    def get_run(self, run_id: str) -> Optional[AgentRunResult]:
        """Retrieve cached AgentRunResult by run_id."""
        return self._run_cache.get(run_id)

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
        Backward-compatible orchestrator execution returning ClosedLoopOutcome.
        Preserves 100% exact outcome behavior for existing validation suites.
        """
        amt = float(payment.amount) if payment.amount is not None else 0.0
        pid = payment.payment_id

        # ---------------------------------------------------------------------
        # STEP 1: PROVE (Financial State Engine)
        # ---------------------------------------------------------------------
        state_eval = self.state_engine.evaluate_payment(payment, events, order_events)
        initial_state = state_eval.state.value

        fail_evs = [e for e in events if e.event == "payment.failed"]
        prev_attempts = max(1, len(set(e.payment_id for e in (order_events or events) if e.payment_id)))
        retry_count = len(fail_evs) if len(fail_evs) <= 3 else 3

        context = self.tools.get_recovery_context(payment, events, order_events)

        context.retry_count = retry_count
        context.previous_actions = list(self._action_history.get(pid, set()))

        # Non-lost states: Safety gate halts immediately (LLM is NEVER called)
        if initial_state != "VERIFIED_LOST":
            if initial_state == "ALREADY_RECOVERED":
                fw_decision = FirewallDecision.STOP.value
                fw_rule = "FIREWALL-006"
                fw_reason = f"Payment state is '{initial_state}'. Recovery prohibited: money is already captured."
                final_out_str = "NO_ACTION"
                withheld = amt

                pending = 0.0
                escalated = 0.0
            elif initial_state == "UNCERTAIN":
                fw_decision = FirewallDecision.STOP.value
                fw_rule = "FIREWALL-007"
                fw_reason = f"Payment state is '{initial_state}'. Waiting for asynchronous banking resolution."
                final_out_str = "WAIT"
                withheld = 0.0
                pending = amt
                escalated = 0.0
            else:  # EXCEPTION
                fw_decision = FirewallDecision.ESCALATE.value
                fw_rule = "FIREWALL-008"
                fw_reason = f"Payment state is '{initial_state}'. Escalated for manual operations reconciliation."

                final_out_str = "ESCALATED_TO_OPERATIONS"
                withheld = 0.0
                pending = 0.0
                escalated = amt

            outcome = ClosedLoopOutcome(
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                initial_state=initial_state,
                agent_action="STOP" if initial_state == "ALREADY_RECOVERED" else "WAIT" if initial_state == "UNCERTAIN" else "ESCALATE",
                agent_reason=fw_reason,
                confidence=1.0,
                firewall_decision=fw_decision,
                firewall_rule=fw_rule,
                firewall_reason=fw_reason,
                execution_status="BLOCKED_BY_FIREWALL",
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_out_str,
                amount_recovered=0.0,
                amount_withheld=withheld,
                amount_pending=pending,
                amount_escalated=escalated,
                reason=fw_reason,
                retry_count=retry_count,
            )
            outcome.decision_trace = build_decision_trace(outcome, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason).to_dict()
            self._log_audit(outcome)
            return outcome


        # ---------------------------------------------------------------------
        # STEP 2: PRIORITIZE (Recovery Intelligence & Unit Economics)
        # ---------------------------------------------------------------------
        prob = context.recovery_probability
        env = context.expected_net_value

        if env is not None and env <= 0:
            fw_decision = FirewallDecision.STOP.value
            fw_rule = "FIREWALL-002"
            fw_reason = f"Recovery is economically irrational (Expected Net Value: Rs. {env:.2f} <= 0)."
            final_out = FinalOutcome.CORRECTLY_WITHHELD

            outcome = ClosedLoopOutcome(
                payment_id=pid,
                order_id=payment.order_id,
                amount=amt,
                initial_state=initial_state,
                recovery_probability=prob,
                expected_net_value=env,
                agent_action="STOP",
                agent_reason=fw_reason,
                confidence=1.0,
                firewall_decision=fw_decision,
                firewall_rule=fw_rule,
                firewall_reason=fw_reason,
                execution_status="BLOCKED_BY_FIREWALL",
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_out.value,
                amount_recovered=0.0,
                amount_withheld=amt,
                amount_pending=0.0,
                amount_escalated=0.0,
                reason=fw_reason,
                retry_count=retry_count,
            )
            outcome.decision_trace = build_decision_trace(outcome, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason).to_dict()
            self._log_audit(outcome)
            return outcome

        # ---------------------------------------------------------------------
        # STEP 3: PLAN (Agentic Recovery Planner — Advisory Only)
        # ---------------------------------------------------------------------
        is_llm_valid = True
        if override_action is not None:
            recommendation = AgentRecommendation(
                payment_id=pid,
                action=override_action,
                priority=RecoveryPriority.HIGH,
                channel="gateway",
                timing="immediate",
                message_strategy="override",
                rationale="Direct action override.",
                confidence=1.0,
                policy_references=["MANUAL_OVERRIDE"],
                observed_failure=context.failure_code or "UNKNOWN",
                selected_strategy=override_action.value,
                policy_basis="Direct injection test override",
                risk_level="HIGH",
                expected_net_value=env,
            )

        else:
            raw_rec = self.planner.plan_recovery(context)
            if raw_rec is None:
                is_llm_valid = False
                recommendation = AgentRecommendation(
                    payment_id=pid,
                    action=RecoveryAction.ESCALATE,
                    priority=RecoveryPriority.HIGH,
                    channel="email",
                    timing="immediate",
                    message_strategy="escalate_support",
                    rationale="LLM planner service unavailable / failed or returned malformed output. Escalated safely to operations.",

                    confidence=0.0,
                    policy_references=["FIREWALL-010"],
                    observed_failure=context.failure_code or "UNKNOWN",
                    selected_strategy=RecoveryAction.ESCALATE.value,
                    policy_basis="Safe fallback on LLM failure",
                    risk_level="HIGH",
                    expected_net_value=env,
                )
            else:
                recommendation = raw_rec

        # ---------------------------------------------------------------------
        # STEP 4: GUARD (Deterministic Recovery Firewall)
        # ---------------------------------------------------------------------
        fw_result = self.firewall.validate_action(
            context=context,
            plan=recommendation if is_llm_valid else None,
            proposed_action=recommendation.action,
            llm_valid=is_llm_valid,
        )


        # Check for duplicate action (Idempotency)
        if pid in self._action_history and recommendation.action.value in self._action_history[pid]:
            fw_result = FirewallResult(
                status=FirewallDecision.STOP,
                action=RecoveryAction.STOP,
                rule_id="FIREWALL-009",
                reason=f"Action '{recommendation.action.value}' has already been executed on payment {pid}. Duplicate blocked.",
            )

        if fw_result.decision != FirewallDecision.APPROVED:
            is_hard_block = fw_result.rule_id == "FIREWALL-004"
            is_max_retry = fw_result.rule_id == "FIREWALL-005"
            is_duplicate = fw_result.rule_id == "FIREWALL-009"

            if is_hard_block:
                final_out = FinalOutcome.SAFE_STOP
            elif is_max_retry:
                final_out = FinalOutcome.MAX_RETRY_PROTECTION
            elif is_duplicate:
                final_out = FinalOutcome.DUPLICATE_ACTION_BLOCKED
            elif fw_result.decision == FirewallDecision.STOP:
                final_out = FinalOutcome.CORRECTLY_WITHHELD
            else:
                final_out = FinalOutcome.ESCALATED_TO_OPERATIONS

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
                firewall_decision=fw_result.decision.value,
                firewall_rule=fw_result.rule_id,
                firewall_reason=fw_result.reason,
                execution_status="BLOCKED_BY_FIREWALL",
                verification_state=initial_state,
                source_of_truth="FINANCIAL STATE ENGINE",
                final_outcome=final_out.value,
                amount_recovered=0.0,
                amount_withheld=amt if final_out != FinalOutcome.ESCALATED_TO_OPERATIONS else 0.0,
                amount_pending=0.0,
                amount_escalated=amt if final_out == FinalOutcome.ESCALATED_TO_OPERATIONS else 0.0,
                reason=fw_result.reason,
                retry_count=retry_count,
            )
            outcome.decision_trace = build_decision_trace(outcome, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason).to_dict()
            self._log_audit(outcome)
            return outcome

        # ---------------------------------------------------------------------
        # STEP 5: ACT (Controlled Action Executor)
        # ---------------------------------------------------------------------
        sim_result = self.executor.execute(
            payment=payment,
            action=recommendation.action,
            force_success=force_simulated_success,
        )

        if pid not in self._action_history:
            self._action_history[pid] = set()
        self._action_history[pid].add(recommendation.action.value)

        # ---------------------------------------------------------------------
        # STEP 6: VERIFY (Independent Financial State Verification)
        # ---------------------------------------------------------------------
        all_post_events = list(events) + sim_result.generated_events
        if post_action_events:
            all_post_events.extend(post_action_events)

        ver_result = self.verifier.verify_post_action(
            payment=payment,
            post_action_events=all_post_events,
            order_events=order_events,
        )

        ver_state_str = ver_result.state.value if hasattr(ver_result.state, "value") else str(ver_result.state)
        if ver_state_str == "ALREADY_RECOVERED":
            final_out_str = "RECOVERY_SUCCESS"
            recovered_amt = amt
            withheld_amt = 0.0
            pending_amt = 0.0
            escalated_amt = 0.0
        elif ver_state_str == "UNCERTAIN":
            final_out_str = "RECOVERY_WAITING_ASYNC"
            recovered_amt = 0.0
            withheld_amt = 0.0
            pending_amt = amt
            escalated_amt = 0.0

        elif ver_state_str == "EXCEPTION":
            final_out_str = "ESCALATED_TO_OPERATIONS"
            recovered_amt = 0.0
            withheld_amt = 0.0
            pending_amt = 0.0
            escalated_amt = amt
        else:  # VERIFIED_LOST
            final_out_str = "RECOVERY_FAILED"
            recovered_amt = 0.0
            withheld_amt = 0.0
            pending_amt = 0.0
            escalated_amt = 0.0

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
            firewall_decision=fw_result.decision.value,
            firewall_rule=fw_result.rule_id,
            firewall_reason=fw_result.reason,
            execution_id=sim_result.execution_id,
            execution_status="SIMULATED_SUCCESS" if sim_result.simulated_success else "SIMULATED_FAILURE",
            execution_message=sim_result.message,
            verification_state=ver_state_str,
            source_of_truth="FINANCIAL STATE ENGINE",
            final_outcome=final_out_str,
            amount_recovered=recovered_amt,
            amount_withheld=withheld_amt,
            amount_pending=pending_amt,
            amount_escalated=escalated_amt,
            reason=getattr(ver_result, "reason", "Verified by Financial State Engine"),
            simulation_flag=True,
            retry_count=retry_count,
        )

        outcome.decision_trace = build_decision_trace(outcome, state_rule_id=state_eval.rule_id, state_reason=state_eval.reason).to_dict()

        self._log_audit(outcome)
        return outcome

    def get_decision_trace(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> AgentDecisionTrace:
        """
        Evaluate and return the strongly-typed 6-stage AgentDecisionTrace for a payment.
        """
        outcome = self.process_payment(payment, events, order_events)
        return build_decision_trace(outcome)

    def run_lifecycle(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
        override_action: Optional[RecoveryAction] = None,
        force_simulated_success: Optional[bool] = None,
        post_action_events: Optional[List[Event]] = None,
    ) -> AgentExecutionResult:
        """Execute lifecycle returning strongly-typed AgentExecutionResult for backwards compatibility."""
        outcome = self.process_payment(
            payment=payment,
            events=events,
            order_events=order_events,
            override_action=override_action,
            force_simulated_success=force_simulated_success,
            post_action_events=post_action_events,
        )

        act_val = str(outcome.agent_action).upper() if outcome.agent_action else "STOP"
        try:
            act_enum = RecoveryAction(act_val)
        except ValueError:
            act_enum = RecoveryAction.STOP

        fw_val = str(outcome.firewall_decision).upper() if outcome.firewall_decision else "STOP"
        try:
            fw_enum = FirewallDecision(fw_val)
        except ValueError:
            fw_enum = FirewallDecision.STOP

        exec_status = outcome.execution_status
        if outcome.firewall_decision == "ESCALATE":
            exec_status = "SIMULATED_ESCALATED"

        return AgentExecutionResult(
            payment_id=outcome.payment_id,
            order_id=outcome.order_id,
            financial_state=outcome.initial_state,
            failure_reason="N/A",
            amount=outcome.amount,
            recovery_probability=outcome.recovery_probability,
            expected_net_value=outcome.expected_net_value,
            agent_action=act_enum,
            agent_reason=outcome.agent_reason or "",
            confidence=outcome.confidence,
            firewall_decision=fw_enum,
            firewall_rule=outcome.firewall_rule,
            firewall_reason=outcome.firewall_reason or "",
            execution_status=exec_status,
            execution_detail={"status": "SIMULATED", "action": outcome.agent_action} if exec_status == "SIMULATED_SUCCESS" else None,
            verification_state=outcome.verification_state,
            final_result=outcome.final_outcome,
        )


    def _log_audit(self, outcome: ClosedLoopOutcome) -> None:
        """Helper to record closed-loop execution in audit logger."""
        self.audit_logger.log_execution(
            payment_id=outcome.payment_id,
            order_id=outcome.order_id,
            amount=outcome.amount,
            initial_financial_state=outcome.initial_state,
            recovery_probability=outcome.recovery_probability,
            expected_net_value=outcome.expected_net_value,
            agent_action=outcome.agent_action,
            agent_reason=outcome.agent_reason,
            firewall_decision=outcome.firewall_decision,
            firewall_rule=outcome.firewall_rule,
            execution_id=outcome.execution_id,
            execution_status=outcome.execution_status,
            verification_state=outcome.verification_state,
            final_result=outcome.final_outcome,
            retry_count=outcome.retry_count,
            amount_recovered=outcome.amount_recovered,
            amount_withheld=outcome.amount_withheld,
        )




# Backward-compatible aliases and functional entry points
RecoverAIOrchestrator = AgenticRecoveryOrchestrator
RecoveryOrchestrator = AgenticRecoveryOrchestrator


def run_recovery_agent(
    payment: PaymentRecord,
    events: List[Event],
    order_events: Optional[List[Event]] = None,
    post_action_events: Optional[List[Event]] = None,
    orchestrator: Optional[AgenticRecoveryOrchestrator] = None,
    **kwargs
) -> ClosedLoopOutcome:
    """Convenience functional wrapper to process a payment through the orchestrator."""
    orch = orchestrator or AgenticRecoveryOrchestrator()
    return orch.process_payment(
        payment=payment,
        events=events,
        order_events=order_events,
        post_action_events=post_action_events,
        **kwargs
    )

