"""
Data Models and Schemas for RecoverAI Recovery Decision Replay & Evidence Graph (Step 13).

Provides strongly typed, validated Pydantic models for:
- EvidenceNode (provenance records for each financial/agentic decision point)
- EvidenceEdge (semantic causal relationships between evidence nodes)
- EvidenceGraph (cryptographically hashed, tamper-evident DAG)
- ActionCandidateEvaluation (comparative expected net value matrix)
- FinancialProof (accounting conservation and verified cash proof)
- DecisionProvenance (deterministic why-acted vs why-blocked explanations)
- ReplayRequest & RecoveryDecisionReplay (complete auditable transaction replay)
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EvidenceSource(str, Enum):
    """Authoritative source for an evidence node."""
    RAW_EVENT = "RAW_EVENT"
    LEDGER = "LEDGER"
    FINANCIAL_STATE_ENGINE = "FINANCIAL_STATE_ENGINE"
    RECOVERY_INTELLIGENCE = "RECOVERY_INTELLIGENCE"
    ECONOMIC_ENGINE = "ECONOMIC_ENGINE"
    LLM_ADVISORY = "LLM_ADVISORY"
    POLICY_ENGINE = "POLICY_ENGINE"
    RECOVERY_FIREWALL = "RECOVERY_FIREWALL"
    ACTION_EXECUTOR = "ACTION_EXECUTOR"
    GATEWAY_ADAPTER = "GATEWAY_ADAPTER"
    RECOVERY_VERIFIER = "RECOVERY_VERIFIER"
    SYSTEM_RULE = "SYSTEM_RULE"


class EvidenceNodeType(str, Enum):
    """Category of decision or state artifact in the evidence graph."""
    RAW_EVENT = "RAW_EVENT"
    NORMALIZED_EVENT = "NORMALIZED_EVENT"
    FINANCIAL_STATE = "FINANCIAL_STATE"
    RECOVERY_OPPORTUNITY = "RECOVERY_OPPORTUNITY"
    LLM_RECOMMENDATION = "LLM_RECOMMENDATION"
    CANDIDATE_ACTION = "CANDIDATE_ACTION"
    ECONOMIC_EVALUATION = "ECONOMIC_EVALUATION"
    POLICY_DECISION = "POLICY_DECISION"
    FIREWALL_DECISION = "FIREWALL_DECISION"
    EXECUTION_DISPATCH = "EXECUTION_DISPATCH"
    GATEWAY_RESPONSE = "GATEWAY_RESPONSE"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    FINAL_FINANCIAL_STATE = "FINAL_FINANCIAL_STATE"
    ECONOMIC_OUTCOME = "ECONOMIC_OUTCOME"
    # Step 14 additions
    RAZORPAY_WEBHOOK = "RAZORPAY_WEBHOOK"
    RAZORPAY_API_RESPONSE = "RAZORPAY_API_RESPONSE"
    PROVIDER_SIGNATURE_VERIFICATION = "PROVIDER_SIGNATURE_VERIFICATION"
    RAZORPAY_EXECUTION = "RAZORPAY_EXECUTION"
    RAZORPAY_VERIFICATION = "RAZORPAY_VERIFICATION"


class EvidenceNode(BaseModel):
    """
    A single verifiable evidence node in the recovery decision chain.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    node_type: EvidenceNodeType
    timestamp: str
    source: EvidenceSource
    title: str
    value: Any
    confidence: str = Field(default="DETERMINISTIC", description="'DETERMINISTIC', 'EXACT', 'CALIBRATED_ML', or 'LLM_ADVISORY'")
    evidence_refs: List[str] = Field(default_factory=list, description="IDs of source nodes/events that substantiate this node")
    explanation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceEdge(BaseModel):
    """
    A directed semantic relationship between two evidence nodes in the decision graph.
    """
    model_config = ConfigDict(extra="allow")

    source_node_id: str
    target_node_id: str
    relationship: str = Field(description="e.g. 'contributes_to', 'proves_state', 'evaluates_candidate', 'approved_by_policy', 'guarded_by_firewall', 'verified_by'")
    description: str


class EvidenceGraph(BaseModel):
    """
    Directed Acyclic Evidence Graph with canonical SHA-256 cryptographic hashing.
    """
    model_config = ConfigDict(extra="allow")

    graph_id: str
    payment_id: str
    timestamp: str
    nodes: List[EvidenceNode] = Field(default_factory=list)
    edges: List[EvidenceEdge] = Field(default_factory=list)
    root_node_ids: List[str] = Field(default_factory=list)
    terminal_node_id: Optional[str] = None
    canonical_hash: str = Field(default="", description="SHA-256 cryptographic digest of canonical graph serialization")
    is_tamper_evident: bool = True


class ActionCandidateEvaluation(BaseModel):
    """
    Side-by-side unit economic and policy evaluation for a single candidate action.
    """
    model_config = ConfigDict(extra="allow")

    action: str
    eligible: bool
    recovery_probability: float
    recoverable_amount: float
    expected_gross: float
    action_cost: float
    expected_risk_loss: float
    expected_net_value: float
    policy_status: str = Field(description="'ALLOW', 'REJECT', or 'BLOCKED'")
    firewall_status: str = Field(description="'ALLOW', 'BLOCK', or 'ESCALATE'")
    selected: bool
    reason: str


class FinancialProof(BaseModel):
    """
    Exact mathematical proof of financial state, verified cash, and accounting balance.
    """
    model_config = ConfigDict(extra="allow")

    initial_state: str
    intermediate_states: List[str] = Field(default_factory=list)
    final_state: str
    total_amount: float
    verified_cash_collected: float = 0.0
    protected_unrecovered_value: float = 0.0
    outstanding_value: float = 0.0
    refunded_value: float = 0.0
    claimed_recovery: float = 0.0
    verified_recovery: float = 0.0
    phantom_revenue: float = 0.0
    double_charges: int = 0
    accounting_imbalance: float = 0.0
    is_accounting_conserved: bool = True


class DecisionProvenance(BaseModel):
    """
    Deterministic human-readable explanation of why RecoverAI acted or was blocked.
    """
    model_config = ConfigDict(extra="allow")

    headline: str
    why_selected: List[str] = Field(default_factory=list)
    why_rejected: Dict[str, str] = Field(default_factory=dict)
    safety_interceptions: List[str] = Field(default_factory=list)
    llm_advisory_summary: Optional[str] = None
    prompt_injection_detected: bool = False
    prompt_injection_contained: bool = False


class ReplayRequest(BaseModel):
    """
    Request payload for executing a decision replay.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: Optional[str] = None
    preset_key: Optional[str] = None
    payment: Optional[Any] = None
    events: Optional[List[Any]] = None
    order_events: Optional[List[Any]] = None
    seed: int = 42
    simulation_only: bool = Field(default=True, description="Must remain True. Real payment execution is prohibited.")

    @field_validator("simulation_only")
    @classmethod
    def validate_simulation_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Replay system is strictly SIMULATION ONLY. Live/production gateway execution is prohibited.")
        return v


class RecoveryDecisionReplay(BaseModel):
    """
    Complete transaction-level recovery decision replay and evidence record.
    """
    model_config = ConfigDict(extra="allow")

    replay_id: str = Field(default_factory=lambda: f"rpl_{uuid.uuid4().hex[:10]}")
    run_id: str
    payment_id: str
    order_id: Optional[str] = None
    correlation_id: str
    timestamp: str
    simulation_only: bool = True
    preset_name: Optional[str] = None

    # Full event stream
    events: List[Any] = Field(default_factory=list)
    order_events: Optional[List[Any]] = None

    # Decision Steps
    initial_financial_state: str
    recovery_opportunity_detected: bool
    llm_recommendation: Optional[Dict[str, Any]] = None
    candidate_matrix: List[ActionCandidateEvaluation] = Field(default_factory=list)
    selected_action: str
    policy_verdict: str
    firewall_verdict: str
    execution_summary: Dict[str, Any] = Field(default_factory=dict)
    verification_summary: Dict[str, Any] = Field(default_factory=dict)
    final_financial_state: str

    # Financial & Provenance Proofs
    financial_proof: FinancialProof
    provenance: DecisionProvenance
    evidence_graph: EvidenceGraph
    evidence_hash: str
    audit_reference: Dict[str, Any] = Field(default_factory=dict)


class ReplayRunResult(BaseModel):
    """API response model for replay execution."""
    replay: RecoveryDecisionReplay
    simulation_flag: bool = True
