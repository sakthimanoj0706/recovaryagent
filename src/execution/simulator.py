"""
Deterministic Synthetic Simulation Engine for RecoverAI.
Simulates realistic recovery outcomes without connecting to real financial networks.
"""

import random
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from state_engine.models import Event
from agent.models import RecoveryAction, RecoveryContext


class SyntheticSimulationEngine:
    """
    Simulates operational outcome of recovery actions in a strictly controlled synthetic environment.
    All outputs are explicitly flagged as 'SYNTHETIC SIMULATION'.
    """

    def __init__(self, simulation_seed: Optional[int] = 42):
        self.simulation_seed = simulation_seed
        self._rng = random.Random(simulation_seed)

    def set_seed(self, seed: int):
        """Reset random seed for reproducible simulations."""
        self.simulation_seed = seed
        self._rng = random.Random(seed)

    def simulate_outcome(
        self,
        context: RecoveryContext,
        action: RecoveryAction,
        force_success: Optional[bool] = None,
    ) -> Tuple[bool, str, List[Event]]:
        """
        Simulate customer/gateway response to the action.
        Returns:
            (is_success, simulation_message, generated_events)
        """
        if force_success is not None:
            success = force_success
        else:
            success = self._determine_probabilistic_success(context, action)

        now_ts = datetime.now(timezone.utc).isoformat()
        events: List[Event] = []

        if action == RecoveryAction.STOP:
            return (
                False,
                "[SYNTHETIC SIMULATION] Recovery halted. No customer intervention dispatched.",
                [],
            )

        if action == RecoveryAction.WAIT:
            # Simulated wait might leave state pending or transition
            if success:
                events = [
                    Event(event="payment.authorized", payment_id=context.payment_id, order_id=context.order_id, ts=now_ts),
                    Event(event="payment.captured", payment_id=context.payment_id, order_id=context.order_id, ts=now_ts),
                ]
                msg = "[SYNTHETIC SIMULATION] Asynchronous settlement resolved successfully during wait period."
            else:
                events = [
                    Event(event="payment.pending", payment_id=context.payment_id, order_id=context.order_id, ts=now_ts),
                ]
                msg = "[SYNTHETIC SIMULATION] Payment remains in pending state awaiting clearing network."
            return success, msg, events

        if success:
            events = [
                Event(
                    event="payment.authorized",
                    payment_id=context.payment_id,
                    order_id=context.order_id,
                    amount=context.amount,
                    method=context.method,
                    ts=now_ts,
                ),
                Event(
                    event="payment.captured",
                    payment_id=context.payment_id,
                    order_id=context.order_id,
                    amount=context.amount,
                    method=context.method,
                    ts=now_ts,
                ),
            ]
            msg = f"[SYNTHETIC SIMULATION] Action {action.value} succeeded. Customer authorized and payment captured."
        else:
            events = [
                Event(
                    event="payment.failed",
                    payment_id=context.payment_id,
                    order_id=context.order_id,
                    amount=context.amount,
                    error_code=context.failure_reason or "RECOVERY_ATTEMPT_FAILED",
                    hardness=context.hardness or "soft",
                    ts=now_ts,
                )
            ]
            msg = f"[SYNTHETIC SIMULATION] Action {action.value} failed. Payment attempt did not complete."

        return success, msg, events

    def _determine_probabilistic_success(self, context: RecoveryContext, action: RecoveryAction) -> bool:
        """
        Evaluate baseline probability based on failure reason and action type.
        """
        err_code = (context.failure_reason or "").upper()
        hardness = (context.hardness or "soft").lower()

        # Hard declines never succeed via retry
        if hardness == "hard" and action == RecoveryAction.RETRY:
            return False

        if action == RecoveryAction.PAYMENT_LINK:
            base_rate = 0.65
            if context.customer_segment == "high_value_repeat":
                base_rate += 0.20
            elif context.customer_segment == "new":
                base_rate -= 0.15
            return self._rng.random() < max(0.1, min(0.95, base_rate))

        elif action == RecoveryAction.REMINDER:
            base_rate = 0.45
            if err_code == "USER_CANCELLED":
                base_rate += 0.20
            return self._rng.random() < max(0.1, min(0.9, base_rate))

        elif action == RecoveryAction.RETRY:
            if err_code == "BANK_DOWNTIME":
                base_rate = 0.80
            elif err_code == "TIMEOUT":
                base_rate = 0.60
            elif err_code == "INSUFFICIENT_FUNDS":
                base_rate = 0.15
            else:
                base_rate = 0.35
            return self._rng.random() < base_rate

        elif action == RecoveryAction.ESCALATE:
            return self._rng.random() < 0.50

        return False
