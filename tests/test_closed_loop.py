"""
Automated closed-loop integration tests for RecoverAI.
Validates the full cycle: PROVE -> PRIORITIZE -> PLAN -> FIREWALL -> ACT -> VERIFY -> OUTCOME -> AUDIT.
"""

import sys
import json
from pathlib import Path
import pytest

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction, RecoveryPlan, RecoveryContext
from agent.llm import DeterministicFallbackLLMClient
from agent.orchestrator import RecoverAIOrchestrator
from audit.logger import AuditLogger


@pytest.fixture
def mock_audit_log(tmp_path):
    log_file = tmp_path / "recovery_audit_test.jsonl"
    return AuditLogger(log_path=log_file)


@pytest.fixture
def orchestrator(mock_audit_log):
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return RecoverAIOrchestrator(
        audit_logger=mock_audit_log,
        llm_client=DeterministicFallbackLLMClient(),
        model=model,
    )


# 1. test_successful_payment_link_recovery
def test_successful_payment_link_recovery(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_01", order_id="ord_cl_01", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_cl_01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_01", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)

    assert outcome.initial_state == "VERIFIED_LOST"
    assert outcome.firewall_decision == "APPROVED"
    assert outcome.agent_action == "PAYMENT_LINK"
    assert outcome.verification_state == "ALREADY_RECOVERED"
    assert outcome.final_outcome == "RECOVERY_SUCCESS"
    assert outcome.amount_recovered == 10000.0
    assert outcome.amount_withheld == 0.0


# 2. test_failed_recovery_detected
def test_failed_recovery_detected(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_02", order_id="ord_cl_02", amount=8000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_02", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_02", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=False)

    assert outcome.initial_state == "VERIFIED_LOST"
    assert outcome.verification_state == "VERIFIED_LOST"
    assert outcome.final_outcome == "RECOVERY_FAILED"
    assert outcome.amount_recovered == 0.0


# 3. test_agent_cannot_claim_recovery
def test_agent_cannot_claim_recovery(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_03", order_id="ord_cl_03", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_03", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_03", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    # Even if action was dispatched, if state engine reports VERIFIED_LOST, system NEVER reports RECOVERY_SUCCESS
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=False)
    assert outcome.final_outcome != "RECOVERY_SUCCESS"
    assert outcome.amount_recovered == 0.0


# 4. test_verification_is_source_of_truth
def test_verification_is_source_of_truth(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_04", order_id="ord_cl_04", amount=6500.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_04", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_04", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.source_of_truth == "FINANCIAL STATE ENGINE"
    assert outcome.verification_state == "ALREADY_RECOVERED"


# 5. test_late_authorization_stops_recovery
def test_late_authorization_stops_recovery(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_05", order_id="ord_cl_05", amount=7499.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_05", ts="2026-08-10T11:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_05", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T11:00:05Z"),
        Event(event="payment.authorized", payment_id="pay_cl_05", ts="2026-08-10T11:05:00Z"),
        Event(event="payment.captured", payment_id="pay_cl_05", ts="2026-08-10T11:05:08Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "ALREADY_RECOVERED"
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule == "FIREWALL-006"
    assert outcome.final_outcome == "NO_ACTION"
    assert outcome.amount_withheld == 7499.0


# 6. test_negative_env_skips_agent
def test_negative_env_skips_agent(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_06", order_id="ord_cl_06", amount=20.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_cl_06", ts="2026-08-10T12:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_06", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T12:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "VERIFIED_LOST"
    assert outcome.expected_net_value <= 0
    assert outcome.firewall_rule == "FIREWALL-002"
    assert outcome.final_outcome == "CORRECTLY_WITHHELD"
    assert outcome.amount_withheld == 20.0


# 7. test_hard_decline_retry_blocked
def test_hard_decline_retry_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_07", order_id="ord_cl_07", amount=12000.0, method="card", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_07", ts="2026-08-10T13:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_07", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T13:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule == "FIREWALL-004"
    assert outcome.final_outcome == "SAFE_STOP"
    assert outcome.amount_withheld == 12000.0


# 8. test_max_retry_limit
def test_max_retry_limit(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_08", order_id="ord_cl_08", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_08", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_cl_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_cl_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_cl_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule == "FIREWALL-005"
    assert outcome.final_outcome == "MAX_RETRY_PROTECTION"
    assert outcome.amount_withheld == 5000.0


# 9. test_duplicate_action_blocked
def test_duplicate_action_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_09", order_id="ord_cl_09", amount=9000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_cl_09", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_09", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    # First attempt executes
    res1 = orchestrator.process_payment(payment, events, force_simulated_success=False)
    assert res1.firewall_decision == "APPROVED"

    # Second attempt on identical payment with same action is blocked
    res2 = orchestrator.process_payment(payment, events, override_action=RecoveryAction.PAYMENT_LINK)
    assert res2.firewall_decision == "STOP"
    assert res2.firewall_rule == "FIREWALL-009"
    assert res2.final_outcome == "DUPLICATE_ACTION_BLOCKED"


# 10. test_uncertain_after_action
def test_uncertain_after_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_10", order_id="ord_cl_10", amount=7500.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_10", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_10", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    post_events = [
        Event(event="payment.pending", payment_id="pay_cl_10", ts="2026-08-10T10:05:00Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, post_action_events=post_events)
    assert outcome.verification_state == "UNCERTAIN"
    assert outcome.final_outcome == "RECOVERY_WAITING_ASYNC"


# 11. test_exception_after_action
def test_exception_after_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_11", order_id="ord_cl_11", amount=3000.0)
    events = [
        Event(event="payment.created", payment_id="pay_cl_11", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_cl_11", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_cl_11", ts="2026-08-10T10:00:10Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "EXCEPTION"
    assert outcome.final_outcome == "ESCALATED_TO_OPERATIONS"


# 12. test_audit_record_created
def test_audit_record_created(orchestrator, mock_audit_log):
    payment = PaymentRecord(payment_id="pay_cl_12", order_id="ord_cl_12", amount=6000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_12", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_12", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    orchestrator.process_payment(payment, events, force_simulated_success=True)

    records = mock_audit_log.get_records()
    assert len(records) >= 1
    last_rec = records[-1]
    assert last_rec.payment_id == "pay_cl_12"
    assert last_rec.final_result == "RECOVERY_SUCCESS"
    assert last_rec.amount_recovered == 6000.0


# 13. test_simulation_reproducibility
def test_simulation_reproducibility(orchestrator):
    orch1 = RecoverAIOrchestrator(llm_client=DeterministicFallbackLLMClient())
    orch1.executor.simulator.set_seed(999)

    orch2 = RecoverAIOrchestrator(llm_client=DeterministicFallbackLLMClient())
    orch2.executor.simulator.set_seed(999)

    payment = PaymentRecord(payment_id="pay_cl_13", order_id="ord_cl_13", amount=4000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_13", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_13", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]

    res1 = orch1.process_payment(payment, events)
    res2 = orch2.process_payment(payment, events)

    assert res1.final_outcome == res2.final_outcome
    assert res1.verification_state == res2.verification_state


# 14. test_recovered_amount_calculated_correctly
def test_recovered_amount_calculated_correctly(orchestrator):
    payment = PaymentRecord(payment_id="pay_cl_14", order_id="ord_cl_14", amount=15000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_cl_14", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_14", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.amount_recovered == 15000.0
    assert outcome.amount_withheld == 0.0


# 15. test_withheld_amount_calculated_correctly
def test_withheld_amount_calculated_correctly(orchestrator):
    # Late auth case: Rs. 7,499 should be withheld, not recovered
    payment = PaymentRecord(payment_id="pay_cl_15", order_id="ord_cl_15", amount=7499.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_cl_15", ts="2026-08-10T11:00:00Z"),
        Event(event="payment.failed", payment_id="pay_cl_15", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T11:00:05Z"),
        Event(event="payment.captured", payment_id="pay_cl_15", ts="2026-08-10T11:05:00Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.amount_recovered == 0.0
    assert outcome.amount_withheld == 7499.0
