"""
Economic calculations and Expected Net Value (ENV) engine for RecoverAI.

Implements:
Expected Gross Recovery = P(success) * amount
Expected Net Value = Expected Gross Recovery - retry_cost - intervention_cost - friction_cost
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RecoveryCostConfig(BaseModel):
    """
    Configurable unit economics for recovery intervention.
    All values represent operational cost estimates (e.g., INR ₹ or USD $).
    """
    model_config = ConfigDict(extra="allow")

    retry_cost: float = Field(default=20.0, description="Cost of automated payment gateway re-attempt API call")
    intervention_cost: float = Field(default=10.0, description="Cost of customer communication (SMS, WhatsApp, email)")
    friction_cost: float = Field(default=50.0, description="Buffer for user UX friction, support overhead, and dispute risk")

    @property
    def total_cost(self) -> float:
        return self.retry_cost + self.intervention_cost + self.friction_cost


class EconomicEvaluation(BaseModel):
    """
    Detailed economic breakdown for a recovery candidate.
    """
    model_config = ConfigDict(extra="allow")

    amount: float
    probability: float
    expected_gross_recovery: float
    retry_cost: float
    intervention_cost: float
    friction_cost: float
    total_cost: float
    expected_net_value: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "probability": round(self.probability, 4),
            "expected_gross_recovery": round(self.expected_gross_recovery, 2),
            "retry_cost": round(self.retry_cost, 2),
            "intervention_cost": round(self.intervention_cost, 2),
            "friction_cost": round(self.friction_cost, 2),
            "total_cost": round(self.total_cost, 2),
            "expected_net_value": round(self.expected_net_value, 2),
        }


def calculate_expected_net_value(
    amount: float,
    probability: float,
    config: Optional[RecoveryCostConfig] = None,
) -> EconomicEvaluation:
    """
    Calculate Expected Gross Recovery and Expected Net Value given transaction amount,
    predicted probability, and cost parameters.
    """
    cfg = config or RecoveryCostConfig()
    amt = max(0.0, float(amount))
    prob = max(0.0, min(1.0, float(probability)))

    expected_gross = amt * prob
    total_cost = cfg.total_cost
    expected_net = expected_gross - total_cost

    return EconomicEvaluation(
        amount=round(amt, 2),
        probability=round(prob, 4),
        expected_gross_recovery=round(expected_gross, 2),
        retry_cost=round(cfg.retry_cost, 2),
        intervention_cost=round(cfg.intervention_cost, 2),
        friction_cost=round(cfg.friction_cost, 2),
        total_cost=round(total_cost, 2),
        expected_net_value=round(expected_net, 2),
    )
