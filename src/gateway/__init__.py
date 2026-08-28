"""
Payment Gateway Integration Layer for RecoverAI.
Provides provider-independent payment interfaces and deterministic mock implementations.
"""

import os
from typing import Optional
from .base import PaymentGateway
from .mock_gateway import MockPaymentGateway
from .razorpay_adapter import RazorpayGatewayAdapter
from .models import (
    GatewayActionType,
    GatewayActionStatus,
    GatewayActionResult,
    PaymentStatusResult,
)


_DEFAULT_GATEWAY: Optional[PaymentGateway] = None


def get_gateway(provider: Optional[str] = None) -> PaymentGateway:
    """
    Factory function returning configured payment gateway adapter.
    Defaults to MockPaymentGateway unless explicitly configured via PAYMENT_PROVIDER env var.
    """
    global _DEFAULT_GATEWAY
    prov = (provider or os.getenv("PAYMENT_PROVIDER", "mock")).lower()

    if prov == "razorpay":
        return RazorpayGatewayAdapter()

    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = MockPaymentGateway()
    return _DEFAULT_GATEWAY


__all__ = [
    "PaymentGateway",
    "MockPaymentGateway",
    "RazorpayGatewayAdapter",
    "GatewayActionType",
    "GatewayActionStatus",
    "GatewayActionResult",
    "PaymentStatusResult",
    "get_gateway",
]
