from typing import List, Optional
from state_engine import FinancialState, Event
from .models import FailureClassification, FailureType

class DeterministicFailureClassifier:
    """Deterministically classify failures based on financial state and events."""
    
    @staticmethod
    def classify(financial_state: str, events: List[Event]) -> FailureClassification:
        # Determine failure reason from events
        fail_events = [e for e in events if e.event == "payment.failed"]
        last_fail = fail_events[-1] if fail_events else None
        
        err_code = ""
        hardness = ""
        if last_fail:
            err_code = str(last_fail.error_code or "").upper()
            hardness = str(last_fail.hardness or "").lower()

        # Conflicting state check
        auth_events = [e for e in events if e.event in ("payment.authorized", "payment.captured")]
        if auth_events and last_fail and getattr(auth_events[-1], 'ts', '') > getattr(last_fail, 'ts', ''):
            return FailureClassification(
                failure_type=FailureType.CONFLICTING_STATE,
                confidence=1.0,
                reason="Authorized after failure",
                is_recoverable=False
            )
            
        if financial_state == "ALREADY_RECOVERED":
            return FailureClassification(
                failure_type=FailureType.ALREADY_CAPTURED,
                confidence=1.0,
                reason="State is ALREADY_RECOVERED",
                is_recoverable=False
            )
        elif financial_state == "REFUNDED":
            return FailureClassification(
                failure_type=FailureType.ALREADY_REFUNDED,
                confidence=1.0,
                reason="State is REFUNDED",
                is_recoverable=False
            )
        elif financial_state == "PARTIAL":
            return FailureClassification(
                failure_type=FailureType.PARTIAL_CAPTURE,
                confidence=1.0,
                reason="State is PARTIAL",
                is_recoverable=True
            )
        elif financial_state == "UNCERTAIN":
            return FailureClassification(
                failure_type=FailureType.VERIFICATION_PENDING,
                confidence=1.0,
                reason="State is UNCERTAIN (verification pending)",
                is_recoverable=False
            )

        if not fail_events:
            return FailureClassification(
                failure_type=FailureType.UNKNOWN_FAILURE,
                confidence=0.0,
                reason="No failure events found",
                is_recoverable=True
            )

        # Classification based on error code
        if "INSUFFICIENT" in err_code or "FUNDS" in err_code or err_code == "BAD_REQUEST_ERROR":
            return FailureClassification(
                failure_type=FailureType.INSUFFICIENT_FUNDS,
                confidence=0.9,
                reason=f"Error code indicates insufficient funds: {err_code}",
                is_recoverable=True
            )
        elif "EXPIRED" in err_code or "CARD_EXPIRED" in err_code:
            return FailureClassification(
                failure_type=FailureType.EXPIRED_PAYMENT_METHOD,
                confidence=0.9,
                reason=f"Error code indicates expired method: {err_code}",
                is_recoverable=False # Usually need a new method (payment link)
            )
        elif "CANCELLED" in err_code or "ABANDONED" in err_code:
            return FailureClassification(
                failure_type=FailureType.CUSTOMER_ABANDONMENT,
                confidence=0.9,
                reason=f"Error code indicates customer abandonment: {err_code}",
                is_recoverable=True
            )
        elif hardness == "hard":
            return FailureClassification(
                failure_type=FailureType.HARD_DECLINE,
                confidence=1.0,
                reason=f"Provider indicated hard decline: {err_code}",
                is_recoverable=False
            )
        else:
            return FailureClassification(
                failure_type=FailureType.TRANSIENT_FAILURE,
                confidence=0.8,
                reason=f"Assumed transient failure based on soft decline: {err_code}",
                is_recoverable=True
            )
