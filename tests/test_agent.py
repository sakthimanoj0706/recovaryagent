"""
Automated unit and integration test suite for RecoverAI Agentic Recovery Planner & Recovery Firewall.
Covers all 20 required agent and firewall safety specifications.
"""

import sys
import json
from pathlib import Path
import pytest

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import FinancialState, PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import (
    RecoveryAction,
    RecoveryPriority,
    FirewallDecision,
    RecoveryContext,
    RecoveryPlan,
    AgentExecutionResult,
)
from agent.tools import RecoveryToolRegistry
from agent.firewall import RecoveryFirewall
from agent.audit import AuditLogger
from agent.llm import BaseLLMClient, GeminiLLMClient, DeterministicFallbackLLMClient
from agent.planner import AgentPlanner
from agent.orchestrator import RecoveryOrchestrator


class MockFailingLLMClient(BaseLLMClient):
    """Mock LLM client that fails or returns None."""
    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        return None


class MockCustomActionLLMClient(BaseLLMClient):
    """Mock LLM client proposing a specific action."""
    def __init__(self, action: RecoveryAction, reason: str = "Mock reason", confidence: float = 0.9):
        self.action = action
        self.reason = reason
        self.confidence = confidence

    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        return RecoveryPlan(
            payment_id=context.payment_id,
            action=self.action,
            priority=RecoveryPriority.MEDIUM,
            reason=self.reason,
            confidence=self.confidence,
            expected_net_value=context.expected_net_value or 0.0,
        )


@pytest.fixture
def mock_audit_log(tmp_path):
    log_file = tmp_path / "recovery_audit_test.jsonl"
    return AuditLogger(log_path=log_file)


@pytest.fixture
def orchestrator(mock_audit_log):
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return RecoveryOrchestrator(
        audit_logger=mock_audit_log,
        llm_client=DeterministicFallbackLLMClient(),
        model=model,
    )


# 1. VERIFIED_LOST enters agent
def test_verified_lost_enters_agent(orchestrator):
    payment = PaymentRecord(payment_id="pay_t01", order_id="ord_01", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_t01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t01", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "VERIFIED_LOST"
    assert result.expected_net_value > 0
    assert result.firewall_decision == FirewallDecision.APPROVED
    assert result.execution_status == "SIMULATED_SUCCESS"


# 2. ALREADY_RECOVERED blocked
def test_already_recovered_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_t02", order_id="ord_02", amount=5000.0)
    events = [
        Event(event="payment.created", payment_id="pay_t02", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_t02", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_t02", ts="2026-08-10T10:00:10Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "ALREADY_RECOVERED"
    assert result.firewall_decision == FirewallDecision.STOP
    assert result.firewall_rule == "FIREWALL-006"
    assert result.execution_status == "BLOCKED_BY_FIREWALL"
    assert result.final_result == "NO_ACTION"


# 3. UNCERTAIN blocked
def test_uncertain_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_t03", order_id="ord_03", amount=2500.0)
    events = [
        Event(event="payment.created", payment_id="pay_t03", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t03", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_t03", ts="2026-08-10T10:01:00Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "UNCERTAIN"
    assert result.firewall_decision == FirewallDecision.STOP
    assert result.firewall_rule == "FIREWALL-007"
    assert result.final_result == "WAIT"


# 4. EXCEPTION escalated
def test_exception_escalated(orchestrator):
    payment = PaymentRecord(
        payment_id="pay_t04",
        order_id="ord_04",
        amount=1999.0,
        has_settlement=True,
        settled_amount=1800.0,
        settlement_matches_order=False,
    )
    events = [
        Event(event="payment.created", payment_id="pay_t04", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_t04", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "EXCEPTION"
    assert result.firewall_decision == FirewallDecision.ESCALATE
    assert result.firewall_rule == "FIREWALL-008"
    assert result.final_result == "ESCALATED_TO_OPERATIONS"


# 5. Negative ENV blocked
def test_negative_env_blocked(orchestrator):
    payment = PaymentRecord(payment_id="pay_t05", order_id="ord_05", amount=30.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_t05", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t05", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "VERIFIED_LOST"
    assert result.expected_net_value <= 0
    assert result.firewall_decision == FirewallDecision.STOP
    assert result.firewall_rule == "FIREWALL-002"
    assert result.final_result in ["STOPPED_FIREWALL-002", "CORRECTLY_WITHHELD"]



# 6. Zero ENV blocked
def test_zero_env_blocked(orchestrator):
    context = RecoveryContext(
        payment_id="pay_t06",
        financial_state="VERIFIED_LOST",
        amount=80.0,
        expected_net_value=0.0,
        previous_attempts=1,
    )
    firewall_res = orchestrator.firewall.validate_action(context, proposed_action=RecoveryAction.PAYMENT_LINK)
    assert firewall_res.status == FirewallDecision.STOP
    assert firewall_res.rule_id == "FIREWALL-002"


# 7. Hard decline + RETRY blocked
def test_hard_decline_retry_blocked(orchestrator):
    context = RecoveryContext(
        payment_id="pay_t07",
        financial_state="VERIFIED_LOST",
        failure_reason="CARD_BLOCKED",
        hardness="hard",
        amount=5000.0,
        expected_net_value=2500.0,
        previous_attempts=1,
    )
    firewall_res = orchestrator.firewall.validate_action(context, proposed_action=RecoveryAction.RETRY)
    assert firewall_res.status == FirewallDecision.STOP
    assert firewall_res.rule_id == "FIREWALL-004"


# 8. Retry_count = 3 blocked
def test_retry_count_3_blocked(orchestrator):
    context = RecoveryContext(
        payment_id="pay_t08",
        financial_state="VERIFIED_LOST",
        failure_reason="TIMEOUT",
        hardness="soft",
        amount=5000.0,
        expected_net_value=3500.0,
        previous_attempts=3,
        retry_count=3,
    )
    firewall_res = orchestrator.firewall.validate_action(context, proposed_action=RecoveryAction.RETRY)
    assert firewall_res.status == FirewallDecision.STOP
    assert firewall_res.rule_id == "FIREWALL-005"


# 9. Duplicate action blocked
def test_duplicate_action_blocked(orchestrator):
    context = RecoveryContext(
        payment_id="pay_t09",
        financial_state="VERIFIED_LOST",
        failure_reason="INSUFFICIENT_FUNDS",
        hardness="soft",
        amount=5000.0,
        expected_net_value=3000.0,
        previous_attempts=1,
        previous_actions=["PAYMENT_LINK"],
    )
    firewall_res = orchestrator.firewall.validate_action(context, proposed_action=RecoveryAction.PAYMENT_LINK)
    assert firewall_res.status == FirewallDecision.STOP
    assert firewall_res.rule_id == "FIREWALL-009"


# 10. Invalid LLM output escalated
def test_invalid_llm_output_escalated(orchestrator):
    failing_planner = AgentPlanner(llm_client=MockFailingLLMClient())
    orch_with_failing_llm = RecoveryOrchestrator(
        audit_logger=orchestrator.audit_logger,
        planner=failing_planner,
        tools=orchestrator.tools,
        firewall=orchestrator.firewall,
    )
    payment = PaymentRecord(payment_id="pay_t10", order_id="ord_10", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_t10", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t10", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orch_with_failing_llm.run_lifecycle(payment, events)
    assert result.firewall_decision == FirewallDecision.ESCALATE
    assert result.firewall_rule == "FIREWALL-010"
    assert result.execution_status == "SIMULATED_ESCALATED"


# 11. Successful simulated action
def test_successful_simulated_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_t11", order_id="ord_11", amount=12000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_t11", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t11", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.execution_status == "SIMULATED_SUCCESS"
    assert result.execution_detail is not None
    assert result.execution_detail["status"] == "SIMULATED"


# 12. Failed simulated action / blocked
def test_failed_blocked_simulated_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_t12", order_id="ord_12", amount=5000.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_t12", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t12", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events, override_action=RecoveryAction.RETRY)
    assert result.firewall_decision == FirewallDecision.STOP
    assert result.execution_status == "BLOCKED_BY_FIREWALL"


# 13. Verification detects ALREADY_RECOVERED
def test_verification_detects_already_recovered(orchestrator):
    payment = PaymentRecord(payment_id="pay_t13", order_id="ord_13", amount=15000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_t13", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t13", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    post_events = [
        Event(event="payment.authorized", payment_id="pay_t13", ts="2026-08-10T10:15:00Z"),
        Event(event="payment.captured", payment_id="pay_t13", ts="2026-08-10T10:15:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events, post_action_events=post_events)
    assert result.verification_state == "ALREADY_RECOVERED"
    assert result.final_result == "RECOVERY_SUCCESS"


# 14. Verification detects VERIFIED_LOST
def test_verification_detects_verified_lost(orchestrator):
    payment = PaymentRecord(payment_id="pay_t14", order_id="ord_14", amount=8000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_t14", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t14", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.verification_state == "VERIFIED_LOST"
    assert result.final_result in ["ACTION_DISPATCHED_AWAITING_PAYMENT", "RECOVERY_FAILED"]



# 15. Verification detects UNCERTAIN
def test_verification_detects_uncertain(orchestrator):
    payment = PaymentRecord(payment_id="pay_t15", order_id="ord_15", amount=7500.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_t15", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t15", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    post_events = [
        Event(event="payment.pending", payment_id="pay_t15", ts="2026-08-10T10:05:00Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events, post_action_events=post_events)
    assert result.verification_state == "UNCERTAIN"
    assert result.final_result == "RECOVERY_WAITING_ASYNC"


# 16. Verification detects EXCEPTION
def test_verification_detects_exception(orchestrator):
    payment = PaymentRecord(payment_id="pay_t16", order_id="ord_16", amount=3000.0)
    events = [
        Event(event="payment.created", payment_id="pay_t16", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_t16", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_t16", ts="2026-08-10T10:00:10Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    assert result.financial_state == "EXCEPTION"
    assert result.final_result == "ESCALATED_TO_OPERATIONS"


# 17. Audit log generated
def test_audit_log_generated(orchestrator, mock_audit_log):
    payment = PaymentRecord(payment_id="pay_t17", order_id="ord_17", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_t17", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t17", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_lifecycle(payment, events)
    
    assert mock_audit_log.log_path.exists()
    with open(mock_audit_log.log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) >= 1
    last_log = json.loads(lines[-1])
    assert last_log["payment_id"] == "pay_t17"
    assert last_log["firewall_decision"] == "APPROVED"


# 18. Missing Gemini API key handled safely
def test_missing_gemini_api_key_safe():
    client = GeminiLLMClient(api_key="")
    context = RecoveryContext(
        payment_id="pay_t18",
        financial_state="VERIFIED_LOST",
        failure_reason="TIMEOUT",
        hardness="soft",
        amount=5000.0,
        expected_net_value=3000.0,
    )
    plan = client.generate_recovery_plan(context, list(RecoveryAction), "policy hints")
    assert plan is None  # Gracefully returns None instead of raising unhandled exception


# 19. Gemini API failure handled safely
def test_gemini_api_failure_handled_safely(orchestrator):
    failing_client = MockFailingLLMClient()
    planner = AgentPlanner(llm_client=failing_client)
    orch = RecoveryOrchestrator(
        audit_logger=orchestrator.audit_logger,
        planner=planner,
        tools=orchestrator.tools,
        firewall=orchestrator.firewall,
    )
    payment = PaymentRecord(payment_id="pay_t19", order_id="ord_19", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_t19", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t19", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    # When Gemini fails, orchestrator must NOT crash; it escalates safely
    result = orch.run_lifecycle(payment, events)
    assert result.firewall_decision == FirewallDecision.ESCALATE
    assert result.firewall_rule == "FIREWALL-010"


# 20. LLM cannot override firewall
def test_llm_cannot_override_firewall(orchestrator):
    # LLM recommends RETRY on a hard card block
    llm_proposing_unsafe_retry = MockCustomActionLLMClient(
        action=RecoveryAction.RETRY,
        reason="I believe this card block will succeed if we retry immediately.",
    )
    planner = AgentPlanner(llm_client=llm_proposing_unsafe_retry)
    orch = RecoveryOrchestrator(
        audit_logger=orchestrator.audit_logger,
        planner=planner,
        tools=orchestrator.tools,
        firewall=orchestrator.firewall,
    )
    payment = PaymentRecord(payment_id="pay_t20", order_id="ord_20", amount=5000.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_t20", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_t20", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = orch.run_lifecycle(payment, events)
    # The firewall vetoes the LLM's recommendation
    assert result.agent_action == RecoveryAction.RETRY
    assert result.firewall_decision == FirewallDecision.STOP
    assert result.firewall_rule == "FIREWALL-004"
    assert result.execution_status == "BLOCKED_BY_FIREWALL"
