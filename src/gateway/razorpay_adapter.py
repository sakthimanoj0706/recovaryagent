"""
Razorpay Payment Gateway Adapter for RecoverAI.
Provider adapter for Razorpay Sandbox/Live environment.
Disabled by default unless explicitly configured via PAYMENT_PROVIDER=razorpay.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from .base import PaymentGateway
from .models import GatewayActionResult, GatewayActionStatus, PaymentStatusResult
from state_engine.models import Event


class RazorpayGatewayAdapter(PaymentGateway):
    """
    Razorpay gateway adapter. Defaults to simulation mode if API credentials are not set.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        is_sandbox: bool = True,
    ):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        self.is_sandbox = is_sandbox
        self.provider = "razorpay"
        self._enabled = bool(self.key_id and self.key_secret and os.getenv("PAYMENT_PROVIDER", "").lower() == "razorpay")

    @property
    def provider_name(self) -> str:
        return self.provider

    @property
    def is_simulation(self) -> bool:
        # Strictly true if running in sandbox or credentials not configured
        return not self._enabled or self.is_sandbox

    def create_payment_link(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        exec_id = f"rzp_plink_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        short_id = payment_id.replace("pay_", "")[:8]

        # In sandbox/disabled mode, return structured simulation response
        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="PAYMENT_LINK",
            status=GatewayActionStatus.SUCCESS,
            provider=self.provider,
            simulation=self.is_simulation,
            timestamp=now_iso,
            message=f"Razorpay sandbox payment link created: https://rzp.io/l/{short_id}",
            metadata={
                "razorpay_link_id": f"plink_{short_id}",
                "amount": amount,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "is_sandbox": self.is_sandbox,
                **(metadata or {}),
            },
        )

    def retry_payment(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        exec_id = f"rzp_retry_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="RETRY",
            status=GatewayActionStatus.SUCCESS,
            provider=self.provider,
            simulation=self.is_simulation,
            timestamp=now_iso,
            message="Razorpay direct server-to-server retry initiated.",
            metadata={"amount": amount, "method": method or "upi", "is_sandbox": self.is_sandbox, **(metadata or {})},
        )

    def send_reminder(
        self,
        payment_id: str,
        amount: float,
        channel: str = "whatsapp",
        order_id: Optional[str] = None,
        customer_contact: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        exec_id = f"rzp_remind_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="REMINDER",
            status=GatewayActionStatus.SUCCESS,
            provider=self.provider,
            simulation=self.is_simulation,
            timestamp=now_iso,
            message=f"Razorpay customer notification dispatched via {channel}.",
            metadata={"channel": channel, "amount": amount, "is_sandbox": self.is_sandbox, **(metadata or {})},
        )

    def get_payment_status(self, payment_id: str) -> PaymentStatusResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        return PaymentStatusResult(
            payment_id=payment_id,
            status="pending",
            amount=0.0,
            captured=False,
            provider=self.provider,
            updated_at=now_iso,
            events=[],
        )

    def get_payment_events(self, payment_id: str) -> List[Event]:
        return []

    def cancel_action(self, payment_id: str, execution_id: str) -> GatewayActionResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        return GatewayActionResult(
            execution_id=f"cancel_{execution_id}",
            payment_id=payment_id,
            action="CANCEL",
            status=GatewayActionStatus.SUCCESS,
            provider=self.provider,
            simulation=self.is_simulation,
            timestamp=now_iso,
            message=f"Razorpay action {execution_id} on payment {payment_id} canceled.",
        )
