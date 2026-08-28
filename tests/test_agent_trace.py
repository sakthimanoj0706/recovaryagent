"""
Unit & Integration Tests for RecoverAI Agent Decision Trace and Demo Mode Hardening.
Validates:
1. Decision trace creation and model schema
2. Trace contains all 6 stages (PROVE, PRIORITIZE, PLAN, GUARD, ACT, VERIFY) plus ACCOUNTING
3. No hidden chain-of-thought stored in trace or outcome
4. Already recovered bypasses ML + Agent planner
5. Uncertain state bypasses ML + Agent planner
6. Exception state bypasses ML + Agent planner
7. Hard decline cannot bypass firewall
8. Duplicate action cannot execute (Idempotency)
9. Retry #4 cannot execute (MAX_RETRY_LIMIT)
10. Executor success does not equal financial recovery
11. Verifier remains the sole source of truth
12. Demo mode does not call external LLM (deterministic & offline)
13. Live mode preserves frontier LLM integration capability
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction, RecoveryPriority, RecoveryContext, RecoveryPlan, FirewallDecision
from agent.llm import (
    DeterministicFallbackLLMClient,
    GeminiLLMClient,
    OpenRouterLLMClient,
    get_default_llm_client,
)
from agent.orchestrator import RecoverAIOrchestrator
from agent.trace import AgentDecisionTrace, build_decision_trace
from audit.logger import AuditLogger


@pytest.fixture
def orchestrator(tmp_path):
    log_file = tmp_path / "test_trace_audit.jsonl"
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return RecoverAIOrchestrator(
        audit_logger=AuditLogger(log_path=log_file),
        llm_client=DeterministicFallbackLLMClient(),
        model=model,
    )


# 1. Decision trace creation & all 6 stages present
def test_decision_trace_contains_all_six_stages(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_01", order_id="ord_tr_01", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_tr_01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_01", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.decision_trace is not None

    trace_dict = outcome.decision_trace
    assert trace_dict["payment_id"] == "pay_tr_01"
    assert trace_dict["amount"] == 10000.0

    # Verify all 6 stages exist in outcome trace
    assert trace_dict["prove"]["financial_state"] == "VERIFIED_LOST"
    assert trace_dict["prioritize"]["economic_decision"] == "RECOVERY_WORTHWHILE"
    assert trace_dict["plan"]["agent_action"] in ["PAYMENT_LINK", "REMINDER"]
    assert trace_dict["guard"]["firewall_decision"] == "APPROVED"
    assert trace_dict["act"]["execution_status"] == "SIMULATED_SUCCESS"
    assert trace_dict["verify"]["verification_source"] == "FINANCIAL STATE ENGINE"
    assert trace_dict["accounting"]["amount_recovered"] == 10000.0

    # Also test get_decision_trace method on fresh payment
    pay_fresh = PaymentRecord(payment_id="pay_tr_01_fresh", order_id="ord_tr_01_fresh", amount=5000.0, method="upi", customer_segment="high_value_repeat")
    evs_fresh = [
        Event(event="payment.created", payment_id="pay_tr_01_fresh", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_01_fresh", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    trace = orchestrator.get_decision_trace(pay_fresh, evs_fresh)
    assert isinstance(trace, AgentDecisionTrace)
    assert trace.payment_id == "pay_tr_01_fresh"
    assert trace.guard.firewall_decision == "APPROVED"



# 2. No hidden chain-of-thought stored
def test_no_hidden_chain_of_thought_stored(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_02", order_id="ord_tr_02", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_tr_02", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_02", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    trace = orchestrator.get_decision_trace(payment, events)

    # Assert no thinking / reasoning_content / raw prompts exposed
    trace_dict = trace.to_dict()
    forbidden_keys = ["thinking", "chain_of_thought", "internal_monologue", "raw_prompt", "system_prompt"]
    for k in forbidden_keys:
        assert k not in trace_dict
        assert k not in trace_dict["plan"]

    # Plan reason should be concise and direct
    assert len(trace.plan.agent_reason) < 1000


# 3. Already recovered bypasses ML + Agent
def test_already_recovered_bypasses_ml_and_agent(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_03", order_id="ord_tr_03", amount=25000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_tr_03", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_03", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.authorized", payment_id="pay_tr_03", ts="2026-08-10T10:45:00Z"),
        Event(event="payment.captured", payment_id="pay_tr_03", ts="2026-08-10T10:45:08Z"),
    ]
    trace = orchestrator.get_decision_trace(payment, events)
    assert trace.prove.financial_state == "ALREADY_RECOVERED"
    assert trace.prioritize.economic_decision == "BYPASSED"
    assert trace.prioritize.recovery_probability is None
    assert trace.plan.agent_action == "BYPASSED"
    assert trace.guard.firewall_decision == "STOP"
    assert trace.act.execution_status == "BLOCKED_BY_FIREWALL"
    assert trace.verify.final_result == "NO_ACTION"
    assert trace.accounting.amount_withheld == 25000.0
    assert trace.accounting.amount_recovered == 0.0


# 4. Uncertain state bypasses ML + Agent
def test_uncertain_bypasses_ml_and_agent(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_04", order_id="ord_tr_04", amount=6000.0, method="upi", scenario="uncertain_pending")
    events = [
        Event(event="payment.created", payment_id="pay_tr_04", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_04", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_tr_04", ts="2026-08-10T10:00:10Z"),
    ]
    trace = orchestrator.get_decision_trace(payment, events)
    assert trace.prove.financial_state == "UNCERTAIN"
    assert trace.prioritize.economic_decision == "BYPASSED"
    assert trace.plan.agent_action == "BYPASSED"
    assert trace.guard.firewall_decision == "STOP"
    assert trace.verify.final_result == "WAIT"
    assert trace.accounting.amount_pending == 6000.0
    assert trace.accounting.amount_withheld == 0.0


# 5. Exception state bypasses ML + Agent
def test_exception_bypasses_ml_and_agent(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_05", order_id="ord_tr_05", amount=8500.0, method="card", has_settlement=True, settled_amount=7000.0, settlement_matches_order=False)
    events = [
        Event(event="payment.created", payment_id="pay_tr_05", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_tr_05", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_tr_05", ts="2026-08-10T10:00:10Z"),
    ]
    trace = orchestrator.get_decision_trace(payment, events)
    assert trace.prove.financial_state == "EXCEPTION"
    assert trace.prioritize.economic_decision == "BYPASSED"
    assert trace.guard.firewall_decision == "ESCALATE"
    assert trace.verify.final_result == "ESCALATED_TO_OPERATIONS"
    assert trace.accounting.amount_escalated == 8500.0
    assert trace.accounting.amount_recovered == 0.0


# 6. Hard decline cannot bypass firewall
def test_hard_decline_cannot_bypass_firewall(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_06", order_id="ord_tr_06", amount=12000.0, method="card", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_tr_06", ts="2026-08-10T11:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_06", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T11:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule == "FIREWALL-004"
    assert outcome.final_outcome == "SAFE_STOP"
    assert outcome.amount_withheld == 12000.0


# 7. Duplicate action cannot execute (Idempotency)
def test_duplicate_action_cannot_execute(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_07", order_id="ord_tr_07", amount=7000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_tr_07", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_07", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    res1 = orchestrator.process_payment(payment, events, force_simulated_success=False)
    assert res1.firewall_decision == "APPROVED"

    res2 = orchestrator.process_payment(payment, events, override_action=RecoveryAction.PAYMENT_LINK)
    assert res2.firewall_decision == "STOP"
    assert res2.firewall_rule == "FIREWALL-009"
    assert res2.final_outcome == "DUPLICATE_ACTION_BLOCKED"


# 8. Retry #4 cannot execute
def test_retry_number_four_cannot_execute(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_08", order_id="ord_tr_08", amount=4500.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_tr_08", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_tr_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_tr_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_tr_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule == "FIREWALL-005"
    assert outcome.final_outcome == "MAX_RETRY_PROTECTION"


# 9. Executor success does not equal financial recovery
def test_executor_success_does_not_equal_financial_recovery(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_09", order_id="ord_tr_09", amount=15000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_tr_09", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_09", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    # Even if action was dispatched, verifier proves state remains VERIFIED_LOST
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=False)
    assert outcome.verification_state == "VERIFIED_LOST"
    assert outcome.final_outcome == "RECOVERY_FAILED"
    assert outcome.amount_recovered == 0.0


# 10. Verifier remains sole source of truth
def test_verifier_remains_source_of_truth(orchestrator):
    payment = PaymentRecord(payment_id="pay_tr_10", order_id="ord_tr_10", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_tr_10", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_tr_10", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.source_of_truth == "FINANCIAL STATE ENGINE"
    assert outcome.verification_state == "ALREADY_RECOVERED"
    assert outcome.final_outcome == "RECOVERY_SUCCESS"


# 11. Demo mode does not call external LLM
def test_demo_mode_does_not_call_external_llm(monkeypatch):
    monkeypatch.setenv("AI_MODE", "demo")
    client = get_default_llm_client()
    assert isinstance(client, DeterministicFallbackLLMClient)
    assert client.mode == "demo"


# 12. Live mode preserves frontier LLM integration
def test_live_mode_preserves_llm_integration(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-fake-key")
    client = get_default_llm_client()
    assert isinstance(client, OpenRouterLLMClient)
    assert client.mode == "live"
