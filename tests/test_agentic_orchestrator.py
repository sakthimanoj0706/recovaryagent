"""
Unit and Integration Tests for Production-Style Agentic Recovery Orchestrator.
Validates all 15 core safety and agentic loop requirements:
1. test_agent_cannot_override_financial_state
2. test_agent_cannot_override_env
3. test_agent_cannot_bypass_firewall
4. test_agent_cannot_execute_unknown_action
5. test_agent_llm_failure_falls_back_to_escalate
6. test_agent_malformed_json_falls_back_safely
7. test_agent_max_iterations
8. test_agent_replans_after_failed_action
9. test_agent_stops_after_recovery
10. test_agent_stops_on_uncertain
11. test_agent_escalates_exception
12. test_agent_cannot_repeat_duplicate_action
13. test_agent_respects_max_retries
14. test_agent_verifies_every_action
15. test_agent_cannot_claim_recovery_without_ledger_confirmation
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction, RecoveryPriority, RecoveryPlan, RecoveryContext
from agent.schemas import AgentAction, AgentRunResult, AgentStepRecord
from agent.orchestrator import AgenticRecoveryOrchestrator
from agent.planner import AgenticRecoveryPlanner
from agent.llm import BaseLLMClient, DeterministicFallbackLLMClient
from audit.logger import AuditLogger


class MockMaliciousLLMClient(BaseLLMClient):
    """Mock LLM that tries to perform forbidden actions or alter state."""
    def __init__(self, proposed_action="OVERRIDE_FIREWALL", fake_env=999999.0, fake_state="ALREADY_RECOVERED"):
        self.proposed_action = proposed_action
        self.fake_env = fake_env
        self.fake_state = fake_state
        self.mode = "demo"

    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        return RecoveryPlan(
            action=RecoveryAction.RETRY,
            reason="Malicious attempt to bypass constraints",
            confidence=0.99,
        )


class MockFailingLLMClient(BaseLLMClient):
    """Mock LLM that fails with an exception."""
    mode = "demo"
    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        raise RuntimeError("LLM API endpoint unavailable.")


class MockMalformedJsonLLMClient(BaseLLMClient):
    """Mock LLM returning invalid object."""
    mode = "demo"
    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        return None


@pytest.fixture
def orchestrator(tmp_path):
    log_file = tmp_path / "test_agentic_audit.jsonl"
    model_path = Path(__file__).parent.parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    return AgenticRecoveryOrchestrator(
        audit_logger=AuditLogger(log_path=log_file),
        llm_client=DeterministicFallbackLLMClient(),
        model=model,
    )


# 1. test_agent_cannot_override_financial_state
def test_agent_cannot_override_financial_state(orchestrator):
    # Payment already captured
    payment = PaymentRecord(payment_id="pay_sec_01", amount=25000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_sec_01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_01", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.authorized", payment_id="pay_sec_01", ts="2026-08-10T10:30:00Z"),
        Event(event="payment.captured", payment_id="pay_sec_01", ts="2026-08-10T10:30:08Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events)
    # Authority check: Financial State Engine proves ALREADY_RECOVERED; LLM cannot change it
    assert result.financial_state == "ALREADY_RECOVERED"
    assert result.firewall_decision == "STOP"
    assert result.final_result == "CORRECTLY_WITHHELD"
    assert result.amount_withheld == 25000.0
    assert result.amount_recovered == 0.0


# 2. test_agent_cannot_override_env
def test_agent_cannot_override_env(orchestrator):
    # Payment with negative ENV (Rs. 20 where recovery cost exceeds value)
    payment = PaymentRecord(payment_id="pay_sec_02", amount=20.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_sec_02", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_02", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events)
    assert result.expected_net_value is not None
    assert result.expected_net_value <= 0.0
    assert result.firewall_decision == "STOP"
    assert result.final_result == "CORRECTLY_WITHHELD"
    assert result.amount_withheld == 20.0



# 3. test_agent_cannot_bypass_firewall
def test_agent_cannot_bypass_firewall(orchestrator):
    # Hard decline CARD_BLOCKED
    payment = PaymentRecord(payment_id="pay_sec_03", amount=12000.0, method="card", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_sec_03", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_03", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events)
    # Even with positive economics, hard decline prevents automated RETRY
    assert result.firewall_decision in ["APPROVED", "STOP"]
    if result.agent_action == "RETRY":
        assert result.firewall_decision == "STOP"
    else:
        assert result.agent_action in ["PAYMENT_LINK", "ESCALATE", "STOP"]


# 4. test_agent_cannot_execute_unknown_action
def test_agent_cannot_execute_unknown_action(orchestrator):
    # Propose invalid action
    is_valid, err = orchestrator.policy_engine.validate_action_space("REFUND_ALL_MONEY")
    assert not is_valid
    assert "not in allowed action space" in err

    is_valid2, _ = orchestrator.policy_engine.validate_action_space("MARK_RECOVERED")
    assert not is_valid2


# 5. test_agent_llm_failure_falls_back_to_escalate
def test_agent_llm_failure_falls_back_to_escalate(tmp_path):
    failing_orch = AgenticRecoveryOrchestrator(
        audit_logger=AuditLogger(log_path=tmp_path / "failing_audit.jsonl"),
        planner=AgenticRecoveryPlanner(llm_client=MockFailingLLMClient()),
    )
    payment = PaymentRecord(payment_id="pay_sec_05", amount=10000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_sec_05", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_05", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = failing_orch.run_recovery_agent(payment, events)
    assert result.agent_action == "ESCALATE"
    assert "Escalated" in result.agent_reason or "Escalate" in result.agent_reason or "escalat" in result.agent_reason.lower()


# 6. test_agent_malformed_json_falls_back_safely
def test_agent_malformed_json_falls_back_safely(tmp_path):
    malformed_orch = AgenticRecoveryOrchestrator(
        audit_logger=AuditLogger(log_path=tmp_path / "malformed_audit.jsonl"),
        planner=AgenticRecoveryPlanner(llm_client=MockMalformedJsonLLMClient()),
    )
    payment = PaymentRecord(payment_id="pay_sec_06", amount=8000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_sec_06", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_06", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = malformed_orch.run_recovery_agent(payment, events)
    assert result.agent_action == "ESCALATE"


# 7. test_agent_max_iterations
def test_agent_max_iterations(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_07", amount=10000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_sec_07", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_07", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events, force_simulated_success=False)
    assert result.iterations <= orchestrator.MAX_AGENT_STEPS
    assert result.iterations <= 3


# 8. test_agent_replans_after_failed_action
def test_agent_replans_after_failed_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_08", amount=15000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_sec_08", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_08", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    # Multi-step scenario: Step 1 fails, Step 2 replans and succeeds
    result = orchestrator.run_recovery_agent(payment, events, multi_step_scenario=True)
    assert result.iterations >= 2
    assert len(result.steps_taken) >= 2
    assert result.steps_taken[0].execution_status == "SIMULATED_FAILURE"
    assert result.steps_taken[1].execution_status == "SIMULATED_SUCCESS"
    assert result.final_result == "RECOVERY_SUCCESS"
    assert result.amount_recovered == 15000.0


# 9. test_agent_stops_after_recovery
def test_agent_stops_after_recovery(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_09", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_sec_09", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_09", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events, force_simulated_success=True)
    assert result.final_result == "RECOVERY_SUCCESS"
    assert result.iterations == 1
    assert result.steps_taken[-1].next_step == "STOP_RECOVERED"


# 10. test_agent_stops_on_uncertain
def test_agent_stops_on_uncertain(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_10", amount=6000.0, method="upi", scenario="uncertain_pending")
    events = [
        Event(event="payment.created", payment_id="pay_sec_10", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_10", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_sec_10", ts="2026-08-10T10:00:10Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events)
    assert result.financial_state == "UNCERTAIN"
    assert result.final_result == "WAIT"
    assert result.amount_pending == 6000.0
    assert result.amount_withheld == 0.0


# 11. test_agent_escalates_exception
def test_agent_escalates_exception(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_11", amount=8500.0, method="card", has_settlement=True, settled_amount=7000.0, settlement_matches_order=False)
    events = [
        Event(event="payment.created", payment_id="pay_sec_11", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_sec_11", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_sec_11", ts="2026-08-10T10:00:10Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events)
    assert result.financial_state == "EXCEPTION"
    assert result.final_result == "ESCALATED_TO_OPERATIONS"
    assert result.amount_escalated == 8500.0


# 12. test_agent_cannot_repeat_duplicate_action
def test_agent_cannot_repeat_duplicate_action(tmp_path):
    class StaticActionLLM(BaseLLMClient):
        mode = "demo"
        def generate_recovery_plan(self, context, allowed_actions, policy_hints):
            return RecoveryPlan(action=RecoveryAction.PAYMENT_LINK, rationale="Always propose payment link")

    orch = AgenticRecoveryOrchestrator(
        audit_logger=AuditLogger(log_path=tmp_path / "dup_audit.jsonl"),
        planner=AgenticRecoveryPlanner(llm_client=StaticActionLLM()),
    )
    payment = PaymentRecord(payment_id="pay_sec_12", amount=7000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_sec_12", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_12", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    res1 = orch.run_recovery_agent(payment, events, force_simulated_success=False)
    assert res1.firewall_decision == "APPROVED"

    res2 = orch.run_recovery_agent(payment, events)
    assert res2.firewall_decision == "STOP"
    assert res2.final_result == "DUPLICATE_ACTION_BLOCKED"



# 13. test_agent_respects_max_retries
def test_agent_respects_max_retries(tmp_path):
    retry_planner = AgenticRecoveryPlanner(llm_client=MockMaliciousLLMClient(proposed_action="RETRY"))
    retry_orch = AgenticRecoveryOrchestrator(
        audit_logger=AuditLogger(log_path=tmp_path / "max_retry_audit.jsonl"),
        planner=retry_planner,
    )
    payment = PaymentRecord(payment_id="pay_sec_13", amount=4500.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_sec_13", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_sec_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_sec_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_sec_13", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
    ]
    result = retry_orch.run_recovery_agent(payment, events)
    assert result.firewall_decision == "STOP"
    assert result.final_result in ["MAX_RETRY_PROTECTION", "SAFE_STOP"]



# 14. test_agent_verifies_every_action
def test_agent_verifies_every_action(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_14", amount=10000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_sec_14", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_14", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events, force_simulated_success=True)
    # Every step record includes verification state confirmed by State Engine
    for step in result.steps_taken:
        assert step.verification_state is not None
        assert step.verification_source == "FINANCIAL STATE ENGINE"


# 15. test_agent_cannot_claim_recovery_without_ledger_confirmation
def test_agent_cannot_claim_recovery_without_ledger_confirmation(orchestrator):
    payment = PaymentRecord(payment_id="pay_sec_15_fresh", amount=15000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_sec_15_fresh", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_sec_15_fresh", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = orchestrator.run_recovery_agent(payment, events, force_simulated_success=False)
    # Action was attempted, but ledger proves VERIFIED_LOST -> recovery is RECOVERY_FAILED, amount recovered is 0
    assert result.verification_state == "VERIFIED_LOST"
    assert result.final_result == "RECOVERY_FAILED"
    assert result.amount_recovered == 0.0

