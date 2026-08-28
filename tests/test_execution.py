"""
Unit tests for RecoverAI Execution and Verification components.
"""

import sys
from pathlib import Path
import pytest

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from agent.models import RecoveryAction, RecoveryPlan, RecoveryContext
from execution.simulator import SyntheticSimulationEngine
from execution.executor import ActionExecutor
from execution.verifier import RecoveryVerifier
from execution.outcome import determine_final_outcome, FinalOutcome
from agent.models import FirewallResult, FirewallDecision


def test_simulation_reproducibility():
    sim1 = SyntheticSimulationEngine(simulation_seed=123)
    sim2 = SyntheticSimulationEngine(simulation_seed=123)

    ctx = RecoveryContext(
        payment_id="pay_sim_01",
        financial_state="VERIFIED_LOST",
        amount=5000.0,
        customer_segment="returning",
    )

    s1, m1, ev1 = sim1.simulate_outcome(ctx, RecoveryAction.PAYMENT_LINK)
    s2, m2, ev2 = sim2.simulate_outcome(ctx, RecoveryAction.PAYMENT_LINK)

    assert s1 == s2
    assert m1 == m2
    assert len(ev1) == len(ev2)


def test_action_executor_payment_link():
    executor = ActionExecutor()
    ctx = RecoveryContext(
        payment_id="pay_exec_link_01",
        financial_state="VERIFIED_LOST",
        amount=4000.0,
    )
    plan = RecoveryPlan(
        payment_id="pay_exec_link_01",
        action=RecoveryAction.PAYMENT_LINK,
        reason="Testing payment link",
        confidence=0.9,
        expected_net_value=3500.0,
    )
    res = executor.execute(plan, ctx, force_success=True)
    assert res.action == RecoveryAction.PAYMENT_LINK
    assert res.simulated_success is True
    assert res.status == "SIMULATED"
    assert "https://pay.recoverai.io/link/" in res.metadata["payment_url"]
    assert any(e.event == "payment.captured" for e in res.generated_events)


def test_action_executor_stop():
    executor = ActionExecutor()
    ctx = RecoveryContext(
        payment_id="pay_exec_stop_01",
        financial_state="VERIFIED_LOST",
        amount=100.0,
    )
    plan = RecoveryPlan(
        payment_id="pay_exec_stop_01",
        action=RecoveryAction.STOP,
        reason="Negative ENV stop",
        confidence=1.0,
        expected_net_value=-50.0,
    )
    res = executor.execute(plan, ctx)
    assert res.action == RecoveryAction.STOP
    assert res.simulated_success is False
    assert len(res.generated_events) == 0


def test_verifier_detects_already_recovered():
    verifier = RecoveryVerifier()
    payment = PaymentRecord(payment_id="pay_ver_01", order_id="ord_ver_01", amount=10000.0)
    original_events = [
        Event(event="payment.created", payment_id="pay_ver_01", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_ver_01", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    executor = ActionExecutor()
    plan = RecoveryPlan(
        payment_id="pay_ver_01",
        action=RecoveryAction.PAYMENT_LINK,
        reason="Testing verification",
        confidence=0.9,
        expected_net_value=9000.0,
    )
    exec_res = executor.execute(plan, RecoveryContext(payment_id="pay_ver_01", financial_state="VERIFIED_LOST", amount=10000.0), force_success=True)
    v_res = verifier.verify(payment, original_events, exec_res)

    assert v_res.verified_financial_state == "ALREADY_RECOVERED"
    assert v_res.is_verified_recovery is True
    assert v_res.source_of_truth == "FINANCIAL STATE ENGINE"


def test_determine_final_outcome_calculation():
    fw_approved = FirewallResult(status=FirewallDecision.APPROVED, action=RecoveryAction.PAYMENT_LINK, reason="Approved")
    
    # Success case
    from execution.verifier import VerificationResult
    v_success = VerificationResult(
        payment_id="pay_calc_01",
        agent_action="PAYMENT_LINK",
        agent_claimed_success=True,
        verified_financial_state="ALREADY_RECOVERED",
        reason="Captured",
        is_verified_recovery=True,
    )
    outcome, rec, withh, _ = determine_final_outcome("VERIFIED_LOST", fw_approved, v_success, amount=5000.0)
    assert outcome == "RECOVERY_SUCCESS"
    assert rec == 5000.0
    assert withh == 0.0

    # Withheld case (e.g. Negative ENV)
    fw_stopped = FirewallResult(status=FirewallDecision.STOP, action=RecoveryAction.STOP, rule_id="FIREWALL-002", reason="Negative ENV")
    outcome_w, rec_w, withh_w, _ = determine_final_outcome("VERIFIED_LOST", fw_stopped, None, amount=3000.0, expected_net_value=-50.0)
    assert outcome_w == "CORRECTLY_WITHHELD"
    assert rec_w == 0.0
    assert withh_w == 3000.0
