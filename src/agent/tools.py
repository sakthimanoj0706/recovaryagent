"""
Simulated operational tools for RecoverAI Agentic Recovery Planner.
All external execution is strictly simulated with transparent metadata.
"""

from typing import Dict, Any, List, Optional
from state_engine import FinancialStateEngine, PaymentRecord, Event
from recovery.decision import RecoveryDecisionEngine
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from .models import RecoveryContext


class RecoveryToolRegistry:
    """
    Registry of simulated operational tools available to the RecoverAI Agent.
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

    def get_payment_state(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 1: Retrieve proven financial state from Financial State Engine.
        """
        result = self.state_engine.evaluate_payment(payment, events, order_events)
        return {
            "tool": "get_payment_state",
            "payment_id": payment.payment_id,
            "order_id": payment.order_id,
            "financial_state": result.state.value,
            "recommended_action": result.recommended_action.value,
            "reason": result.reason,
            "rule_id": result.rule_id,
        }

    def get_customer_history(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 2: Retrieve customer segment and historical order context.
        """
        total_order_events = len(order_events) if order_events else len(events)
        previous_attempts = len(set(e.payment_id for e in (order_events or events) if e.payment_id))
        return {
            "tool": "get_customer_history",
            "payment_id": payment.payment_id,
            "order_id": payment.order_id,
            "customer_segment": payment.customer_segment or "unknown",
            "previous_attempts": max(1, previous_attempts),
            "retry_count": max(0, previous_attempts - 1),
            "total_lifecycle_events": total_order_events,
            "method": payment.method or "unknown",
        }

    def get_recovery_context(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> RecoveryContext:
        """
        Tool 3: Extract comprehensive recovery context including ML probability and Expected Net Value.
        """
        state_res = self.state_engine.evaluate_payment(payment, events, order_events)
        
        # Extract last failure event
        fail_evs = [e for e in events if e.event == "payment.failed"]
        last_fail = fail_evs[-1] if fail_evs else None
        err_code = last_fail.error_code if last_fail else "UNKNOWN"
        hardness = last_fail.hardness if last_fail else "soft"
        amt = float(payment.amount) if payment.amount is not None else 0.0

        prob = None
        env = None
        if self.recovery_engine and state_res.state.value == "VERIFIED_LOST":
            dec_res = self.recovery_engine.evaluate_payment(payment, events, order_events, precomputed_state=state_res.state)
            prob = dec_res.recovery_probability
            env = dec_res.expected_net_value

        previous_attempts = len(set(e.payment_id for e in (order_events or events) if e.payment_id))

        return RecoveryContext(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            financial_state=state_res.state.value,
            failure_reason=err_code,
            hardness=hardness,
            amount=amt,
            method=payment.method,
            customer_segment=payment.customer_segment,
            recovery_probability=prob,
            expected_net_value=env,
            previous_attempts=max(1, previous_attempts),
            retry_count=max(0, previous_attempts - 1),
            previous_actions=[],
        )

    def propose_retry(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Tool 4: Simulated gateway retry dispatch.
        """
        return {
            "tool": "propose_retry",
            "status": "SIMULATED",
            "payment_id": payment_id,
            "action": "RETRY",
            "amount": amount,
            "result": "retry_dispatched",
            "message": f"Simulated automated payment gateway retry submitted for payment {payment_id}.",
        }

    def generate_payment_link(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Tool 5: Simulated customer recovery payment link generator.
        """
        short_id = payment_id.replace("pay_", "")[:8]
        return {
            "tool": "generate_payment_link",
            "status": "SIMULATED",
            "payment_id": payment_id,
            "action": "PAYMENT_LINK",
            "amount": amount,
            "result": "payment_link_generated",
            "link": f"https://pay.recoverai.io/link/{short_id}",
            "message": f"Simulated dynamic recovery link generated for payment {payment_id}.",
        }

    def generate_reminder(self, payment_id: str, channel: str = "sms") -> Dict[str, Any]:
        """
        Tool 6: Simulated customer notification reminder.
        """
        return {
            "tool": "generate_reminder",
            "status": "SIMULATED",
            "payment_id": payment_id,
            "action": "REMINDER",
            "channel": channel.lower(),
            "result": "reminder_sent",
            "message": f"Simulated recovery reminder dispatched via {channel.upper()} for payment {payment_id}.",
        }

    def escalate_to_human(self, payment_id: str, reason: str = "Manual intervention required") -> Dict[str, Any]:
        """
        Tool 7: Simulated escalation to operations team.
        """
        short_id = payment_id.replace("pay_", "")[:6].upper()
        return {
            "tool": "escalate_to_human",
            "status": "SIMULATED",
            "payment_id": payment_id,
            "action": "ESCALATE",
            "ticket_id": f"ESC-{short_id}",
            "result": "escalated_to_human",
            "message": f"Simulated escalation ticket created for payment {payment_id}. Reason: {reason}",
        }

    def verify_payment_state(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Dict[str, Any]:
        """
        Tool 8: Closed-Loop Re-verification via Financial State Engine.
        """
        state_result = self.state_engine.evaluate_payment(payment, events, order_events)
        return {
            "tool": "verify_payment_state",
            "payment_id": payment.payment_id,
            "verified_financial_state": state_result.state.value,
            "rule_id": state_result.rule_id,
            "reason": state_result.reason,
            "recommended_action": state_result.recommended_action.value,
        }
