"""
Recovery Verifier for RecoverAI.
Enforces the core rule: Never trust the agent. The Financial State Engine is the absolute source of truth.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from state_engine import FinancialStateEngine, PaymentRecord, Event
from .actions import ActionExecutionResponse


class VerificationResult(BaseModel):
    """
    Independent verification verdict from the Financial State Engine.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    agent_action: str
    agent_claimed_success: bool
    verified_financial_state: str
    source_of_truth: str = "FINANCIAL STATE ENGINE"
    rule_id: Optional[str] = None
    reason: str
    is_verified_recovery: bool
    state_result: Optional[Any] = None
    recovered_amount: Optional[float] = None
    outstanding_amount: Optional[float] = None


class RecoveryVerifier:
    """
    Verifies actual financial state post-execution by re-evaluating the complete event stream.
    """

    def __init__(self, state_engine: Optional[FinancialStateEngine] = None):
        self.state_engine = state_engine or FinancialStateEngine()

    def verify(
        self,
        payment: PaymentRecord,
        original_events: List[Event],
        execution_response: ActionExecutionResponse,
        order_events: Optional[List[Event]] = None,
    ) -> VerificationResult:
        """
        Re-evaluate the full event trail including post-action generated events.
        """
        # Combine original history + post-execution events
        full_events = list(original_events) + list(execution_response.generated_events)
        
        # If order_events exist, also include post-execution events in order context
        full_order_events = None
        if order_events is not None:
            full_order_events = list(order_events) + list(execution_response.generated_events)

        # Independent financial state evaluation
        state_eval = self.state_engine.evaluate_payment(payment, full_events, full_order_events)
        verified_state = state_eval.state.value

        is_recovered = (verified_state == "ALREADY_RECOVERED")

        return VerificationResult(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            agent_action=execution_response.action.value if hasattr(execution_response.action, "value") else str(execution_response.action),
            agent_claimed_success=execution_response.simulated_success,
            verified_financial_state=verified_state,
            source_of_truth="FINANCIAL STATE ENGINE",
            rule_id=state_eval.rule_id,
            reason=state_eval.reason,
            is_verified_recovery=is_recovered,
            state_result=state_eval,
            recovered_amount=state_eval.recovered_amount,
            outstanding_amount=state_eval.outstanding_amount,
        )


    def verify_post_action(
        self,
        payment: PaymentRecord,
        post_action_events: List[Event],
        order_events: Optional[List[Event]] = None,
    ) -> Any:
        """Direct verification on the financial state engine with post-action events."""
        return self.state_engine.evaluate_payment(payment, post_action_events, order_events)

