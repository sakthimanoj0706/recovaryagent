"""
Mock Payment Gateway Adapter for RecoverAI.
Provides deterministic, synthetic sandbox simulation for payment actions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from .base import PaymentGateway
from .models import GatewayActionResult, GatewayActionStatus, PaymentStatusResult
from state_engine.models import Event


class MockPaymentGateway(PaymentGateway):
    """
    In-memory deterministic mock gateway for testing and simulated execution.
    Never initiates real payment transfers or real notification dispatch.
    """

    def __init__(self, default_outcome: GatewayActionStatus = GatewayActionStatus.SUCCESS):
        self.default_outcome = default_outcome
        self.provider = "mock"
        self._action_configs: Dict[str, GatewayActionStatus] = {}
        self._payment_events: Dict[str, List[Event]] = {}
        self._action_history: List[GatewayActionResult] = []

    @property
    def provider_name(self) -> str:
        return self.provider

    @property
    def is_simulation(self) -> bool:
        return True

    def configure_outcome(self, payment_id: str, outcome: GatewayActionStatus) -> None:
        """Configure deterministic outcome override for a specific payment ID."""
        self._action_configs[payment_id] = outcome

    def reset_configurations(self) -> None:
        """Reset all custom outcome overrides."""
        self._action_configs.clear()

    def _determine_status(self, payment_id: str, force_status: Optional[GatewayActionStatus] = None) -> GatewayActionStatus:
        if force_status is not None:
            return force_status
        return self._action_configs.get(payment_id, self.default_outcome)

    def create_payment_link(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_status: Optional[GatewayActionStatus] = None,
    ) -> GatewayActionResult:
        exec_id = f"mock_plink_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        status = self._determine_status(payment_id, force_status)
        short_id = payment_id.replace("pay_", "")[:8]

        events: List[Event] = []
        if status == GatewayActionStatus.SUCCESS:
            events.append(
                Event(
                    event="payment.authorized",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                    late_authorization=True,
                )
            )
            events.append(
                Event(
                    event="payment.captured",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                )
            )
            msg = f"Mock Payment link generated: https://pay.recoverai.io/link/{short_id}. Checkout succeeded."
        elif status == GatewayActionStatus.FAILURE:
            events.append(
                Event(
                    event="payment.failed",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    error_code="RECOVERY_ATTEMPT_FAILED",
                    hardness="soft",
                    ts=now_iso,
                )
            )
            msg = "Payment link generated, but customer did not complete checkout (or payment failed)."
        elif status == GatewayActionStatus.PENDING:
            events.append(
                Event(
                    event="payment.pending",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                )
            )
            msg = "Payment link active; awaiting asynchronous customer payment."
        else:  # TIMEOUT
            msg = "Gateway timed out while creating payment link."

        if payment_id not in self._payment_events:
            self._payment_events[payment_id] = []
        self._payment_events[payment_id].extend(events)

        result = GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="PAYMENT_LINK",
            status=status,
            provider=self.provider,
            simulation=True,
            timestamp=now_iso,
            message=msg,
            metadata={
                "payment_url": f"https://pay.recoverai.io/link/{short_id}",
                "amount": amount,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                **(metadata or {}),
            },
            generated_events=events,
        )
        self._action_history.append(result)
        return result

    def retry_payment(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_status: Optional[GatewayActionStatus] = None,
    ) -> GatewayActionResult:
        exec_id = f"mock_retry_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        status = self._determine_status(payment_id, force_status)

        events: List[Event] = []
        if status == GatewayActionStatus.SUCCESS:
            events.append(
                Event(
                    event="payment.authorized",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    method=method or "upi",
                    ts=now_iso,
                    late_authorization=True,
                )
            )
            events.append(
                Event(
                    event="payment.captured",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    method=method or "upi",
                    ts=now_iso,
                )
            )
            msg = "Mock gateway direct retry succeeded and captured funds."
        elif status == GatewayActionStatus.FAILURE:
            events.append(
                Event(
                    event="payment.failed",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    method=method or "upi",
                    error_code="RETRY_REJECTED",
                    hardness="soft",
                    ts=now_iso,
                )
            )
            msg = "Mock gateway direct retry declined by issuing bank."
        elif status == GatewayActionStatus.PENDING:
            events.append(
                Event(
                    event="payment.pending",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                )
            )
            msg = "Direct retry queued on bank rail; pending confirmation."
        else:  # TIMEOUT
            msg = "Direct retry call timed out."

        if payment_id not in self._payment_events:
            self._payment_events[payment_id] = []
        self._payment_events[payment_id].extend(events)

        result = GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="RETRY",
            status=status,
            provider=self.provider,
            simulation=True,
            timestamp=now_iso,
            message=msg,
            metadata={"amount": amount, "method": method or "upi", **(metadata or {})},
            generated_events=events,
        )
        self._action_history.append(result)
        return result

    def send_reminder(
        self,
        payment_id: str,
        amount: float,
        channel: str = "whatsapp",
        order_id: Optional[str] = None,
        customer_contact: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_status: Optional[GatewayActionStatus] = None,
    ) -> GatewayActionResult:
        exec_id = f"mock_remind_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        status = self._determine_status(payment_id, force_status)

        events: List[Event] = []
        if status == GatewayActionStatus.SUCCESS:
            events.append(
                Event(
                    event="payment.authorized",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                    late_authorization=True,
                )
            )
            events.append(
                Event(
                    event="payment.captured",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                )
            )
            msg = f"Mock customer reminder sent via {channel}. Customer paid successfully."
        elif status == GatewayActionStatus.FAILURE:
            events.append(
                Event(
                    event="payment.failed",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    error_code="REMINDER_NO_RESPONSE",
                    hardness="soft",
                    ts=now_iso,
                )
            )
            msg = f"Reminder sent via {channel}, but no payment was made."
        elif status == GatewayActionStatus.PENDING:
            events.append(
                Event(
                    event="payment.pending",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    ts=now_iso,
                )
            )
            msg = f"Reminder dispatched via {channel}. Awaiting customer interaction."
        else:  # TIMEOUT
            msg = f"Reminder notification channel ({channel}) timed out."

        if payment_id not in self._payment_events:
            self._payment_events[payment_id] = []
        self._payment_events[payment_id].extend(events)

        result = GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="REMINDER",
            status=status,
            provider=self.provider,
            simulation=True,
            timestamp=now_iso,
            message=msg,
            metadata={"channel": channel, "amount": amount, **(metadata or {})},
            generated_events=events,
        )
        self._action_history.append(result)
        return result

    def get_payment_status(self, payment_id: str) -> PaymentStatusResult:
        evs = self._payment_events.get(payment_id, [])
        is_cap = any(e.event in ["payment.captured", "payment.authorized"] for e in evs)
        st = "captured" if is_cap else "failed" if any(e.event == "payment.failed" for e in evs) else "unknown"
        amt = next((e.amount for e in evs if e.amount is not None), 0.0)

        return PaymentStatusResult(
            payment_id=payment_id,
            status=st,
            amount=amt,
            captured=is_cap,
            provider=self.provider,
            events=evs,
        )

    def get_payment_events(self, payment_id: str) -> List[Event]:
        return list(self._payment_events.get(payment_id, []))

    def cancel_action(self, payment_id: str, execution_id: str) -> GatewayActionResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        return GatewayActionResult(
            execution_id=f"cancel_{execution_id}",
            payment_id=payment_id,
            action="CANCEL",
            status=GatewayActionStatus.SUCCESS,
            provider=self.provider,
            simulation=True,
            timestamp=now_iso,
            message=f"Action {execution_id} on payment {payment_id} was successfully canceled.",
            metadata={"canceled_execution_id": execution_id},
        )
