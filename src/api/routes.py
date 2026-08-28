"""
FastAPI Routes for RecoverAI Command Center.
Bridges frontend dashboard to existing backend engine, recovery intelligence, agent planner, and verifier.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from state_engine.models import PaymentRecord, Event, FinancialState
from state_engine.engine import FinancialStateEngine
from recovery.model import RecoveryProbabilityModel
from recovery.decision import RecoveryDecisionEngine
from recovery.economics import RecoveryCostConfig
from agent.models import RecoveryAction
from agent.orchestrator import RecoverAIOrchestrator
from agent.llm import get_default_llm_client
from audit.logger import AuditLogger
from execution.outcome import ClosedLoopOutcome

router = APIRouter()

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
PAYMENTS_CSV = BASE_DIR / "payments.csv"
EVENTS_JSONL = BASE_DIR / "events.jsonl"
MODEL_PATH = BASE_DIR / "models" / "recovery_probability_model.joblib"
AUDIT_LOG_PATH = BASE_DIR / "logs" / "recovery_audit.jsonl"

# Singletons
state_engine = FinancialStateEngine()
model = RecoveryProbabilityModel.load(MODEL_PATH) if MODEL_PATH.exists() else None
recovery_engine = RecoveryDecisionEngine(model=model, cost_config=RecoveryCostConfig(), state_engine=state_engine) if model else None
audit_logger = AuditLogger(AUDIT_LOG_PATH)
llm_client = get_default_llm_client()
orchestrator = RecoverAIOrchestrator(
    state_engine=state_engine,
    model=model,
    llm_client=llm_client,
    audit_logger=audit_logger,
)


def load_dataset() -> tuple[pd.DataFrame, Dict[str, List[Event]]]:
    """Load payments and events from local dataset files."""
    df_payments = pd.read_csv(PAYMENTS_CSV)
    
    events_by_payment: Dict[str, List[Event]] = {}
    if EVENTS_JSONL.exists():
        with open(EVENTS_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ev_data = json.loads(line.strip())
                    ev = Event(**ev_data)
                    pid = ev.payment_id
                    if pid:
                        if pid not in events_by_payment:
                            events_by_payment[pid] = []
                        events_by_payment[pid].append(ev)
    return df_payments, events_by_payment


@router.get("/metrics")
def get_metrics() -> Dict[str, Any]:
    """
    Retrieve aggregated dashboard KPIs including ₹ Recovered and ₹ Correctly Withheld.
    """
    metrics = audit_logger.calculate_metrics()
    return {
        "total_cases": metrics.total_cases,
        "verified_lost_cases": metrics.verified_lost_cases,
        "recovery_attempts": metrics.recovery_attempts,
        "successful_recoveries": metrics.successful_recoveries,
        "failed_recoveries": metrics.failed_recoveries,
        "recovery_success_rate": metrics.recovery_success_rate,
        "total_amount_attempted": metrics.total_amount_attempted,
        "total_amount_recovered": metrics.total_amount_recovered,
        "total_amount_withheld": metrics.total_amount_withheld,
        "unnecessary_actions_avoided": metrics.unnecessary_actions_avoided,
        "firewall_blocks": metrics.firewall_blocks,
        "uncertain_cases": metrics.uncertain_cases,
        "exception_cases": metrics.exception_cases,
        "max_retry_blocks": metrics.max_retry_blocks,
        "duplicate_action_blocks": metrics.duplicate_action_blocks,
    }


@router.get("/payments")
def list_payments(limit: int = 50, offset: int = 0, filter_state: Optional[str] = None) -> Dict[str, Any]:
    """
    List payments with ground truth states and recovery attributes.
    """
    df, events_map = load_dataset()
    
    records = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        pid = str(row_dict.get("payment_id"))
        evs = events_map.get(pid, [])
        
        # Calculate state if not already present
        state_res = state_engine.evaluate_payment(PaymentRecord(**row_dict), evs)
        
        item = {
            "payment_id": pid,
            "order_id": row_dict.get("order_id"),
            "amount": float(row_dict.get("amount", 0.0)),
            "currency": row_dict.get("currency", "INR"),
            "method": row_dict.get("method", "unknown"),
            "customer_segment": row_dict.get("customer_segment", "unknown"),
            "error_code": row_dict.get("error_code") or (evs[-1].error_code if evs and evs[-1].error_code else "NONE"),
            "hardness": row_dict.get("hardness") or (evs[-1].hardness if evs and evs[-1].hardness else "soft"),
            "financial_state": state_res.state.value,
            "event_count": len(evs),
        }
        
        if filter_state and filter_state.upper() != "ALL":
            if item["financial_state"] != filter_state.upper():
                continue

        records.append(item)

    total_count = len(records)
    paginated = records[offset : offset + limit]

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "payments": paginated,
    }


@router.get("/payments/{payment_id}")
def get_payment_details(payment_id: str) -> Dict[str, Any]:
    """
    Retrieve full details, lifecycle events, and intelligence evaluation for a payment.
    """
    df, events_map = load_dataset()
    match = df[df["payment_id"] == payment_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    row_dict = match.iloc[0].to_dict()
    payment = PaymentRecord(**row_dict)
    events = events_map.get(payment_id, [])

    state_res = state_engine.evaluate_payment(payment, events)
    
    rec_prob = None
    env = None
    rec_decision = "INELIGIBLE"

    if recovery_engine and state_res.state == FinancialState.VERIFIED_LOST:
        dec_res = recovery_engine.evaluate_payment(payment, events, precomputed_state=state_res.state)
        rec_prob = dec_res.recovery_probability
        env = dec_res.expected_net_value
        rec_decision = dec_res.decision.value

    return {
        "payment": row_dict,
        "financial_state": state_res.state.value,
        "financial_rule_id": state_res.rule_id,
        "financial_state_reason": state_res.reason,
        "recovery_probability": rec_prob,
        "expected_net_value": env,
        "recovery_decision": rec_decision,
        "events": [e.model_dump() for e in events],
    }


@router.post("/recovery/{payment_id}")
@router.post("/recovery/run/{payment_id}")
def run_recovery_on_payment(payment_id: str) -> Dict[str, Any]:
    """
    Trigger end-to-end closed-loop recovery on a specific payment.
    """
    df, events_map = load_dataset()
    match = df[df["payment_id"] == payment_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    row_dict = match.iloc[0].to_dict()
    payment = PaymentRecord(**row_dict)
    events = events_map.get(payment_id, [])

    outcome = orchestrator.process_payment(payment, events)
    return outcome.model_dump()


@router.get("/recovery/{payment_id}/trace")
def get_recovery_trace(payment_id: str) -> Dict[str, Any]:
    """
    Retrieve the structured Agent Decision Trace across the 6-stage lifecycle:
    PROVE -> PRIORITIZE -> PLAN -> GUARD -> ACT -> VERIFY.
    """
    df, events_map = load_dataset()
    match = df[df["payment_id"] == payment_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    row_dict = match.iloc[0].to_dict()
    payment = PaymentRecord(**row_dict)
    events = events_map.get(payment_id, [])

    trace = orchestrator.get_decision_trace(payment, events)
    return trace.model_dump()


@router.post("/agent/recover/{payment_id}")
def run_agentic_recovery(payment_id: str) -> Dict[str, Any]:
    """
    Execute bounded autonomous agent recovery loop on a payment.
    Returns full AgentRunResult telemetry including steps, tool calls, and policy checks.
    """
    df, events_map = load_dataset()
    match = df[df["payment_id"] == payment_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    row_dict = match.iloc[0].to_dict()
    payment = PaymentRecord(**row_dict)
    events = events_map.get(payment_id, [])

    run_result = orchestrator.run_recovery_agent(payment, events)
    return run_result.model_dump()


@router.get("/agent/runs/{run_id}")
def get_agent_run(run_id: str) -> Dict[str, Any]:
    """
    Retrieve full execution trace for an autonomous agent run.
    """
    run_result = orchestrator.get_run(run_id)
    if not run_result:
        raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found.")
    return run_result.model_dump()




@router.get("/audit")
def get_audit_trail(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve persisted audit trail records.
    """
    records = audit_logger.get_records()
    # Return latest records first
    records_rev = list(reversed(records))[:limit]
    return [r.to_dict() for r in records_rev]


class DemoScenarioRequest(BaseModel):
    scenario_id: Optional[str] = None
    custom_amount: Optional[float] = None


@router.post("/demo/scenario/{scenario_id}")
@router.post("/demo/{scenario}")
def run_demo_scenario(scenario: Optional[str] = None, scenario_id: Optional[str] = None, req: Optional[DemoScenarioRequest] = None) -> Dict[str, Any]:
    """
    Run predefined demonstration scenarios through the actual backend pipeline.
    Returns structured step-by-step telemetry for the animated UI pipeline.
    """
    sc = (scenario or scenario_id or (req.scenario_id if req else "") or "1").lower().strip()

    
    if sc in ["1", "successful_recovery", "success"]:
        pay = PaymentRecord(
            payment_id=f"pay_demo_success_{uuid.uuid4().hex[:6]}",
            order_id="order_demo_101",
            amount=10000.0 if not req or not req.custom_amount else req.custom_amount,
            method="upi",
            customer_segment="high_value_repeat",
        )
        events = [
            Event(event="payment.created", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T10:00:00Z"),
            Event(event="payment.failed", payment_id=pay.payment_id, order_id=pay.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:06Z"),
        ]
        outcome = orchestrator.process_payment(pay, events, force_simulated_success=True)
        title = "Successful Closed-Loop Recovery"
        desc = "Soft Failure -> Payment Link Dispatched -> Confirmed Captured -> Rs. 10,000 Recovered."

    elif sc in ["2", "late_authorization", "flip_flop", "flip"]:
        pay = PaymentRecord(
            payment_id=f"pay_demo_lateauth_{uuid.uuid4().hex[:6]}",
            order_id="order_demo_202",
            amount=25000.0 if not req or not req.custom_amount else req.custom_amount,
            method="upi",
            customer_segment="returning",
        )
        events = [
            Event(event="payment.created", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T11:00:00Z"),
            Event(event="payment.failed", payment_id=pay.payment_id, order_id=pay.order_id, error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T11:00:06Z"),
            Event(event="payment.authorized", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T11:05:00Z"),
            Event(event="payment.captured", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T11:05:08Z"),
        ]
        outcome = orchestrator.process_payment(pay, events)
        title = "Late Authorization Flip (FAILED ≠ LOST)"
        desc = "Late capture detected by Financial State Engine. Recovery blocked: Rs. 25,000 correctly withheld."

    elif sc in ["3", "hard_decline", "card_blocked"]:
        pay = PaymentRecord(
            payment_id=f"pay_demo_hard_{uuid.uuid4().hex[:6]}",
            order_id="order_demo_303",
            amount=12000.0 if not req or not req.custom_amount else req.custom_amount,
            method="card",
            customer_segment="returning",
        )
        events = [
            Event(event="payment.created", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T13:00:00Z"),
            Event(event="payment.failed", payment_id=pay.payment_id, order_id=pay.order_id, error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T13:00:05Z"),
        ]
        outcome = orchestrator.process_payment(pay, events, override_action=RecoveryAction.RETRY)
        title = "Hard Decline Safety Protection"
        desc = "Permanent card block decline. Automated RETRY blocked by FIREWALL-004."

    elif sc in ["4", "negative_env", "uneconomic"]:
        pay = PaymentRecord(
            payment_id=f"pay_demo_negenv_{uuid.uuid4().hex[:6]}",
            order_id="order_demo_404",
            amount=500.0 if not req or not req.custom_amount else req.custom_amount,
            method="card",
            customer_segment="new",
        )
        events = [
            Event(event="payment.created", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T12:00:00Z"),
            Event(event="payment.failed", payment_id=pay.payment_id, order_id=pay.order_id, error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T12:00:05Z"),
        ]
        outcome = orchestrator.process_payment(pay, events)
        title = "Negative Unit Economics Protection (ENV <= 0)"
        desc = "Expected Net Value is negative (cost > expected return). Rs. 500 correctly withheld."

    elif sc in ["5", "verification_catch", "failed_recovery", "unrecovered"]:
        pay = PaymentRecord(
            payment_id=f"pay_demo_unrec_{uuid.uuid4().hex[:6]}",
            order_id="order_demo_505",
            amount=15000.0 if not req or not req.custom_amount else req.custom_amount,
            method="upi",
            customer_segment="returning",
        )
        events = [
            Event(event="payment.created", payment_id=pay.payment_id, order_id=pay.order_id, ts="2026-08-10T10:30:00Z"),
            Event(event="payment.failed", payment_id=pay.payment_id, order_id=pay.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:30:06Z"),
        ]
        outcome = orchestrator.process_payment(pay, events, force_simulated_success=False)
        title = "Agent Claim ≠ Financial Truth (Verification Catch)"
        desc = "Action dispatched but customer did not pay. Verifier independently proves state remains VERIFIED_LOST."


    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario {scenario}")

    # Build timeline stages for animation
    timeline = [
        {
            "step": "PAYMENT",
            "status": "COMPLETED",
            "label": "Payment Ingested",
            "detail": f"ID: {outcome.payment_id} | Amount: Rs. {outcome.amount:,.2f}",
        },
        {
            "step": "PROVE",
            "status": "COMPLETED",
            "label": "Financial State Engine",
            "detail": f"State: {outcome.initial_state}",
        },
        {
            "step": "PRIORITIZE",
            "status": "COMPLETED" if outcome.expected_net_value is not None else "SKIPPED",
            "label": "Recovery Intelligence",
            "detail": f"P: {int(round(outcome.recovery_probability * 100)) if outcome.recovery_probability else 0}% | ENV: Rs. {outcome.expected_net_value:,.2f}" if outcome.expected_net_value is not None else "Ineligible for recovery",
        },
        {
            "step": "AGENT",
            "status": "COMPLETED" if outcome.agent_action else "SKIPPED",
            "label": "Agent Planner",
            "detail": f"Action: {outcome.agent_action} | {outcome.agent_reason}" if outcome.agent_action else "Planning bypassed",
        },
        {
            "step": "FIREWALL",
            "status": "COMPLETED",
            "label": "Recovery Firewall",
            "detail": f"Verdict: {outcome.firewall_decision} | Rule: {outcome.firewall_rule or 'PASSED'}",
        },
        {
            "step": "ACT",
            "status": "COMPLETED" if outcome.execution_status.startswith("SIMULATED_SUCCESS") else ("BLOCKED" if "BLOCKED" in outcome.execution_status else "FAILED"),
            "label": "Simulated Action Executor",
            "detail": f"Status: {outcome.execution_status} | {outcome.execution_message or ''}",
        },
        {
            "step": "VERIFY",
            "status": "COMPLETED",
            "label": "Closed-Loop Verification",
            "detail": f"Verified State: {outcome.verification_state} (Source: {outcome.source_of_truth})",
        },
    ]

    return {
        "title": title,
        "description": desc,
        "outcome": outcome.model_dump(),
        "timeline": timeline,
    }


# =============================================================================
# EVENT INGESTION & WEBHOOK API (Step 6)
# =============================================================================

from ingestion import get_event_processor, WebhookPayload
from gateway import get_gateway


@router.post("/webhooks/payment")
def handle_payment_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real-time payment webhook ingestion endpoint.
    Idempotently validates, normalizes, stores, and evaluates financial events.
    """
    processor = get_event_processor()
    result = processor.process_webhook(payload)
    return result.to_dict()


@router.get("/events/timeline")
def get_event_timeline(limit: int = 50) -> Dict[str, Any]:
    """
    Retrieve chronological event ingestion timeline for the Command Center.
    """
    processor = get_event_processor()
    events = processor.get_timeline(limit=limit)
    return {
        "total_events": len(events),
        "timeline": events,
    }


@router.get("/system/health")
def get_system_health() -> Dict[str, Any]:
    """
    System Health Status Report across all RecoverAI modules.
    """
    gateway_inst = get_gateway()
    return {
        "timestamp": pd.Timestamp.now("UTC").isoformat(),
        "status": "OPERATIONAL",
        "simulation_mode": True,
        "subsystems": {
            "ingestion": {"status": "HEALTHY", "mode": "IDEMPOTENT_STREAM"},
            "state_engine": {"status": "HEALTHY", "mode": "DETERMINISTIC_AUTHORITY"},
            "agent": {"status": "HEALTHY", "mode": "BOUNDED_ADVISORY"},
            "firewall": {"status": "ACTIVE", "mode": "HARD_GATES"},
            "gateway": {
                "status": "SIMULATION",
                "provider": gateway_inst.provider_name,
                "is_simulation": gateway_inst.is_simulation,
            },
            "verifier": {"status": "HEALTHY", "mode": "INDEPENDENT_LEDGER"},
            "audit": {"status": "APPEND_ONLY", "mode": "IMMUTABLE_JSONL"},
        },
    }

