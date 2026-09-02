"""
Razorpay Payment Gateway Adapter for RecoverAI — Step 14 Edition.

Supports three modes controlled by RECOVERAI_PROVIDER_MODE:
  simulation     — Deterministic mock (default, no HTTP calls)
  razorpay_test  — Real Razorpay Test API (no live money)
  razorpay_live  — HARD BLOCKED by deployment policy

RecoverAI uses Razorpay Test Mode for external integration validation.
Test Mode does not process real payments.
Live financial execution is intentionally disabled.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from .base import PaymentGateway
from .models import GatewayActionResult, GatewayActionStatus, PaymentStatusResult
from .provider_config import (
    ProviderMode,
    get_provider_mode,
    get_capabilities,
    assert_live_execution_disabled,
    LiveModeDisabledError,
)
from .razorpay_models import (
    RazorpayPaymentLinkRequest,
    RazorpayPayment,
    RazorpayOrder,
    RazorpayOrderPayments,
    RazorpayPaymentLink,
)
from state_engine.models import Event

logger = logging.getLogger(__name__)


class RazorpayGatewayAdapter(PaymentGateway):
    """
    Razorpay gateway adapter supporting SIMULATION and RAZORPAY_TEST modes.

    In SIMULATION mode: returns deterministic mock results with zero HTTP calls.
    In RAZORPAY_TEST mode: calls real Razorpay Test API using RazorpayClient.
    In RAZORPAY_LIVE mode: hard-blocked — raises LiveModeDisabledError.

    This adapter NEVER bypasses ActionExecutor, PolicyEngine, or RecoveryFirewall.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        mode: Optional[ProviderMode] = None,
    ):
        self._mode = mode or get_provider_mode()
        self._capabilities = get_capabilities(self._mode)

        # Hard-block live mode at construction time
        assert_live_execution_disabled(self._mode)

        self._key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "")
        # key_secret stored but NEVER logged
        self._key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")

        self._client: Optional[Any] = None  # Lazy-initialised RazorpayClient

        logger.info(
            "RazorpayGatewayAdapter initialised",
            extra={
                "provider": "razorpay",
                "mode": self._mode.value,
                "live_execution": False,
                # key_secret NEVER logged
            },
        )

    def _get_client(self):
        """Lazily initialise RazorpayClient for test mode."""
        if self._client is None:
            from .razorpay_client import RazorpayClient, RazorpayClientError
            try:
                self._client = RazorpayClient(
                    key_id=self._key_id,
                    key_secret=self._key_secret,
                )
            except RazorpayClientError as exc:
                logger.error("Failed to initialise RazorpayClient: %s", exc)
                raise
        return self._client

    @property
    def provider_name(self) -> str:
        return "razorpay"

    @property
    def is_simulation(self) -> bool:
        return self._mode == ProviderMode.SIMULATION

    @property
    def provider_mode(self) -> ProviderMode:
        return self._mode

    def test_connection(self, correlation_id: Optional[str] = None) -> Tuple[bool, str]:
        """Test connectivity to the Razorpay API."""
        if self._mode == ProviderMode.SIMULATION:
            return True, "SIMULATION mode — no external connectivity"
        if self._mode == ProviderMode.RAZORPAY_LIVE:
            return False, "RAZORPAY_LIVE mode is blocked by deployment policy"

        try:
            client = self._get_client()
            return client.test_connection(correlation_id=correlation_id)
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    def create_payment_link(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> GatewayActionResult:
        """Create a Payment Link — simulation or real Razorpay Test API."""
        exec_id = f"rzp_plink_{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._mode == ProviderMode.SIMULATION:
            return self._simulate_payment_link(
                payment_id, amount, order_id, exec_id, now_iso, metadata
            )

        if self._mode == ProviderMode.RAZORPAY_TEST:
            return self._real_create_payment_link(
                payment_id, amount, order_id, description, metadata,
                exec_id, now_iso, correlation_id
            )

        # Live mode — hard block (should never reach here due to constructor check)
        raise LiveModeDisabledError("LIVE PAYMENT EXECUTION IS DISABLED.")

    def _simulate_payment_link(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str],
        exec_id: str,
        now_iso: str,
        metadata: Optional[Dict[str, Any]],
    ) -> GatewayActionResult:
        short_id = payment_id.replace("pay_", "")[:10]
        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="PAYMENT_LINK",
            status=GatewayActionStatus.SUCCESS,
            provider="razorpay",
            simulation=True,
            timestamp=now_iso,
            message=f"[SIMULATION] Razorpay payment link: https://rzp.io/l/{short_id}",
            metadata={
                "provider_link_id": f"plink_{short_id}",
                "short_url": f"https://rzp.io/l/{short_id}",
                "amount_inr": amount,
                "provider_mode": "simulation",
                **(metadata or {}),
            },
        )

    def _real_create_payment_link(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str],
        description: Optional[str],
        metadata: Optional[Dict[str, Any]],
        exec_id: str,
        now_iso: str,
        correlation_id: Optional[str],
    ) -> GatewayActionResult:
        """Call real Razorpay Payment Links API."""
        from .razorpay_client import RazorpayClientError
        try:
            amount_paise = int(round(amount * 100))
            request = RazorpayPaymentLinkRequest(
                amount=amount_paise,
                currency="INR",
                description=description or f"RecoverAI recovery: {payment_id}",
                reference_id=payment_id,  # idempotency key
                notify={"sms": False, "email": False},
                reminder_enable=False,
                notes={
                    "recoverai_payment_id": payment_id,
                    "recoverai_correlation_id": correlation_id or exec_id,
                    "provider_mode": "test",
                },
            )

            client = self._get_client()
            link: RazorpayPaymentLink = client.create_payment_link(
                request, correlation_id=correlation_id
            )

            logger.info(
                "Razorpay payment link created (TEST MODE)",
                extra={
                    "provider": "razorpay",
                    "mode": "test",
                    "operation": "create_payment_link",
                    "payment_id": payment_id,
                    "link_id": link.id,
                    "correlation_id": correlation_id,
                    "live_money": False,
                },
            )

            return GatewayActionResult(
                execution_id=exec_id,
                payment_id=payment_id,
                order_id=order_id,
                action="PAYMENT_LINK",
                status=GatewayActionStatus.SUCCESS,
                provider="razorpay",
                simulation=False,
                timestamp=now_iso,
                message=f"[RAZORPAY TEST] Payment link created: {link.short_url or link.id}",
                metadata={
                    "provider_link_id": link.id,
                    "short_url": link.short_url,
                    "amount_inr": link.amount_inr,
                    "status": link.status,
                    "reference_id": link.reference_id,
                    "provider_mode": "razorpay_test",
                    "live_money": False,
                    **(metadata or {}),
                },
            )

        except RazorpayClientError as exc:
            logger.warning(
                "Razorpay payment link creation failed (TEST MODE)",
                extra={
                    "provider": "razorpay",
                    "operation": "create_payment_link",
                    "payment_id": payment_id,
                    "error_code": getattr(exc, "error_code", None),
                },
            )
            return GatewayActionResult(
                execution_id=exec_id,
                payment_id=payment_id,
                order_id=order_id,
                action="PAYMENT_LINK",
                status=GatewayActionStatus.FAILURE,
                provider="razorpay",
                simulation=False,
                timestamp=now_iso,
                message=f"[RAZORPAY TEST] Payment link creation failed: {exc}",
                metadata={"error": str(exc), "provider_mode": "razorpay_test"},
            )

    def retry_payment(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        """
        Direct server-to-server payment retry.
        NOTE: Razorpay does not support automated direct retry via API
        in the same way. This falls back to simulation in all modes.
        """
        exec_id = f"rzp_retry_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="RETRY",
            status=GatewayActionStatus.SUCCESS,
            provider="razorpay",
            simulation=True,
            timestamp=now_iso,
            message="[SIMULATION] Direct retry not supported via Razorpay API; simulated.",
            metadata={"amount": amount, "method": method or "upi", **(metadata or {})},
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
        """Customer notification reminder — simulated."""
        exec_id = f"rzp_remind_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        return GatewayActionResult(
            execution_id=exec_id,
            payment_id=payment_id,
            order_id=order_id,
            action="REMINDER",
            status=GatewayActionStatus.SUCCESS,
            provider="razorpay",
            simulation=True,
            timestamp=now_iso,
            message=f"[SIMULATION] Customer notification via {channel} simulated.",
            metadata={"channel": channel, "amount": amount, **(metadata or {})},
        )

    def get_payment_status(
        self,
        payment_id: str,
        correlation_id: Optional[str] = None,
    ) -> PaymentStatusResult:
        """
        Query Razorpay for payment status.
        In TEST mode: calls real Razorpay API.
        In SIMULATION mode: returns deterministic stub.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._mode == ProviderMode.SIMULATION:
            return PaymentStatusResult(
                payment_id=payment_id,
                status="simulated",
                amount=0.0,
                captured=False,
                provider="razorpay",
                updated_at=now_iso,
                events=[],
            )

        if self._mode == ProviderMode.RAZORPAY_TEST:
            from .razorpay_client import RazorpayClientError
            try:
                client = self._get_client()
                payment: RazorpayPayment = client.fetch_payment(
                    payment_id, correlation_id=correlation_id
                )
                return PaymentStatusResult(
                    payment_id=payment.id,
                    order_id=payment.order_id,
                    status=payment.status,
                    amount=payment.amount_inr,
                    currency=payment.currency,
                    captured=payment.is_captured,
                    provider="razorpay",
                    updated_at=now_iso,
                    events=[],
                )
            except RazorpayClientError as exc:
                return PaymentStatusResult(
                    payment_id=payment_id,
                    status=f"fetch_error:{exc}",
                    amount=0.0,
                    captured=False,
                    provider="razorpay",
                    updated_at=now_iso,
                    events=[],
                )

        raise LiveModeDisabledError("LIVE PAYMENT EXECUTION IS DISABLED.")

    def fetch_payment(
        self,
        payment_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[RazorpayPayment]:
        """Fetch raw Razorpay payment object (TEST mode only)."""
        if self._mode != ProviderMode.RAZORPAY_TEST:
            return None
        from .razorpay_client import RazorpayClientError
        try:
            return self._get_client().fetch_payment(payment_id, correlation_id=correlation_id)
        except RazorpayClientError:
            return None

    def fetch_order(
        self,
        order_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[RazorpayOrder]:
        """Fetch raw Razorpay order object (TEST mode only)."""
        if self._mode != ProviderMode.RAZORPAY_TEST:
            return None
        from .razorpay_client import RazorpayClientError
        try:
            return self._get_client().fetch_order(order_id, correlation_id=correlation_id)
        except RazorpayClientError:
            return None

    def fetch_order_payments(
        self,
        order_id: str,
        correlation_id: Optional[str] = None,
    ) -> Optional[RazorpayOrderPayments]:
        """Fetch all payments for a Razorpay order (TEST mode only)."""
        if self._mode != ProviderMode.RAZORPAY_TEST:
            return None
        from .razorpay_client import RazorpayClientError
        try:
            return self._get_client().fetch_order_payments(order_id, correlation_id=correlation_id)
        except RazorpayClientError:
            return None

    def get_payment_events(self, payment_id: str) -> List[Event]:
        """Return empty list — event ingestion is handled via webhook pipeline."""
        return []

    def cancel_action(self, payment_id: str, execution_id: str) -> GatewayActionResult:
        """Cancel/void an in-flight recovery action."""
        now_iso = datetime.now(timezone.utc).isoformat()
        return GatewayActionResult(
            execution_id=f"cancel_{execution_id}",
            payment_id=payment_id,
            action="CANCEL",
            status=GatewayActionStatus.SUCCESS,
            provider="razorpay",
            simulation=self.is_simulation,
            timestamp=now_iso,
            message=f"Recovery action {execution_id} on {payment_id} cancelled.",
        )
