"""
Recovery Decision Engine for RecoverAI.

Enforces the strict safety gate:
Only VERIFIED_LOST payments from the Financial State Engine are eligible for recovery modeling.
All non-lost states (ALREADY_RECOVERED, UNCERTAIN, EXCEPTION) are strictly rejected.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

try:
    from ..state_engine.models import FinancialState, PaymentRecord, Event
    from ..state_engine.engine import FinancialStateEngine
except (ImportError, ValueError):
    try:
        from state_engine.models import FinancialState, PaymentRecord, Event
        from state_engine.engine import FinancialStateEngine
    except ImportError:
        from src.state_engine.models import FinancialState, PaymentRecord, Event
        from src.state_engine.engine import FinancialStateEngine

from .features import extract_payment_features
from .model import RecoveryProbabilityModel
from .economics import RecoveryCostConfig, EconomicEvaluation, calculate_expected_net_value


class RecoveryDecision(str, Enum):
    """Economic decision for a verified lost payment."""
    RECOVERY_WORTHWHILE = "RECOVERY_WORTHWHILE"
    DO_NOT_RECOVER = "DO_NOT_RECOVER"
    INELIGIBLE_STATE = "INELIGIBLE_STATE"


class RecoveryDecisionResult(BaseModel):
    """
    Structured outcome of the recovery intelligence evaluation.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    order_id: Optional[str] = None
    financial_state: str
    recovery_probability: Optional[float] = None
    amount: float
    expected_gross_recovery: Optional[float] = None
    retry_cost: Optional[float] = None
    intervention_cost: Optional[float] = None
    friction_cost: Optional[float] = None
    expected_net_value: Optional[float] = None
    decision: RecoveryDecision
    reason: str
    explanation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "financial_state": self.financial_state,
            "recovery_probability": self.recovery_probability,
            "amount": self.amount,
            "expected_gross_recovery": self.expected_gross_recovery,
            "retry_cost": self.retry_cost,
            "intervention_cost": self.intervention_cost,
            "friction_cost": self.friction_cost,
            "expected_net_value": self.expected_net_value,
            "decision": self.decision.value if isinstance(self.decision, RecoveryDecision) else str(self.decision),
            "reason": self.reason,
            "explanation": self.explanation,
        }


class RecoveryDecisionEngine:
    """
    End-to-end Recovery Intelligence orchestrator.
    Gates inference through the Financial State Engine before applying ML + Economics.
    """

    def __init__(
        self,
        model: RecoveryProbabilityModel,
        cost_config: Optional[RecoveryCostConfig] = None,
        state_engine: Optional[FinancialStateEngine] = None,
    ):
        self.model = model
        self.cost_config = cost_config or RecoveryCostConfig()
        self.state_engine = state_engine or FinancialStateEngine()

    def evaluate_payment(
        self,
        payment: PaymentRecord,
        events: List[Event],
        order_events: Optional[List[Event]] = None,
        precomputed_state: Optional[FinancialState] = None,
    ) -> RecoveryDecisionResult:
        """
        Evaluate recovery eligibility, probability, unit economics, and recommendation.
        """
        # Step 1: Determine / verify financial state
        if precomputed_state is not None:
            fin_state = precomputed_state
        else:
            state_result = self.state_engine.evaluate_payment(payment, events, order_events)
            fin_state = state_result.state

        state_str = fin_state.value if isinstance(fin_state, FinancialState) else str(fin_state)
        amt = float(payment.amount) if payment.amount is not None else 0.0

        # Step 2: Strict Safety Gate: Only VERIFIED_LOST can proceed to ML
        if fin_state != FinancialState.VERIFIED_LOST:
            return RecoveryDecisionResult(
                payment_id=payment.payment_id,
                order_id=payment.order_id,
                financial_state=state_str,
                recovery_probability=None,
                amount=amt,
                expected_gross_recovery=None,
                retry_cost=None,
                intervention_cost=None,
                friction_cost=None,
                expected_net_value=None,
                decision=RecoveryDecision.INELIGIBLE_STATE,
                reason=(
                    f"Recovery evaluation rejected: Financial state is '{state_str}'. "
                    f"Only VERIFIED_LOST payments are eligible for recovery modeling."
                ),
                explanation=None,
            )

        # Step 3: Feature Extraction & ML Probability
        features = extract_payment_features(payment, events)
        prob = float(self.model.predict_probability(features))
        explanation = self.model.explain(features)

        # Step 4: Expected Net Value Calculation
        econ = calculate_expected_net_value(amount=amt, probability=prob, config=self.cost_config)

        # Step 5: Economic Decision Rule
        if econ.expected_net_value > 0.0:
            decision = RecoveryDecision.RECOVERY_WORTHWHILE
            reason = (
                f"Recovery is economically worthwhile with Expected Net Value of Rs. {econ.expected_net_value:,.2f} "
                f"(Gross: Rs. {econ.expected_gross_recovery:,.2f} vs Costs: Rs. {econ.total_cost:,.2f} at {prob*100:.1f}% win rate)."
            )
        else:
            decision = RecoveryDecision.DO_NOT_RECOVER
            reason = (
                f"Recovery is not economically viable: Expected Net Value is Rs. {econ.expected_net_value:,.2f} "
                f"(Gross: Rs. {econ.expected_gross_recovery:,.2f} <= Costs: Rs. {econ.total_cost:,.2f})."
            )

        return RecoveryDecisionResult(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            financial_state=state_str,
            recovery_probability=round(prob, 4),
            amount=econ.amount,
            expected_gross_recovery=econ.expected_gross_recovery,
            retry_cost=econ.retry_cost,
            intervention_cost=econ.intervention_cost,
            friction_cost=econ.friction_cost,
            expected_net_value=econ.expected_net_value,
            decision=decision,
            reason=reason,
            explanation=explanation,
        )
