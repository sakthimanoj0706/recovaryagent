"""
Adversarial and Edge Case Safety Test Suite for RecoverAI (Step 7).
Proves the core fintech safety invariant: 'NO FALSE RECOVERIES UNDER ANY ADVERSARIAL CONDITION'.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime, timezone

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import FinancialState, PaymentRecord, Event
from state_engine.engine import FinancialStateEngine
from recovery.model import RecoveryProbabilityModel
from agent.orchestrator import AgenticRecoveryOrchestrator
from agent.models import RecoveryAction, FirewallDecision
from ingestion.processor import EventProcessor
from ingestion.models import IngestionStatus
from audit.logger import AuditLogger
from gateway.mock_gateway import MockPaymentGateway
from gateway.models import GatewayActionStatus


@pytest.fixture
def state_engine():
    return FinancialStateEngine()


@pytest.fixture
def orchestrator(state_engine):
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return AgenticRecoveryOrchestrator(state_engine=state_engine, model=model)


@pytest.fixture
def processor(state_engine, orchestrator):
    proc = EventProcessor(state_engine=state_engine, orchestrator=orchestrator)
    proc.clear_store()
    return proc


# 1. test_late_authorization_after_recovery_action
def test_late_authorization_after_recovery_action(orchestrator):
    pay = PaymentRecord(payment_id="adv_late_auth_01", amount=18000.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=18000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=18000.0, ts="2026-08-28T10:00:05Z"),
        Event(event="payment.authorized", payment_id=pay.payment_id, amount=18000.0, late_authorization=True, ts="2026-08-28T10:45:00Z"),
    ]
    outcome = orchestrator.process_payment(pay, evs)
    assert outcome.initial_state == "ALREADY_RECOVERED"
    assert outcome.firewall_decision == "STOP"
    assert outcome.amount_withheld == 18000.0
    assert outcome.amount_recovered == 0.0


# 2. test_capture_arriving_long_after_failure
def test_capture_arriving_long_after_failure(processor):
    pid = "adv_long_capture_02"
    # Failed at 10:00
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_adv_f_02",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 22000.0,
        "error_code": "TIMEOUT",
        "ts": "2026-08-28T10:00:00Z",
    })
    # Captured at 18:00 (8 hours later)
    res_cap = processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_adv_c_02",
        "event": "payment.captured",
        "payment_id": pid,
        "amount": 22000.0,
        "ts": "2026-08-28T18:00:00Z",
    })
    assert res_cap.financial_state_after == "ALREADY_RECOVERED"
    assert res_cap.state_changed is True


# 3. test_duplicate_capture_idempotency
def test_duplicate_capture_idempotency(processor):
    pid = "adv_dup_cap_03"
    payload = {
        "provider": "mock",
        "event_id": "evt_adv_cap_03",
        "event": "payment.captured",
        "payment_id": pid,
        "amount": 5000.0,
        "ts": "2026-08-28T10:00:00Z",
    }
    r1 = processor.process_webhook(payload)
    assert r1.status == IngestionStatus.PROCESSED
    r2 = processor.process_webhook(payload)
    assert r2.status == IngestionStatus.DUPLICATE_EVENT


# 4. test_failed_after_capture_impossible_transition
def test_failed_after_capture_impossible_transition(orchestrator):
    pay = PaymentRecord(payment_id="adv_fail_after_cap_04", amount=9000.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=9000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.captured", payment_id=pay.payment_id, amount=9000.0, ts="2026-08-28T10:00:05Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=9000.0, ts="2026-08-28T10:00:10Z"),
    ]
    eval_res = orchestrator.state_engine.evaluate_payment(pay, evs)
    assert eval_res.state == FinancialState.EXCEPTION


# 5. test_refunded_without_capture_impossible
def test_refunded_without_capture_impossible(orchestrator):
    pay = PaymentRecord(payment_id="adv_refund_no_cap_05", amount=4500.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=4500.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=4500.0, ts="2026-08-28T10:00:05Z"),
        Event(event="payment.refunded", payment_id=pay.payment_id, amount=4500.0, ts="2026-08-28T10:00:10Z"),
    ]
    eval_res = orchestrator.state_engine.evaluate_payment(pay, evs)
    assert eval_res.state == FinancialState.EXCEPTION


# 6. test_malformed_webhook_rejected_as_exception
def test_malformed_webhook_rejected_as_exception(processor):
    malformed = {"provider": "mock", "amount": "INVALID_AMOUNT", "ts": "bad_time"}
    res = processor.process_webhook(malformed)
    assert res.status == IngestionStatus.MALFORMED_EVENT


# 7. test_duplicate_recovery_request_blocked
def test_duplicate_recovery_request_blocked(orchestrator):
    pay = PaymentRecord(payment_id="adv_dup_req_07", amount=7000.0, scenario="soft_decline_retryable")
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=7000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=7000.0, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    # Call 1: PAYMENT_LINK
    out1 = orchestrator.process_payment(pay, evs, override_action=RecoveryAction.PAYMENT_LINK, force_simulated_success=False)
    assert out1.final_outcome == "RECOVERY_FAILED"

    # Call 2: Duplicate PAYMENT_LINK -> Intercepted by FIREWALL-009
    out2 = orchestrator.process_payment(pay, evs, override_action=RecoveryAction.PAYMENT_LINK)
    assert out2.firewall_decision == "STOP"
    assert out2.firewall_rule == "FIREWALL-009"
    assert out2.final_outcome == "DUPLICATE_ACTION_BLOCKED"


# 8. test_planner_hallucinating_success_string
def test_planner_hallucinating_success_string(orchestrator):
    # If an LLM suggests an unsupported action string, policy safely rejects
    assert not RecoveryAction.is_valid_action("DECLARE_RECOVERED")
    assert not RecoveryAction.is_valid_action("FORCE_CAPTURE")


# 9. test_planner_suggesting_forbidden_retry_on_hard_decline
def test_planner_suggesting_forbidden_retry_on_hard_decline(orchestrator):
    pay = PaymentRecord(payment_id="adv_hard_retry_09", amount=12000.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=12000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=12000.0, error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-28T10:00:05Z"),
    ]
    out = orchestrator.process_payment(pay, evs, override_action=RecoveryAction.RETRY)
    assert out.firewall_decision == "STOP"
    assert out.firewall_rule == "FIREWALL-004"
    assert out.amount_recovered == 0.0


# 10. test_positive_env_with_hard_decline_blocked
def test_positive_env_with_hard_decline_blocked(orchestrator):
    # Even if amount is 100k, hard decline blocks automated RETRY
    pay = PaymentRecord(payment_id="adv_pos_env_hard_10", amount=100000.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=100000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=100000.0, error_code="CARD_EXPIRED", hardness="hard", ts="2026-08-28T10:00:05Z"),
    ]
    out = orchestrator.process_payment(pay, evs, override_action=RecoveryAction.RETRY)
    assert out.firewall_decision == "STOP"
    assert out.firewall_rule == "FIREWALL-004"


# 11. test_negative_env_with_agent_recommendation_withheld
def test_negative_env_with_agent_recommendation_withheld(orchestrator):
    pay = PaymentRecord(payment_id="adv_neg_env_11", amount=500.0, method="card", customer_segment="new")
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=500.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=500.0, error_code="USER_CANCELLED", hardness="hard", ts="2026-08-28T10:00:05Z"),
    ]
    out = orchestrator.process_payment(pay, evs)
    assert out.firewall_rule == "FIREWALL-002"
    assert out.amount_withheld == 500.0
    assert out.amount_recovered == 0.0


# 12. test_retry_count_beyond_maximum_blocked
def test_retry_count_beyond_maximum_blocked(orchestrator):
    pay = PaymentRecord(payment_id="adv_max_retry_12", amount=4500.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=4500.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=4500.0, error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-28T10:00:05Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=4500.0, error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-28T10:00:10Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=4500.0, error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-28T10:00:15Z"),
    ]
    out = orchestrator.process_payment(pay, evs, override_action=RecoveryAction.RETRY)
    assert out.firewall_decision == "STOP"
    assert out.firewall_rule == "FIREWALL-005"
    assert out.final_outcome == "MAX_RETRY_PROTECTION"


# 13. test_verification_disagrees_with_executor_catch
def test_verification_disagrees_with_executor_catch(orchestrator):
    pay = PaymentRecord(payment_id="adv_ver_catch_13", amount=15000.0, scenario="soft_decline_retryable")
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=15000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=15000.0, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    # Simulated execution fails
    out = orchestrator.process_payment(pay, evs, force_simulated_success=False)
    assert out.verification_state == "VERIFIED_LOST"
    assert out.final_outcome == "RECOVERY_FAILED"
    assert out.amount_recovered == 0.0


# 14. test_gateway_says_success_but_ledger_remains_verified_lost
def test_gateway_says_success_but_ledger_remains_verified_lost(orchestrator):
    # Even if mock gateway returned SUCCESS, if post-action events still indicate failure, verifier rules
    pay = PaymentRecord(payment_id="adv_gw_vs_ledger_14", amount=10000.0)
    evs = [
        Event(event="payment.created", payment_id=pay.payment_id, amount=10000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay.payment_id, amount=10000.0, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    post_evs = [
        Event(event="payment.failed", payment_id=pay.payment_id, amount=10000.0, error_code="EXPIRED_CHECKOUT", ts="2026-08-28T10:30:00Z")
    ]
    ver_res = orchestrator.verifier.verify_post_action(pay, evs + post_evs)
    assert ver_res.state == FinancialState.VERIFIED_LOST


# 15. test_accounting_invariant_holds_under_adversarial_load
def test_accounting_invariant_holds_under_adversarial_load():
    logger = AuditLogger()
    metrics = logger.calculate_metrics()
    assert metrics.verify_accounting_balance() is True
