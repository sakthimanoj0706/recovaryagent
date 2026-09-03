"""
Step 20 — Production Observability Models.

Structured event envelopes with correlation, tracing, and latency fields.
Never logs secrets. Redacts sensitive fields.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class OperationType(str, Enum):
    REQUEST = "REQUEST"
    PAYMENT = "PAYMENT"
    DECISION = "DECISION"
    ACTION = "ACTION"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    OUTCOME = "OUTCOME"
    POLICY = "POLICY"
    FIREWALL = "FIREWALL"
    LLM = "LLM"
    LEARNING = "LEARNING"
    DRIFT = "DRIFT"
    EXPERIMENT = "EXPERIMENT"
    CHALLENGER = "CHALLENGER"
    PROMOTION = "PROMOTION"
    ROLLBACK = "ROLLBACK"
    HEALTH = "HEALTH"
    CONFIGURATION = "CONFIGURATION"


class OperationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"


class ObservabilityEvent(BaseModel):
    """Structured observability event for every important operation."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    correlation_id: str
    request_id: Optional[str] = None
    payment_id: Optional[str] = None
    decision_id: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    operation: OperationType
    status: OperationStatus
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class DecisionTrace(BaseModel):
    """End-to-end correlation trace for a single payment recovery decision."""
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:16]}")
    correlation_id: str
    payment_id: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    total_latency_ms: Optional[float] = None

    # Stages
    raw_event: Optional[Dict[str, Any]] = None
    normalization: Optional[Dict[str, Any]] = None
    financial_state: Optional[Dict[str, Any]] = None
    failure_classification: Optional[Dict[str, Any]] = None
    recovery_opportunity: Optional[Dict[str, Any]] = None
    candidate_generation: Optional[Dict[str, Any]] = None
    economic_ranking: Optional[Dict[str, Any]] = None
    llm_advisory: Optional[Dict[str, Any]] = None
    policy_decision: Optional[Dict[str, Any]] = None
    firewall_decision: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    independent_verification: Optional[Dict[str, Any]] = None
    final_financial_state: Optional[Dict[str, Any]] = None
    outcome: Optional[Dict[str, Any]] = None
    economic_result: Optional[Dict[str, Any]] = None

    # Evidence reference
    evidence_graph_id: Optional[str] = None
    replay_id: Optional[str] = None

    def summary(self) -> str:
        stages_complete = sum(1 for s in [
            self.raw_event, self.normalization, self.financial_state,
            self.failure_classification, self.recovery_opportunity,
            self.candidate_generation, self.economic_ranking, self.llm_advisory,
            self.policy_decision, self.firewall_decision, self.execution,
            self.independent_verification, self.final_financial_state,
            self.outcome, self.economic_result
        ] if s is not None)
        return f"trace_id={self.trace_id} payment_id={self.payment_id} stages={stages_complete}/15 latency={self.total_latency_ms}ms"


class HealthStatus(str, Enum):
    HEALTHY = "APPLICATION_HEALTHY"
    DEGRADED = "APPLICATION_DEGRADED"
    UNHEALTHY = "APPLICATION_UNHEALTHY"


class DependencyClass(str, Enum):
    CRITICAL = "CRITICAL"
    NON_CRITICAL = "NON_CRITICAL"


class DependencyHealth(BaseModel):
    name: str
    dependency_class: DependencyClass
    status: str  # "OK" | "DEGRADED" | "UNAVAILABLE"
    detail: Optional[str] = None
    latency_ms: Optional[float] = None


class SystemHealthReport(BaseModel):
    """Comprehensive system health report."""
    report_id: str = Field(default_factory=lambda: f"health_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    overall_status: HealthStatus
    dependencies: List[DependencyHealth] = Field(default_factory=list)
    critical_failures: List[str] = Field(default_factory=list)
    non_critical_failures: List[str] = Field(default_factory=list)

    # Financial safety invariants (always checked)
    phantom_revenue: float = 0.0
    duplicate_recovery: int = 0
    accounting_imbalance: float = 0.0
    unsafe_executions: int = 0

    # Core safety flags
    financial_state_engine_ok: bool = True
    policy_engine_ok: bool = True
    firewall_ok: bool = True
    verification_ok: bool = True

    # Non-critical
    learning_ok: bool = True
    llm_ok: bool = True
    metrics_ok: bool = True

    def is_safe_to_execute(self) -> bool:
        """Returns True only if all CRITICAL dependencies are healthy."""
        return (
            self.financial_state_engine_ok
            and self.policy_engine_ok
            and self.firewall_ok
            and self.verification_ok
        )


class LatencyMetrics(BaseModel):
    """Latency percentile metrics for a named operation."""
    operation: str
    sample_count: int
    p50_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    p99_ms: Optional[float] = None
    min_ms: Optional[float] = None
    max_ms: Optional[float] = None
    mean_ms: Optional[float] = None
    status: str = "OK"  # "OK" | "INSUFFICIENT_DATA"

    MINIMUM_SAMPLES: int = 5

    @classmethod
    def insufficient(cls, operation: str) -> "LatencyMetrics":
        return cls(operation=operation, sample_count=0, status="INSUFFICIENT_DATA")
