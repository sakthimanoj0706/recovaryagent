"""
Payment Gateway Integration Layer for RecoverAI.
Provides provider-independent payment interfaces and deterministic mock implementations.

Step 14: Extended with ProviderMode, ProviderCapabilities, and Razorpay Test Mode adapter.
"""

import os
from typing import Optional
from .base import PaymentGateway
from .mock_gateway import MockPaymentGateway
from .razorpay_adapter import RazorpayGatewayAdapter
from .provider_config import (
    ProviderMode,
    ProviderCapabilities,
    LiveModeDisabledError,
    get_provider_mode,
    get_capabilities,
    assert_live_execution_disabled,
    get_provider_display_name,
)
from .models import (
    GatewayActionType,
    GatewayActionStatus,
    GatewayActionResult,
    PaymentStatusResult,
)
from .razorpay_models import (
    RazorpayPayment,
    RazorpayOrder,
    RazorpayOrderPayments,
    RazorpayPaymentLink,
    RazorpayWebhookEvent,
    RazorpayProviderStatus,
)
from .razorpay_webhook import (
    RazorpayWebhookSignatureValidator,
    RazorpayWebhookNormalizer,
    RazorpaySignatureError,
    extract_razorpay_event_id,
    extract_razorpay_signature,
)


_DEFAULT_GATEWAY: Optional[PaymentGateway] = None


def get_gateway(provider: Optional[str] = None) -> PaymentGateway:
    """
    Factory function returning configured payment gateway adapter.

    Provider resolution order:
    1. Explicit `provider` argument
    2. RECOVERAI_PROVIDER_MODE environment variable (new in Step 14)
    3. PAYMENT_PROVIDER environment variable (legacy fallback)
    4. Default: MockPaymentGateway (SIMULATION)
    """
    global _DEFAULT_GATEWAY

    # If explicit provider override passed, always create fresh
    if provider:
        prov = provider.lower()
        if prov == "razorpay":
            return RazorpayGatewayAdapter()
        return MockPaymentGateway()

    # Read from ProviderMode (Step 14 standard)
    mode = get_provider_mode()

    if mode in (ProviderMode.RAZORPAY_TEST, ProviderMode.RAZORPAY_LIVE):
        return RazorpayGatewayAdapter(mode=mode)

    # SIMULATION mode — use cached singleton
    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = MockPaymentGateway()
    return _DEFAULT_GATEWAY


__all__ = [
    # Gateway classes
    "PaymentGateway",
    "MockPaymentGateway",
    "RazorpayGatewayAdapter",
    # Provider configuration
    "ProviderMode",
    "ProviderCapabilities",
    "LiveModeDisabledError",
    "get_provider_mode",
    "get_capabilities",
    "assert_live_execution_disabled",
    "get_provider_display_name",
    # Gateway models
    "GatewayActionType",
    "GatewayActionStatus",
    "GatewayActionResult",
    "PaymentStatusResult",
    # Razorpay models
    "RazorpayPayment",
    "RazorpayOrder",
    "RazorpayOrderPayments",
    "RazorpayPaymentLink",
    "RazorpayWebhookEvent",
    "RazorpayProviderStatus",
    # Webhook
    "RazorpayWebhookSignatureValidator",
    "RazorpayWebhookNormalizer",
    "RazorpaySignatureError",
    "extract_razorpay_event_id",
    "extract_razorpay_signature",
    # Factory
    "get_gateway",
]
