"""
Data Models and Types for the RecoverAI Economic Benchmark and ROI Engine.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict


class BenchmarkArchetype(str, Enum):
    """Synthetic financial lifecycle archetypes."""
    SUCCESS = "SUCCESS"
    SOFT_FAILURE = "SOFT_FAILURE"
    HARD_DECLINE = "HARD_DECLINE"
    ALREADY_RECOVERED = "ALREADY_RECOVERED"
    UNCERTAIN = "UNCERTAIN"
    EXCEPTION = "EXCEPTION"
    PARTIAL_CAPTURE = "PARTIAL_CAPTURE"
    REFUNDED = "REFUNDED"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    TIMEOUT = "TIMEOUT"
    LATE_CAPTURE = "LATE_CAPTURE"


class CostModelConfig(BaseModel):
    """
    Configurable unit cost model for payment recovery operations.
    All figures in INR (₹). Configurable per merchant economics.
    """
    model_config = ConfigDict(extra="allow")

    gateway_attempt_cost: float = Field(default=0.50, description="Cost per automated retry attempt via gateway")
    payment_link_cost: float = Field(default=1.50, description="Cost to generate & dispatch dynamic checkout link (SMS/WhatsApp/Email)")
    customer_contact_cost: float = Field(default=0.25, description="Notification & communication platform delivery cost")
    manual_escalation_cost: float = Field(default=50.00, description="Operations team manual review/reconciliation overhead")
    hard_decline_penalty_cost: float = Field(default=15.00, description="Estimated scheme/network penalty & risk surcharge for retrying hard declines")
    double_recovery_chargeback_cost: float = Field(default=250.00, description="Estimated dispute, chargeback, and customer support cost from double-charging")


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark simulation run."""
    model_config = ConfigDict(extra="allow")

    payments: int = Field(default=10000, description="Total synthetic payment lifecycles to simulate")
    seed: int = Field(default=42, description="Deterministic pseudo-random seed for 100% reproducibility")
    costs: CostModelConfig = Field(default_factory=CostModelConfig)
    
    # Archetype weights (approximate realistic distribution)
    archetype_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "SUCCESS": 0.35,
            "SOFT_FAILURE": 0.22,
            "HARD_DECLINE": 0.10,
            "ALREADY_RECOVERED": 0.10,
            "UNCERTAIN": 0.05,
            "EXCEPTION": 0.03,
            "PARTIAL_CAPTURE": 0.03,
            "REFUNDED": 0.03,
            "DUPLICATE": 0.03,
            "OUT_OF_ORDER": 0.03,
            "TIMEOUT": 0.02,
            "LATE_CAPTURE": 0.01,
        }
    )


class StrategyMetrics(BaseModel):
    """
    Comprehensive financial, operational, and safety metrics for a recovery strategy.
    """
    model_config = ConfigDict(extra="allow")

    strategy_name: str
    total_payments: int = 0
    total_payment_value: float = 0.0

    # Operational metrics
    recovery_opportunities: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    unnecessary_actions: int = 0

    # Safety and protection metrics
    duplicate_actions_prevented: int = 0
    hard_decline_retries_prevented: int = 0
    hard_decline_retried_count: int = 0
    already_recovered_protected: int = 0
    false_recovery_claims: int = 0
    double_charge_events: int = 0


    # Volume of infrastructure actions
    gateway_operations: int = 0
    customer_contact_actions: int = 0

    # Financial accounting buckets (INR)
    gross_recovered_value: float = 0.0
    claimed_recovered_value: float = 0.0
    false_recovery_value: float = 0.0
    real_verified_value: float = 0.0
    protected_value: float = 0.0
    amount_withheld: float = 0.0
    amount_pending: float = 0.0
    amount_escalated: float = 0.0
    
    # Costs & Net Value
    total_operating_cost: float = 0.0
    scheme_penalty_losses: float = 0.0
    dispute_chargeback_losses: float = 0.0
    prevented_penalty_losses: float = 0.0
    net_recovery_value: float = 0.0
    net_legitimate_value: float = 0.0


    # ROI and Unit Economic Ratios
    roi_percentage: float = 0.0
    cost_per_recovered_rupee: float = 0.0
    cost_per_successful_recovery: float = 0.0
    recovery_success_rate: float = 0.0

    # Safety Violation Rates (0.0 to 1.0)
    false_recovery_rate: float = 0.0
    double_recovery_rate: float = 0.0
    unnecessary_action_rate: float = 0.0
    hard_decline_retry_rate: float = 0.0
    already_recovered_action_rate: float = 0.0
    accounting_imbalance: float = 0.0

    # Statistical Distributions
    mean_ticket_size: float = 0.0
    median_ticket_size: float = 0.0
    std_ticket_size: float = 0.0
    recovered_mean: float = 0.0
    recovered_std: float = 0.0
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)


class BenchmarkComparison(BaseModel):
    """
    Side-by-side comparison between Naive Recovery Baseline and RecoverAI.
    """
    model_config = ConfigDict(extra="allow")

    benchmark_id: str
    timestamp: str
    config: BenchmarkConfig
    simulation_label: str = "SYNTHETIC BENCHMARK — NOT REAL PAYMENT DATA"

    naive: StrategyMetrics
    recoverai: StrategyMetrics

    # Improvement Deltas
    recovered_value_lift_pct: float = 0.0
    net_value_lift_amount: float = 0.0
    net_value_lift_pct: float = 0.0
    unnecessary_actions_reduction_pct: float = 0.0
    gateway_operations_reduction_pct: float = 0.0
    operating_cost_reduction_pct: float = 0.0
    false_recoveries_eliminated: int = 0
    double_recoveries_prevented: int = 0

    # Machine-readable Executive Insights
    executive_summary: str
    key_findings: List[str]
    archetype_breakdown: Dict[str, int]
