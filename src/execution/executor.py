"""
Action Executor for RecoverAI.
Performs strictly simulated recovery operations with synthetic execution responses.
"""

from typing import Optional, Dict, Any
from agent.models import RecoveryAction, RecoveryPlan, RecoveryContext
from .actions import ActionExecutionRequest, ActionExecutionResponse
from .simulator import SyntheticSimulationEngine


class ActionExecutor:
    """
    Simulates operational execution of recovery plans.
    Guarantees no real payment rail or notification gateway is triggered.
    """

    def __init__(self, simulator: Optional[SyntheticSimulationEngine] = None):
        self.simulator = simulator or SyntheticSimulationEngine()

    def execute_retry(
        self,
        payment_id: str,
        amount: float = 0.0,
        context: Optional[RecoveryContext] = None,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="VERIFIED_LOST",
            amount=amount,
        )
        success, msg, events = self.simulator.simulate_outcome(ctx, RecoveryAction.RETRY, force_success=force_success)
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.RETRY,
            simulated_success=success,
            message=msg,
            generated_events=events,
            metadata={"amount": amount, "simulation_mode": "SYNTHETIC SIMULATION"},
        )

    def execute_payment_link(
        self,
        payment_id: str,
        amount: float = 0.0,
        context: Optional[RecoveryContext] = None,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="VERIFIED_LOST",
            amount=amount,
        )
        success, msg, events = self.simulator.simulate_outcome(ctx, RecoveryAction.PAYMENT_LINK, force_success=force_success)
        short_id = payment_id.replace("pay_", "")[:8]
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.PAYMENT_LINK,
            simulated_success=success,
            message=msg,
            generated_events=events,
            metadata={
                "amount": amount,
                "payment_url": f"https://pay.recoverai.io/link/{short_id}",
                "simulation_mode": "SYNTHETIC SIMULATION",
            },
        )

    def execute_reminder(
        self,
        payment_id: str,
        channel: str = "sms",
        amount: float = 0.0,
        context: Optional[RecoveryContext] = None,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="VERIFIED_LOST",
            amount=amount,
        )
        success, msg, events = self.simulator.simulate_outcome(ctx, RecoveryAction.REMINDER, force_success=force_success)
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.REMINDER,
            simulated_success=success,
            message=msg,
            generated_events=events,
            metadata={"channel": channel, "simulation_mode": "SYNTHETIC SIMULATION"},
        )

    def execute_wait(
        self,
        payment_id: str,
        duration_seconds: int = 60,
        context: Optional[RecoveryContext] = None,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="UNCERTAIN",
            amount=0.0,
        )
        success, msg, events = self.simulator.simulate_outcome(ctx, RecoveryAction.WAIT, force_success=force_success)
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.WAIT,
            simulated_success=success,
            message=msg,
            generated_events=events,
            metadata={"duration_seconds": duration_seconds, "simulation_mode": "SYNTHETIC SIMULATION"},
        )

    def execute_escalate(
        self,
        payment_id: str,
        reason: str = "Manual intervention required",
        context: Optional[RecoveryContext] = None,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="EXCEPTION",
            amount=0.0,
        )
        success, msg, events = self.simulator.simulate_outcome(ctx, RecoveryAction.ESCALATE, force_success=force_success)
        ticket_id = f"ESC-{payment_id.replace('pay_', '')[:6].upper()}"
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.ESCALATE,
            simulated_success=success,
            message=f"{msg} (Ticket ID: {ticket_id}, Reason: {reason})",
            generated_events=events,
            metadata={"ticket_id": ticket_id, "reason": reason, "simulation_mode": "SYNTHETIC SIMULATION"},
        )

    def execute_stop(
        self,
        payment_id: str,
        reason: str = "Recovery halted",
        context: Optional[RecoveryContext] = None,
    ) -> ActionExecutionResponse:
        ctx = context or RecoveryContext(
            payment_id=payment_id,
            financial_state="VERIFIED_LOST",
            amount=0.0,
        )
        return ActionExecutionResponse(
            payment_id=payment_id,
            order_id=ctx.order_id,
            action=RecoveryAction.STOP,
            simulated_success=False,
            message=f"[SYNTHETIC SIMULATION] Action STOP executed. {reason}",
            generated_events=[],
            metadata={"reason": reason, "simulation_mode": "SYNTHETIC SIMULATION"},
        )

    def execute(
        self,
        plan: RecoveryPlan,
        context: RecoveryContext,
        force_success: Optional[bool] = None,
    ) -> ActionExecutionResponse:
        """
        Dispatch execution based on the recommended RecoveryAction.
        """
        action = plan.action
        if action == RecoveryAction.RETRY:
            return self.execute_retry(plan.payment_id, amount=context.amount, context=context, force_success=force_success)
        elif action == RecoveryAction.PAYMENT_LINK:
            return self.execute_payment_link(plan.payment_id, amount=context.amount, context=context, force_success=force_success)
        elif action == RecoveryAction.REMINDER:
            return self.execute_reminder(plan.payment_id, channel="sms", amount=context.amount, context=context, force_success=force_success)
        elif action == RecoveryAction.WAIT:
            return self.execute_wait(plan.payment_id, duration_seconds=60, context=context, force_success=force_success)
        elif action == RecoveryAction.ESCALATE:
            return self.execute_escalate(plan.payment_id, reason=plan.reason, context=context, force_success=force_success)
        elif action == RecoveryAction.STOP:
            return self.execute_stop(plan.payment_id, reason=plan.reason, context=context)
        else:
            return self.execute_stop(plan.payment_id, reason=f"Unknown action {action}", context=context)
