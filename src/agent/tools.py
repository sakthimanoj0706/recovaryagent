"""
Controlled Operational Tools for RecoverAI Agentic Recovery Orchestrator.

SAFETY BOUNDARY:
- The LLM can query and request these tools.
- The LLM cannot directly modify tool outputs or underlying financial state.
- All tool outputs are strongly typed, structured JSON dictionaries.
- State evaluations and verifications route directly to deterministic engines.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from state_engine import FinancialStateEngine, PaymentRecord, Event, FinancialState
from recovery.decision import RecoveryDecisionEngine
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from .models import RecoveryContext, RecoveryAction
from .schemas import ToolCallRecord, AgentAction


class RecoveryToolRegistry:
    """
    Registry of controlled operational tools available to the RecoverAI Agent.
    All external queries and state checks are guarded and deterministic.
    """

    def __init__(
        self,
        state_engine: Optional[FinancialStateEngine] = None,
        recovery_engine: Optional[RecoveryDecisionEngine] = None,
        model: Optional[RecoveryProbabilityModel] = None,
    ):
        self.state_engine = state_engine or FinancialStateEngine()
        self.recovery_engine = recovery_engine or (
            RecoveryDecisionEngine(model=model, cost_config=RecoveryCostConfig(), state_engine=self.state_engine)
            if model
            else None
        )
        self.tool_call_history: List[ToolCallRecord] = []

    def _record_call(self, tool_name: str, args: Dict[str, Any], output: Dict[str, Any]) -> ToolCallRecord:
        record = ToolCallRecord(
            tool_name=tool_name,
            input_args=args,
            output_data=output,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.tool_call_history.append(record)
        return record

    def get_financial_state(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 1: get_financial_state(payment_id)
        Query deterministic Financial State Engine to establish financial truth.
        """
        result = self.state_engine.evaluate_payment(payment, events, order_events)
        output = {
            "tool": "get_financial_state",
            "payment_id": payment.payment_id,
            "order_id": payment.order_id,
            "financial_state": result.state.value,
            "rule_id": result.rule_id,
            "reason": result.reason,
            "recommended_action": result.recommended_action.value,
            "is_verified_lost": result.state == FinancialState.VERIFIED_LOST,
        }
        self._record_call("get_financial_state", {"payment_id": payment.payment_id}, output)
        return output

    def get_payment_events(
        self,
        payment: PaymentRecord,
        events: List[Event],
    ) -> Dict[str, Any]:
        """
        Tool 2: get_payment_events(payment_id)
        Retrieve chronological raw webhook event stream for the payment.
        """
        sorted_evs = sorted(events, key=lambda e: e.ts)
        ev_dicts = [e.model_dump() for e in sorted_evs]
        output = {
            "tool": "get_payment_events",
            "payment_id": payment.payment_id,
            "event_count": len(sorted_evs),
            "events": ev_dicts,
            "last_event": ev_dicts[-1]["event"] if ev_dicts else None,
        }
        self._record_call("get_payment_events", {"payment_id": payment.payment_id}, output)
        return output

    def get_order_history(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 3: get_order_history(order_id)
        Retrieve historical customer segment, lifetime order context, and payment attempts.
        """
        all_evs = order_events or events
        unique_pids = set(e.payment_id for e in all_evs if e.payment_id)
        output = {
            "tool": "get_order_history",
            "order_id": payment.order_id,
            "payment_id": payment.payment_id,
            "customer_segment": payment.customer_segment or "standard",
            "total_attempts_on_order": max(1, len(unique_pids)),
            "payment_method": payment.method or "unknown",
            "amount": payment.amount,
        }
        self._record_call("get_order_history", {"order_id": payment.order_id}, output)
        return output

    def get_recovery_economics(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 4: get_recovery_economics(payment_id)
        Retrieve ML recovery probability, cost configuration, and Expected Net Value (ENV).
        """
        state_res = self.state_engine.evaluate_payment(payment, events, order_events)
        
        prob = None
        env = None
        decision = "INELIGIBLE_NON_LOST"

        if state_res.state == FinancialState.VERIFIED_LOST and self.recovery_engine:
            dec_res = self.recovery_engine.evaluate_payment(payment, events, order_events, precomputed_state=state_res.state)
            prob = dec_res.recovery_probability
            env = dec_res.expected_net_value
            decision = dec_res.decision.value

        output = {
            "tool": "get_recovery_economics",
            "payment_id": payment.payment_id,
            "financial_state": state_res.state.value,
            "recovery_probability": prob,
            "expected_net_value": env,
            "economic_decision": decision,
            "is_worthwhile": decision == "RECOVERY_WORTHWHILE",
        }
        self._record_call("get_recovery_economics", {"payment_id": payment.payment_id}, output)
        return output

    def get_previous_actions(
        self,
        payment_id: str,
        memory_actions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 5: get_previous_actions(payment_id)
        Retrieve previous recovery actions attempted on this payment in the current session.
        """
        actions = memory_actions or []
        output = {
            "tool": "get_previous_actions",
            "payment_id": payment_id,
            "previous_actions": list(actions),
            "attempt_count": len(actions),
            "has_retried": "RETRY" in [a.upper() for a in actions],
        }
        self._record_call("get_previous_actions", {"payment_id": payment_id}, output)
        return output

    def propose_action(
        self,
        payment_id: str,
        action: str,
        reason: str = "",
        confidence: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Tool 6: propose_action(action)
        Propose a recovery action from the allowed action space.
        Rejects illegal or unknown actions.
        """
        clean_action = action.upper().strip()
        is_valid = AgentAction.is_valid_action(clean_action)

        output = {
            "tool": "propose_action",
            "payment_id": payment_id,
            "proposed_action": clean_action,
            "is_allowed_action_type": is_valid,
            "reason": reason,
            "confidence": confidence,
            "status": "PROPOSED" if is_valid else "REJECTED_UNKNOWN_ACTION",
        }
        self._record_call("propose_action", {"action": action, "payment_id": payment_id}, output)
        return output

    def request_verification(
        self,
        payment: PaymentRecord,
        post_events: List[Event],
    ) -> Dict[str, Any]:
        """
        Tool 7: request_verification(payment_id)
        Request independent verification of financial ledger state post-action execution.
        """
        state_res = self.state_engine.evaluate_payment(payment, post_events)
        output = {
            "tool": "request_verification",
            "payment_id": payment.payment_id,
            "verified_financial_state": state_res.state.value,
            "rule_id": state_res.rule_id,
            "reason": state_res.reason,
            "is_captured": state_res.state == FinancialState.ALREADY_RECOVERED,
        }
        self._record_call("request_verification", {"payment_id": payment.payment_id}, output)
        return output

    def get_recovery_context(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> RecoveryContext:
        """
        Construct standard RecoveryContext for LLM advisory prompting.
        """
        state_res = self.state_engine.evaluate_payment(payment, events, order_events)
        
        fail_evs = [e for e in events if e.event == "payment.failed"]
        last_fail = fail_evs[-1] if fail_evs else None
        err_code = last_fail.error_code if last_fail else "UNKNOWN"
        hardness = last_fail.hardness if last_fail else "soft"
        amt = float(payment.amount) if payment.amount is not None else 0.0

        prob = None
        env = None
        if self.recovery_engine and state_res.state == FinancialState.VERIFIED_LOST:
            dec_res = self.recovery_engine.evaluate_payment(payment, events, order_events, precomputed_state=state_res.state)
            prob = dec_res.recovery_probability
            env = dec_res.expected_net_value

        previous_attempts = len(set(e.payment_id for e in (order_events or events) if e.payment_id))

        return RecoveryContext(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            amount=amt,
            financial_state=state_res.state.value,
            failure_code=err_code,
            failure_reason=err_code,
            failure_description=f"Failure due to {err_code}",
            hardness=hardness,
            method=payment.method or "upi",
            customer_segment=payment.customer_segment or "standard",
            recovery_probability=prob,
            expected_net_value=env,
            retry_count=max(0, previous_attempts - 1),
            previous_attempts=max(1, previous_attempts),
            allowed_actions=[RecoveryAction.PAYMENT_LINK.value, RecoveryAction.REMINDER.value, RecoveryAction.RETRY.value, RecoveryAction.STOP.value, RecoveryAction.ESCALATE.value],
            previous_actions=[],
        )
