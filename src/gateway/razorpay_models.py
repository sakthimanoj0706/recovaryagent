"""
Razorpay API Response Models for RecoverAI.

Only models fields actually required by the RecoverAI recovery workflow.
Uses extra="ignore" to handle forward-compatible unknown fields gracefully.
Unknown fields do not break parsing.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RazorpayErrorDetail(BaseModel):
    """Razorpay structured error payload."""
    model_config = ConfigDict(extra="ignore")

    code: Optional[str] = None
    description: Optional[str] = None
    field: Optional[str] = None
    source: Optional[str] = None
    step: Optional[str] = None
    reason: Optional[str] = None


class RazorpayError(BaseModel):
    """Top-level Razorpay error wrapper."""
    model_config = ConfigDict(extra="ignore")

    error: Optional[RazorpayErrorDetail] = None

    def get_description(self) -> str:
        if self.error and self.error.description:
            return self.error.description
        return "Unknown Razorpay error"

    def get_code(self) -> Optional[str]:
        if self.error:
            return self.error.code
        return None


class RazorpayPayment(BaseModel):
    """
    Razorpay payment object — fields used by RecoverAI.
    Ref: https://razorpay.com/docs/api/payments/
    """
    model_config = ConfigDict(extra="ignore")

    id: str                                     # e.g. "pay_xxxxx"
    order_id: Optional[str] = None             # e.g. "order_xxxxx"
    amount: int = 0                             # Amount in paise (smallest currency unit)
    currency: str = "INR"
    status: str = "created"                    # created|authorized|captured|refunded|failed
    captured: bool = False
    method: Optional[str] = None               # upi|card|netbanking|wallet
    error_code: Optional[str] = None           # e.g. "BAD_REQUEST_ERROR"
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    international: bool = False
    created_at: Optional[int] = None           # Unix timestamp

    @property
    def amount_inr(self) -> float:
        """Convert paise to INR."""
        return self.amount / 100.0

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_captured(self) -> bool:
        return self.status == "captured" or self.captured

    @property
    def is_authorized(self) -> bool:
        return self.status == "authorized"


class RazorpayOrder(BaseModel):
    """
    Razorpay order object — fields used by RecoverAI.
    Ref: https://razorpay.com/docs/api/orders/
    """
    model_config = ConfigDict(extra="ignore")

    id: str                                     # e.g. "order_xxxxx"
    amount: int = 0                             # Amount in paise
    amount_paid: int = 0                        # Amount already paid
    amount_due: int = 0                         # Amount still due
    currency: str = "INR"
    status: str = "created"                    # created|attempted|paid
    receipt: Optional[str] = None              # Merchant's order reference
    attempts: int = 0
    created_at: Optional[int] = None

    @property
    def amount_inr(self) -> float:
        return self.amount / 100.0

    @property
    def is_paid(self) -> bool:
        return self.status == "paid"


class RazorpayOrderPayments(BaseModel):
    """List of payments for an order."""
    model_config = ConfigDict(extra="ignore")

    entity: str = "collection"
    count: int = 0
    items: List[RazorpayPayment] = Field(default_factory=list)


class RazorpayPaymentLink(BaseModel):
    """
    Razorpay Payment Link object.
    Ref: https://razorpay.com/docs/api/payments/payment-links/
    """
    model_config = ConfigDict(extra="ignore")

    id: str                                     # e.g. "plink_xxxxx"
    short_url: Optional[str] = None            # Short URL for the payment link
    amount: int = 0                             # Amount in paise
    currency: str = "INR"
    status: str = "created"                    # created|partially_paid|expired|cancelled|paid
    reference_id: Optional[str] = None        # Merchant's reference for idempotency
    description: Optional[str] = None
    expire_by: Optional[int] = None            # Unix expiry timestamp
    created_at: Optional[int] = None

    @property
    def amount_inr(self) -> float:
        return self.amount / 100.0

    @property
    def is_active(self) -> bool:
        return self.status in ("created", "partially_paid")


class RazorpayPaymentLinkRequest(BaseModel):
    """Request model for creating a Razorpay Payment Link."""
    model_config = ConfigDict(extra="ignore")

    amount: int                                 # Amount in paise
    currency: str = "INR"
    description: Optional[str] = None
    reference_id: Optional[str] = None        # Idempotency key
    expire_by: Optional[int] = None
    notify: Dict[str, bool] = Field(default_factory=lambda: {"sms": False, "email": False})
    reminder_enable: bool = False
    notes: Dict[str, str] = Field(default_factory=dict)  # Metadata (UNTRUSTED in RecoverAI)


class RazorpayWebhookPaymentEntity(BaseModel):
    """Payment entity inside Razorpay webhook payload."""
    model_config = ConfigDict(extra="ignore")

    entity: RazorpayPayment


class RazorpayWebhookOrderEntity(BaseModel):
    """Order entity inside Razorpay webhook payload."""
    model_config = ConfigDict(extra="ignore")

    entity: RazorpayOrder


class RazorpayWebhookPayload(BaseModel):
    """Webhook event payload containing entities."""
    model_config = ConfigDict(extra="ignore")

    payment: Optional[RazorpayWebhookPaymentEntity] = None
    order: Optional[RazorpayWebhookOrderEntity] = None


class RazorpayWebhookEvent(BaseModel):
    """
    Top-level Razorpay webhook event.
    Ref: https://razorpay.com/docs/webhooks/
    """
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None                   # x-razorpay-event-id header value
    entity: str = "event"
    event: str                                  # e.g. "payment.failed"
    contains: List[str] = Field(default_factory=list)  # e.g. ["payment"]
    payload: RazorpayWebhookPayload = Field(default_factory=RazorpayWebhookPayload)
    created_at: Optional[int] = None           # Unix timestamp
    account_id: Optional[str] = None

    def get_payment(self) -> Optional[RazorpayPayment]:
        if self.payload.payment:
            return self.payload.payment.entity
        return None

    def get_order(self) -> Optional[RazorpayOrder]:
        if self.payload.order:
            return self.payload.order.entity
        return None


class RazorpayProviderStatus(BaseModel):
    """Provider status response for the /api/provider/status endpoint."""
    model_config = ConfigDict(extra="ignore")

    provider_mode: str
    provider_name: str
    test_mode: bool
    live_enabled: bool
    configuration_status: str              # CONFIGURED | NOT_CONFIGURED | PARTIAL
    api_reachable: Optional[bool] = None
    webhook_configured: bool = False
    capabilities: Dict[str, bool] = Field(default_factory=dict)
    last_provider_error: Optional[str] = None
    last_successful_check: Optional[str] = None
    # NOTE: key_id, key_secret, webhook_secret are NEVER included in this response


__all__ = [
    "RazorpayPayment",
    "RazorpayOrder",
    "RazorpayOrderPayments",
    "RazorpayPaymentLink",
    "RazorpayPaymentLinkRequest",
    "RazorpayWebhookEvent",
    "RazorpayWebhookPaymentEntity",
    "RazorpayWebhookOrderEntity",
    "RazorpayWebhookPayload",
    "RazorpayError",
    "RazorpayErrorDetail",
    "RazorpayProviderStatus",
]
