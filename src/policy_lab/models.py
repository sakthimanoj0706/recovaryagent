"""
Data Models and Schemas for RecoverAI Policy Lab & What-If Economic Simulator (Step 12).

Defines strongly typed, validated Pydantic models for:
- EconomicEnvironment (custom unit economics & costs)
- CustomRecoveryPolicy (deterministic customizable recovery policy)
- PolicyComparison & StrategyResult (3-way comparison between Naive, RecoverAI, and Custom Policy)
- SensitivityPoint & SensitivityResult (one-parameter sweep analytics)
- BreakEvenRequest & BreakEvenResult (crossover discovery)
- MonteCarloConfig & MonteCarloResult (multi-seed stochastic validation)
- PolicyLabRunResult (complete auditable run object)
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EconomicEnvironment(BaseModel):
    """
    Configurable macroeconomic and merchant unit cost parameters.
    All monetary units in INR (Rs.).
    """
    model_config = ConfigDict(extra="allow")

    retry_cost: float = Field(default=0.50, ge=0.0, description="Cost per automated retry attempt via gateway (Rs.)")
    customer_contact_cost: float = Field(default=0.25, ge=0.0, description="Communication & notification dispatch cost (Rs.)")
    payment_link_cost: float = Field(default=1.50, ge=0.0, description="Cost to create & dispatch dynamic payment link (Rs.)")
    chargeback_cost: float = Field(default=250.00, ge=0.0, description="Direct cost of dispute, chargeback, or customer support from double charging (Rs.)")
    scheme_penalty: float = Field(default=15.00, ge=0.0, description="Card network/scheme penalty fee for retrying hard declines (Rs.)")
    manual_escalation_cost: float = Field(default=50.00, ge=0.0, description="Operations overhead per manual reconciliation review (Rs.)")

    recovery_probability_multiplier: float = Field(
        default=1.0,
        ge=0.05,
        le=3.0,
        description="Global market conversion factor multiplier (0.05 to 3.0)"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Global ceiling on automated retries")
    high_value_threshold: float = Field(default=25000.0, ge=0.0, description="Ticket size threshold for high-value priority handling (Rs.)")
    risk_tolerance: str = Field(default="MEDIUM", description="Merchant risk appetite: LOW, MEDIUM, or HIGH")
    payment_population: int = Field(default=1000, ge=10, le=50000, description="Synthetic payment population size to simulate")
    random_seed: int = Field(default=42, description="Deterministic pseudo-random seed for 100% reproducibility")

    @field_validator("risk_tolerance")
    @classmethod
    def validate_risk_tolerance(cls, v: str) -> str:
        val = v.upper().strip()
        if val not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError(f"risk_tolerance must be 'LOW', 'MEDIUM', or 'HIGH', got '{v}'")
        return val


class CustomRecoveryPolicy(BaseModel):
    """
    Deterministic custom policy definition for fintech operators.
    Can never bypass deterministic FinancialStateEngine, RecoveryFirewall, or RecoveryVerifier.
    """
    model_config = ConfigDict(extra="allow")

    name: str = Field(default="Custom Policy", description="Descriptive name of the custom policy")
    max_retries: int = Field(default=2, ge=0, le=10, description="Maximum automated gateway retry attempts")
    enable_retry: bool = Field(default=True, description="Enable automated gateway retries on soft transient failures")
    enable_payment_link: bool = Field(default=True, description="Enable dynamic checkout links")
    enable_reminder: bool = Field(default=True, description="Enable gentle customer notifications")
    enable_escalation: bool = Field(default=True, description="Enable ops queue escalation for exceptions")
    high_value_threshold: float = Field(default=25000.0, ge=0.0, description="Threshold above which payments are escalated or prioritized (Rs.)")
    min_expected_net_value: float = Field(default=0.0, description="Minimum Expected Net Value required to pursue recovery (Rs.)")
    preferred_channel: str = Field(default="auto", description="Preferred contact channel: 'auto', 'whatsapp', 'sms', 'email', 'gateway'")
    escalate_on_exception: bool = Field(default=True, description="Immediately escalate ledger/reconciliation exceptions")
    escalate_on_high_value: bool = Field(default=False, description="Automatically escalate all transactions above high_value_threshold")
    risk_tolerance: str = Field(default="MEDIUM", description="Policy risk tolerance tier: 'LOW', 'MEDIUM', 'HIGH'")

    @field_validator("risk_tolerance")
    @classmethod
    def validate_risk_tolerance(cls, v: str) -> str:
        val = v.upper().strip()
        if val not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError(f"risk_tolerance must be 'LOW', 'MEDIUM', or 'HIGH', got '{v}'")
        return val


class ActionExplanation(BaseModel):
    """Transparent mathematical breakdown of expected economic value per action."""
    action: str
    probability: float
    expected_gross: float
    action_cost: float
    expected_risk: float
    expected_net_value: float
    decision: str
    reason: str


class PolicyComparison(BaseModel):
    """
    Side-by-side 3-strategy comparative analysis.
    """
    model_config = ConfigDict(extra="allow")

    comparison_id: str
    timestamp: str
    simulation_label: str = "SYNTHETIC BENCHMARK — NOT REAL PAYMENT DATA"
    env: EconomicEnvironment
    custom_policy: CustomRecoveryPolicy

    # Strategy metrics (reusing StrategyMetrics from benchmark.models)
    naive: Any
    recoverai: Any
    custom: Any

    best_strategy: str = "RECOVERAI"
    best_legitimate_value: float = 0.0

    # Comparative lift deltas
    deltas: Dict[str, Any] = Field(default_factory=dict)
    executive_summary: str = ""
    why_winner_won: List[str] = Field(default_factory=list)


class SensitivityPoint(BaseModel):
    """A single evaluation point in a sensitivity parameter sweep."""
    parameter_value: float
    naive_net_value: float
    recoverai_net_value: float
    custom_net_value: float
    recoverai_lift_percent: float
    custom_lift_percent: float
    naive_safety_violations: int = 0
    recoverai_safety_violations: int = 0
    custom_safety_violations: int = 0
    naive_unnecessary_actions: int = 0
    recoverai_unnecessary_actions: int = 0
    custom_unnecessary_actions: int = 0


class SensitivityRequest(BaseModel):
    """Request payload for one-parameter sensitivity analysis."""
    parameter_name: str = Field(default="retry_cost", description="Parameter to vary: 'retry_cost', 'customer_contact_cost', 'chargeback_cost', 'scheme_penalty', 'recovery_probability_multiplier', 'max_retries'")
    parameter_values: Optional[List[float]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    steps: int = Field(default=6, ge=2, le=20)
    env: EconomicEnvironment = Field(default_factory=EconomicEnvironment)
    custom_policy: CustomRecoveryPolicy = Field(default_factory=CustomRecoveryPolicy)


class SensitivityResult(BaseModel):
    """Complete results from a sensitivity analysis parameter sweep."""
    parameter_name: str
    points: List[SensitivityPoint]
    summary: str
    disclaimer: str = "Synthetic simulation. Not real-world production performance."


class BreakEvenRequest(BaseModel):
    """Request payload for economic break-even search."""
    parameter_name: str = Field(default="retry_cost", description="Parameter to search across for break-even")
    search_min: float = Field(default=0.0, ge=0.0)
    search_max: float = Field(default=500.0, ge=0.0)
    tolerance: float = Field(default=1.0, ge=0.001)
    env: EconomicEnvironment = Field(default_factory=EconomicEnvironment)
    custom_policy: CustomRecoveryPolicy = Field(default_factory=CustomRecoveryPolicy)


class BreakEvenResult(BaseModel):
    """Deterministic result of break-even search."""
    parameter_name: str
    break_even_found: bool
    break_even_value: Optional[float] = None
    naive_value: Optional[float] = None
    recoverai_value: Optional[float] = None
    search_range: Tuple[float, float]
    explanation: str


class MonteCarloConfig(BaseModel):
    """Configuration for multi-run Monte Carlo simulation."""
    runs: int = Field(default=50, ge=2, le=500, description="Number of independent synthetic runs")
    starting_seed: int = Field(default=42, description="Starting seed for sequence (seed, seed+1, ...)")
    population_per_run: int = Field(default=500, ge=10, le=5000, description="Synthetic payments per run")
    env: EconomicEnvironment = Field(default_factory=EconomicEnvironment)
    custom_policy: CustomRecoveryPolicy = Field(default_factory=CustomRecoveryPolicy)


class MonteCarloResult(BaseModel):
    """Aggregated statistical outcome across multiple synthetic Monte Carlo runs."""
    total_runs: int
    starting_seed: int
    population_per_run: int

    mean_recoverai_lift_pct: float
    median_recoverai_lift_pct: float
    std_recoverai_lift_pct: float
    min_recoverai_lift_pct: float
    max_recoverai_lift_pct: float
    confidence_interval_95: Tuple[float, float]

    mean_custom_lift_pct: float
    median_custom_lift_pct: float

    mean_naive_safety_violations: float
    mean_recoverai_safety_violations: float
    mean_custom_safety_violations: float
    mean_unnecessary_actions_saved: float
    accounting_imbalance_all_zero: bool
    disclaimer: str = "Synthetic simulation. Not real-world production performance."


class PolicyLabRunResult(BaseModel):
    """Complete auditable record of a Policy Lab simulation run."""
    run_id: str
    timestamp: str
    env: EconomicEnvironment
    custom_policy: CustomRecoveryPolicy
    comparison: PolicyComparison
    simulation_flag: bool = True
