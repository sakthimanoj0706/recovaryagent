"""
Comprehensive unit & safety test suite for RecoverAI Agentic Recovery Orchestrator (Step 3).
Validates all 17 non-negotiable safety rules and agentic boundaries.
"""

import sys
import json
from pathlib import Path
import pytest

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import (
    RecoveryAction,
    RecoveryPriority,
    FirewallDecision,
    RecoveryContext,
    AgentRecommendation,
    RecoveryPlan,
)
from agent.policy import (
    validate_agent_recommendation_against_policy,
    get_failure_policy,
)
from agent.llm import BaseLLMClient, DeterministicFallbackLLMClient
from agent.planner import AgenticRecoveryPlanner
from agent.orchestrator import RecoverAIOrchestrator, run_recovery_agent
from audit.logger import AuditLogger


class MockTrackingLLMClient(BaseLLMClient):
    """Mock LLM client that tracks if and how often it was called."""
    def __init__(self, return_action: RecoveryAction = RecoveryAction.PAYMENT_LINK, rationale: str = "Test rationale"):
        self.call_count = 0
        self.return_action = return_action
        self.rationale = rationale

    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        self.call_count += 1
        return AgentRecommendation(
            payment_id=context.payment_id,
            action=self.return_action,
            rationale=self.rationale,
            confidence=0.9,
            expected_net_value=context.expected_net_value,
        )


class MockTamperingLLMClient(BaseLLMClient):
    """Mock LLM client attempting to tamper with financial state and ENV."""
    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        # Attempt to forge state or expected net value
        rec = AgentRecommendation(
            payment_id=context.payment_id,
            action=RecoveryAction.PAYMENT_LINK,
            rationale="Attempting to forge values",
            confidence=0.9,
            expected_net_value=999999.0, # Attempted forged value
        )
        return rec


@pytest.fixture
def mock_audit_log(tmp_path):
    log_file = tmp_path / "agent_orchestrator_test.jsonl"
    return AuditLogger(log_path=log_file)


@pytest.fixture
def tracking_llm():
    return MockTrackingLLMClient()


@pytest.fixture
def orchestrator(mock_audit_log, tracking_llm):
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return RecoverAIOrchestrator(
        audit_logger=mock_audit_log,
        llm_client=tracking_llm,
        model=model,
    )


# 1. VERIFIED_LOST -> agent called
def test_verified_lost_agent_called(orchestrator, tracking_llm):
    payment = PaymentRecord(payment_id="pay_orc_01", order_id="ord_orc_01", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_orc_01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_01", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.initial_state == "VERIFIED_LOST"
    assert tracking_llm.call_count == 1
    assert outcome.agent_action == "PAYMENT_LINK"


# 2. ALREADY_RECOVERED -> agent not called
def test_already_recovered_agent_not_called(orchestrator, tracking_llm):
    payment = PaymentRecord(payment_id="pay_orc_02", order_id="ord_orc_02", amount=25000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_orc_02", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_02", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_orc_02", ts="2026-08-10T10:45:00Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "ALREADY_RECOVERED"
    assert tracking_llm.call_count == 0  # LLM must NEVER be called for non-lost payments
    assert outcome.final_outcome == "NO_ACTION"
    assert outcome.amount_withheld == 25000.0


# 3. UNCERTAIN -> agent not called
def test_uncertain_agent_not_called(orchestrator, tracking_llm):
    payment = PaymentRecord(payment_id="pay_orc_03", order_id="ord_orc_03", amount=7500.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_orc_03", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_03", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_orc_03", ts="2026-08-10T10:01:00Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "UNCERTAIN"
    assert tracking_llm.call_count == 0
    assert outcome.final_outcome == "WAIT"


# 4. EXCEPTION -> agent not called
def test_exception_agent_not_called(orchestrator, tracking_llm):
    payment = PaymentRecord(payment_id="pay_orc_04", order_id="ord_orc_04", amount=3000.0)
    events = [
        Event(event="payment.created", payment_id="pay_orc_04", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_orc_04", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_04", ts="2026-08-10T10:00:10Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "EXCEPTION"
    assert tracking_llm.call_count == 0
    assert outcome.final_outcome == "ESCALATED_TO_OPERATIONS"


# 5. Negative ENV -> agent not called
def test_negative_env_agent_not_called(orchestrator, tracking_llm):
    payment = PaymentRecord(payment_id="pay_orc_05", order_id="ord_orc_05", amount=30.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_orc_05", ts="2026-08-10T12:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_05", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T12:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events)
    assert outcome.initial_state == "VERIFIED_LOST"
    assert outcome.expected_net_value <= 0
    assert tracking_llm.call_count == 0  # LLM must NEVER be called when ENV <= 0
    assert outcome.final_outcome in ["CORRECTLY_WITHHELD", "STOPPED_FIREWALL-002"]


# 6. Hard decline + LLM recommends RETRY -> firewall blocks
def test_hard_decline_retry_firewall_blocks(mock_audit_log):
    unsafe_llm = MockTrackingLLMClient(return_action=RecoveryAction.RETRY, rationale="Unsafe blind retry")
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    orch = RecoverAIOrchestrator(audit_logger=mock_audit_log, llm_client=unsafe_llm, model=model)

    payment = PaymentRecord(payment_id="pay_orc_06", order_id="ord_orc_06", amount=12000.0, method="card", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_orc_06", ts="2026-08-10T13:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_06", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T13:00:05Z"),
    ]
    outcome = orch.process_payment(payment, events)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule in ["FIREWALL-004", "POLICY_VIOLATION"]
    assert outcome.final_outcome == "SAFE_STOP"
    assert outcome.amount_withheld == 12000.0


# 7. LLM recommends unsupported action -> policy rejects
def test_llm_unsupported_action_policy_rejects():
    ctx = RecoveryContext(
        payment_id="pay_orc_07",
        financial_state="VERIFIED_LOST",
        failure_code="CARD_BLOCKED",
        hardness="hard",
        amount=5000.0,
    )
    rec = AgentRecommendation(
        payment_id="pay_orc_07",
        action=RecoveryAction.RETRY,
        rationale="Policy prohibited retry",
    )
    is_valid, code, reason = validate_agent_recommendation_against_policy(ctx, rec)
    assert is_valid is False
    assert code == "POLICY_VIOLATION"


# 8. LLM malformed JSON -> safe failure
def test_llm_malformed_json_safe_failure(mock_audit_log):
    class MalformedLLM(BaseLLMClient):
        def generate_recovery_plan(self, context, allowed_actions, policy_hints):
            return None  # Represents failed JSON parsing / exception

    planner = AgenticRecoveryPlanner(llm_client=MalformedLLM())
    ctx = RecoveryContext(
        payment_id="pay_orc_08",
        financial_state="VERIFIED_LOST",
        failure_code="TIMEOUT",
        amount=4000.0,
        expected_net_value=3000.0,
    )
    plan = planner.plan_recovery(ctx)
    assert plan is None  # Planner safely returns None

    # Orchestrator safely catches None and escalates
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    orch = RecoverAIOrchestrator(audit_logger=mock_audit_log, planner=planner, model=model)
    payment = PaymentRecord(payment_id="pay_orc_08", order_id="ord_08", amount=4000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_orc_08", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_08", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orch.process_payment(payment, events)
    assert outcome.firewall_decision == "ESCALATE"
    assert outcome.firewall_rule == "FIREWALL-010"
    assert outcome.final_outcome == "ESCALATED_TO_OPERATIONS"




# 9. LLM unavailable -> deterministic fallback
def test_llm_unavailable_deterministic_fallback():
    planner = AgenticRecoveryPlanner(llm_client=None)
    ctx = RecoveryContext(
        payment_id="pay_orc_09",
        financial_state="VERIFIED_LOST",
        failure_code="INSUFFICIENT_FUNDS",
        hardness="soft",
        amount=6000.0,
        customer_segment="high_value_repeat",
        expected_net_value=5500.0,
    )
    plan = planner.plan_recovery(ctx)
    assert plan is not None
    assert plan.action == RecoveryAction.PAYMENT_LINK


# 10. Agent recommends PAYMENT_LINK -> executor receives it
def test_agent_recommends_payment_link_executor_receives(orchestrator):
    payment = PaymentRecord(payment_id="pay_orc_10", order_id="ord_orc_10", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_orc_10", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_10", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.agent_action == "PAYMENT_LINK"
    assert outcome.execution_status == "SIMULATED_SUCCESS"
    assert outcome.execution_id is not None


# 11. Executor reports success but state remains VERIFIED_LOST -> final result RECOVERY_FAILED
def test_executor_success_state_verified_lost_recovery_failed(orchestrator):
    payment = PaymentRecord(payment_id="pay_orc_11", order_id="ord_orc_11", amount=15000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_orc_11", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_11", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=False)
    assert outcome.verification_state == "VERIFIED_LOST"
    assert outcome.final_outcome == "RECOVERY_FAILED"
    assert outcome.amount_recovered == 0.0


# 12. Executor reports success and state becomes ALREADY_RECOVERED -> RECOVERY_SUCCESS
def test_executor_success_state_already_recovered_recovery_success(orchestrator):
    payment = PaymentRecord(payment_id="pay_orc_12", order_id="ord_orc_12", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_orc_12", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_12", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, force_simulated_success=True)
    assert outcome.verification_state == "ALREADY_RECOVERED"
    assert outcome.final_outcome == "RECOVERY_SUCCESS"
    assert outcome.amount_recovered == 10000.0


# 13. Retry count = 3 -> another retry blocked
def test_retry_count_3_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_orc_13", order_id="ord_orc_13", amount=5000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_orc_13", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.firewall_rule in ["FIREWALL-005", "MAX_RETRY_LIMIT"]
    assert outcome.final_outcome == "MAX_RETRY_PROTECTION"


# 14. Retry count = 4 -> blocked
def test_retry_count_4_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_orc_14", order_id="ord_orc_14", amount=5000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_orc_14", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
        Event(event="payment.failed", payment_id="pay_orc_14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:04:05Z"),
    ]
    outcome = orchestrator.process_payment(payment, events, override_action=RecoveryAction.RETRY)
    assert outcome.firewall_decision == "STOP"
    assert outcome.final_outcome == "MAX_RETRY_PROTECTION"


# 15. LLM cannot modify Expected Net Value
def test_llm_cannot_modify_expected_net_value(mock_audit_log):
    tampering_llm = MockTamperingLLMClient()
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    orch = RecoverAIOrchestrator(audit_logger=mock_audit_log, llm_client=tampering_llm, model=model)

    payment = PaymentRecord(payment_id="pay_orc_15", order_id="ord_orc_15", amount=1000.0, method="upi", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_orc_15", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_15", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orch.process_payment(payment, events)
    # The outcome's expected net value must match the deterministic calculation, not 999,999
    assert outcome.expected_net_value < 1000.0
    assert outcome.expected_net_value != 999999.0


# 16. LLM cannot modify Financial State
def test_llm_cannot_modify_financial_state(mock_audit_log):
    tampering_llm = MockTamperingLLMClient()
    orch = RecoverAIOrchestrator(audit_logger=mock_audit_log, llm_client=tampering_llm)

    payment = PaymentRecord(payment_id="pay_orc_16", order_id="ord_orc_16", amount=5000.0)
    events = [
        Event(event="payment.created", payment_id="pay_orc_16", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_16", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    outcome = orch.process_payment(payment, events, force_simulated_success=False)
    # The source of truth remains the Financial State Engine
    assert outcome.source_of_truth == "FINANCIAL STATE ENGINE"
    assert outcome.verification_state == "VERIFIED_LOST"


# 17. Complete audit record generated
def test_complete_audit_record_generated(orchestrator, mock_audit_log):
    payment = PaymentRecord(payment_id="pay_orc_17", order_id="ord_orc_17", amount=8000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_orc_17", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_orc_17", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    orchestrator.process_payment(payment, events, force_simulated_success=True)

    records = mock_audit_log.get_records()
    assert len(records) >= 1
    last_rec = records[-1]
    assert last_rec.payment_id == "pay_orc_17"
    assert last_rec.initial_financial_state == "VERIFIED_LOST"
    assert last_rec.final_result == "RECOVERY_SUCCESS"
    assert last_rec.amount_recovered == 8000.0
