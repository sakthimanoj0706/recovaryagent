import pytest
import math
from learning.models import RecoveryOutcome, DriftStatus
from learning.outcome_store import OutcomeStore
from learning.metrics import LearningMetricsCalculator
from learning.drift import DriftDetector

def test_outcome_store():
    store = OutcomeStore()
    store.clear()
    
    o = RecoveryOutcome(
        decision_id="d1", payment_id="p1", strategy_id="s1", strategy_version="v1",
        failure_class="hard", candidate_action="RETRY", selected_action="RETRY",
        expected_recovery=100.0, expected_cost=5.0, expected_net_value=95.0, expected_probability=0.9,
        risk_loss=0.0, policy_result="APPROVED", firewall_result="APPROVED",
        execution_result="SUCCESS", verification_result="VERIFIED",
        actual_recovered_value=100.0, actual_cost=5.0, actual_net_value=95.0,
        recovery_success=True, recovery_latency=0.5, correlation_id="c1"
    )
    store.record(o)
    assert len(store.get_all()) == 1

def test_metrics_decision_quality():
    o = RecoveryOutcome(
        decision_id="d1", payment_id="p1", strategy_id="s1", strategy_version="v1",
        failure_class="hard", candidate_action="RETRY", selected_action="RETRY",
        expected_recovery=100.0, expected_cost=5.0, expected_net_value=95.0, expected_probability=0.9,
        risk_loss=0.0, policy_result="APPROVED", firewall_result="APPROVED",
        execution_result="SUCCESS", verification_result="VERIFIED",
        actual_recovered_value=100.0, actual_cost=5.0, actual_net_value=95.0,
        recovery_success=True, recovery_latency=0.5, correlation_id="c1"
    )
    dq = LearningMetricsCalculator.calculate_decision_quality(o)
    assert math.isclose(dq.total_score, 1.0)  # Perfect match

def test_drift_detection():
    baseline = [
        RecoveryOutcome(
            decision_id="d1", payment_id="p1", strategy_id="s1", strategy_version="v1",
            failure_class="soft", candidate_action="RETRY", selected_action="RETRY",
            expected_recovery=100.0, expected_cost=5.0, expected_net_value=95.0, expected_probability=0.9,
            risk_loss=0.0, policy_result="APPROVED", firewall_result="APPROVED",
            execution_result="SUCCESS", verification_result="VERIFIED",
            actual_recovered_value=100.0, actual_cost=5.0, actual_net_value=95.0,
            recovery_success=True, recovery_latency=0.5, correlation_id="c1"
        )
    ]
    current = baseline[:]
    drift = DriftDetector.detect_failure_distribution_drift(baseline, current)
    assert drift.status == DriftStatus.STABLE
