from typing import List, Dict, Any, Optional
from .models import CandidateAction, FailureClassification, FailureType
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from state_engine import PaymentRecord, Event

class DeterministicCandidateGenerator:
    """Generates and evaluates candidate actions."""
    
    def __init__(self, model: Optional[RecoveryProbabilityModel] = None, config: Optional[RecoveryCostConfig] = None):
        self.model = model or RecoveryProbabilityModel()
        self.config = config or RecoveryCostConfig()

    def generate(
        self,
        payment: PaymentRecord,
        events: List[Event],
        classification: FailureClassification,
        retry_count: int
    ) -> List[CandidateAction]:
        
        candidates = []
        amount = float(payment.amount or 0.0)
        from recovery.features import extract_payment_features
        feats = extract_payment_features(payment, events)
        # Base probability from the ML model
        base_prob = float(self.model.predict_probability(feats))
        
        # Evaluate RETRY
        retry_eligible = True
        retry_reason = None
        if not classification.is_recoverable:
            retry_eligible = False
            retry_reason = f"Classification {classification.failure_type.name} is not recoverable via RETRY."
        elif retry_count >= getattr(self.config, 'max_retries', 3):
            retry_eligible = False
            retry_reason = "Max retries reached."
            
        retry_prob = base_prob * 0.9 if retry_eligible else 0.0 # slight decay
        retry_gross = retry_prob * amount
        retry_cost = getattr(self.config, 'gateway_attempt_cost', getattr(self.config, 'retry_cost', 0.5))
        retry_risk = 0.0 # basic retry has no chargeback risk unless hard decline
        if classification.failure_type == FailureType.HARD_DECLINE:
            retry_risk = getattr(self.config, 'hard_decline_penalty_cost', getattr(self.config, 'friction_cost', 15.0))
            
        retry_net = retry_gross - retry_cost - retry_risk
        
        candidates.append(CandidateAction(
            action="RETRY",
            is_eligible=retry_eligible,
            expected_recovery_probability=retry_prob,
            expected_gross_recovery=retry_gross,
            operational_cost=retry_cost,
            risk_penalty=retry_risk,
            expected_net_value=retry_net if retry_eligible else -9999.0,
            explanation="Standard payment gateway retry.",
            rejection_reason=retry_reason
        ))

        # Evaluate PAYMENT_LINK
        pl_prob = base_prob * 0.75 # Requires customer action
        pl_gross = pl_prob * amount
        pl_cost = getattr(self.config, 'payment_link_cost', getattr(self.config, 'intervention_cost', 1.5))
        pl_net = pl_gross - pl_cost
        
        candidates.append(CandidateAction(
            action="PAYMENT_LINK",
            is_eligible=True,
            expected_recovery_probability=pl_prob,
            expected_gross_recovery=pl_gross,
            operational_cost=pl_cost,
            risk_penalty=0.0,
            expected_net_value=pl_net,
            explanation="Send a new payment link to the customer.",
        ))

        # Evaluate REMINDER
        rem_prob = base_prob * 0.4
        rem_gross = rem_prob * amount
        rem_cost = getattr(self.config, 'customer_contact_cost', getattr(self.config, 'intervention_cost', 0.25))
        rem_net = rem_gross - rem_cost
        
        candidates.append(CandidateAction(
            action="REMINDER",
            is_eligible=True,
            expected_recovery_probability=rem_prob,
            expected_gross_recovery=rem_gross,
            operational_cost=rem_cost,
            risk_penalty=0.0,
            expected_net_value=rem_net,
            explanation="Send a gentle reminder to the customer.",
        ))

        # Evaluate ESCALATE
        esc_cost = getattr(self.config, 'manual_escalation_cost', getattr(self.config, 'friction_cost', 50.0))
        esc_net = -esc_cost # Escalation usually just incurs cost and manual review
        
        candidates.append(CandidateAction(
            action="ESCALATE",
            is_eligible=True,
            expected_recovery_probability=0.0,
            expected_gross_recovery=0.0,
            operational_cost=esc_cost,
            risk_penalty=0.0,
            expected_net_value=esc_net,
            explanation="Escalate to human operations.",
        ))

        # Evaluate STOP
        candidates.append(CandidateAction(
            action="STOP",
            is_eligible=True,
            expected_recovery_probability=0.0,
            expected_gross_recovery=0.0,
            operational_cost=0.0,
            risk_penalty=0.0,
            expected_net_value=0.0,
            explanation="Halt recovery efforts to prevent further costs.",
        ))

        return candidates
