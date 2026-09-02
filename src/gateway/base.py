"""
Abstract Base Interface for Payment Gateway Adapters in RecoverAI.
Guarantees provider independence across Mock, Sandbox, and Future Gateway providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .models import GatewayActionResult, PaymentStatusResult
from state_engine.models import Event


class PaymentGateway(ABC):
    """
    Provider-independent gateway contract for executing recovery actions.
    
    SAFETY PRINCIPLE:
    Gateways only execute approved actions and return execution results.
    Gateways NEVER decide:
    - FinancialState
    - RecoveryDecision
    - FirewallDecision
    - VerificationState
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider name identifier (e.g. 'mock', 'razorpay')."""
        pass

    @property
    @abstractmethod
    def is_simulation(self) -> bool:
        """Indicate whether the gateway runs in simulated / sandbox mode."""
        pass

    @abstractmethod
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
        """Generate a fresh payment checkout link for an unrecovered payment."""
        pass

    @abstractmethod
    def create_checkout_order(
        self,
        payment_id: str,
        amount: float,
        currency: str = "INR",
        receipt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        """Generate a provider order specifically for frontend standard web checkout."""
        pass

    @abstractmethod
    def retry_payment(
        self,
        payment_id: str,
        amount: float,
        order_id: Optional[str] = None,
        method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        """Dispatch automated direct retry on the payment rail."""
        pass

    @abstractmethod
    def send_reminder(
        self,
        payment_id: str,
        amount: float,
        channel: str = "whatsapp",
        order_id: Optional[str] = None,
        customer_contact: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GatewayActionResult:
        """Dispatch customer notification reminder across the specified channel."""
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> PaymentStatusResult:
        """Query gateway status for a specific payment ID."""
        pass

    @abstractmethod
    def get_payment_events(self, payment_id: str) -> List[Event]:
        """Fetch all recorded gateway events for a specific payment."""
        pass

    @abstractmethod
    def cancel_action(self, payment_id: str, execution_id: str) -> GatewayActionResult:
        """Cancel an in-flight recovery action or payment link."""
        pass
