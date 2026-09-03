"""
Step 20 — Observability Tests.

Tests for: observability models, latency recording, p50/p95/p99,
decision tracer, health checker, correlation IDs, INSUFFICIENT_DATA.
"""
import sys
import os
import time
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ.setdefault("AI_MODE", "demo")


# ── Models ────────────────────────────────────────────────────────────────────

def test_observability_event_has_correlation_id():
    from observability.models import ObservabilityEvent, OperationType, OperationStatus
    evt = ObservabilityEvent(
        correlation_id="corr_abc123",
        operation=OperationType.DECISION,
        status=OperationStatus.SUCCESS,
    )
    assert evt.correlation_id == "corr_abc123"
    assert evt.event_id.startswith("evt_")


def test_decision_trace_has_all_stage_fields():
    from observability.models import DecisionTrace
    trace = DecisionTrace(correlation_id="corr_xyz", payment_id="pay_test")
    assert trace.raw_event is None
    assert trace.financial_state is None
    assert trace.trace_id.startswith("trace_")


def test_health_status_enum():
    from observability.models import HealthStatus
    assert HealthStatus.HEALTHY == "APPLICATION_HEALTHY"
    assert HealthStatus.DEGRADED == "APPLICATION_DEGRADED"
    assert HealthStatus.UNHEALTHY == "APPLICATION_UNHEALTHY"


def test_latency_metrics_insufficient_data():
    from observability.models import LatencyMetrics
    m = LatencyMetrics.insufficient("test.op")
    assert m.status == "INSUFFICIENT_DATA"
    assert m.sample_count == 0
    assert m.p50_ms is None


# ── Latency Recorder ─────────────────────────────────────────────────────────

def test_latency_recorder_insufficient_data():
    from observability.metrics import LatencyRecorder
    recorder = LatencyRecorder()
    recorder.clear()
    recorder.record("my.op", 10.0)
    recorder.record("my.op", 20.0)
    # < 5 samples → INSUFFICIENT_DATA
    m = recorder.get_metrics("my.op")
    assert m.status == "INSUFFICIENT_DATA"
    assert m.sample_count == 2


def test_latency_recorder_computes_percentiles():
    from observability.metrics import LatencyRecorder
    recorder = LatencyRecorder()
    recorder.clear()
    # Record 20 samples
    for i in range(20):
        recorder.record("latency.test", float(i * 10))  # 0, 10, 20, ... 190 ms
    m = recorder.get_metrics("latency.test")
    assert m.status == "OK"
    assert m.sample_count == 20
    assert m.p50_ms is not None
    assert m.p95_ms is not None
    assert m.p99_ms is not None
    assert m.p50_ms <= m.p95_ms <= m.p99_ms


def test_latency_recorder_measure_context_manager():
    from observability.metrics import LatencyRecorder
    recorder = LatencyRecorder()
    recorder.clear()
    for _ in range(10):
        with recorder.measure("ctx.op"):
            time.sleep(0.001)
    m = recorder.get_metrics("ctx.op")
    assert m.sample_count == 10
    assert m.min_ms is not None
    assert m.min_ms >= 0.0


def test_latency_recorder_thread_safe():
    from observability.metrics import LatencyRecorder
    recorder = LatencyRecorder()
    recorder.clear()

    def record_many():
        for _ in range(100):
            recorder.record("thread.op", 5.0)

    threads = [threading.Thread(target=record_many) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert recorder.get_sample_count("thread.op") == 1000


def test_latency_recorder_unknown_operation_returns_insufficient():
    from observability.metrics import LatencyRecorder
    recorder = LatencyRecorder()
    recorder.clear()
    m = recorder.get_metrics("nonexistent.op")
    assert m.status == "INSUFFICIENT_DATA"


# ── Health Checker ────────────────────────────────────────────────────────────

def test_health_checker_returns_report():
    from observability.health import HealthChecker
    checker = HealthChecker()
    report = checker.check()
    assert report.overall_status in ["APPLICATION_HEALTHY", "APPLICATION_DEGRADED", "APPLICATION_UNHEALTHY"]
    assert len(report.dependencies) >= 4  # At least critical ones


def test_health_checker_critical_deps_present():
    from observability.health import HealthChecker
    from observability.models import DependencyClass
    checker = HealthChecker()
    report = checker.check()
    critical_names = {d.name for d in report.dependencies if d.dependency_class == DependencyClass.CRITICAL}
    # Must check all 4 critical subsystems
    expected = {"Financial State Engine", "Policy Engine", "Firewall", "Verification"}
    assert critical_names == expected


def test_health_checker_is_safe_to_execute():
    from observability.health import HealthChecker
    checker = HealthChecker()
    report = checker.check()
    # In demo environment, critical systems should always be available
    assert report.is_safe_to_execute() is True


def test_health_report_financial_invariants():
    from observability.health import HealthChecker
    checker = HealthChecker()
    report = checker.check()
    # Initial report has zero violations
    assert report.phantom_revenue == 0.0
    assert report.duplicate_recovery == 0
    assert report.accounting_imbalance == 0.0
    assert report.unsafe_executions == 0


# ── Observability Service ─────────────────────────────────────────────────────

def test_observability_service_record_event():
    from observability.service import ObservabilityService
    from observability.models import OperationType, OperationStatus
    svc = ObservabilityService()
    evt = svc.record_event(
        operation=OperationType.DECISION,
        status=OperationStatus.SUCCESS,
        correlation_id="corr_test_01",
        payment_id="pay_001",
        latency_ms=42.5,
    )
    assert evt is not None
    assert evt.payment_id == "pay_001"
    assert evt.latency_ms == 42.5


def test_observability_service_get_events_for_payment():
    from observability.service import ObservabilityService
    from observability.models import OperationType, OperationStatus
    svc = ObservabilityService()
    svc.record_event(OperationType.PAYMENT, OperationStatus.SUCCESS, payment_id="pay_filter_me")
    svc.record_event(OperationType.DECISION, OperationStatus.SUCCESS, payment_id="pay_filter_me")
    svc.record_event(OperationType.EXECUTION, OperationStatus.BLOCKED, payment_id="pay_different")
    evts = svc.get_events_for_payment("pay_filter_me")
    assert len(evts) >= 2
    assert all(e.payment_id == "pay_filter_me" for e in evts)


def test_observability_service_health_check():
    from observability.service import ObservabilityService
    svc = ObservabilityService()
    report = svc.health_check()
    assert report is not None
    assert report.overall_status is not None


# ── Decision Tracer ───────────────────────────────────────────────────────────

def test_decision_tracer_produces_trace():
    from observability.tracing import DecisionTracer
    from state_engine.models import PaymentRecord, Event
    tracer = DecisionTracer(correlation_id="corr_trace_test")
    payment = PaymentRecord(payment_id="pay_trace_01", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_trace_01", ts="2026-01-01T00:00:00Z"),
        Event(event="payment.failed", payment_id="pay_trace_01", error_code="TIMEOUT", hardness="soft", ts="2026-01-01T00:01:00Z"),
    ]
    trace = tracer.trace_payment(payment, events)
    assert trace.payment_id == "pay_trace_01"
    assert trace.correlation_id == "corr_trace_test"
    assert trace.financial_state is not None
    assert trace.failure_classification is not None
    assert trace.total_latency_ms is not None
    assert trace.total_latency_ms > 0


def test_decision_tracer_no_phantom_revenue():
    from observability.tracing import DecisionTracer
    from state_engine.models import PaymentRecord, Event
    tracer = DecisionTracer()
    payment = PaymentRecord(payment_id="pay_no_phantom", amount=9999.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_no_phantom", ts="2026-01-01T00:00:00Z"),
        Event(event="payment.failed", payment_id="pay_no_phantom", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-01-01T00:01:00Z"),
    ]
    trace = tracer.trace_payment(payment, events)
    # Trace cannot claim phantom revenue
    assert trace.outcome is not None
    assert trace.outcome["phantom_revenue"] == 0.0
    assert trace.outcome["duplicate_recovery"] == 0


def test_decision_tracer_already_recovered_state():
    from observability.tracing import DecisionTracer
    from state_engine.models import PaymentRecord, Event
    tracer = DecisionTracer()
    payment = PaymentRecord(payment_id="pay_recovered", amount=8000.0, method="upi")
    events = [
        Event(event="payment.created", payment_id="pay_recovered", ts="2026-01-01T00:00:00Z"),
        Event(event="payment.failed", payment_id="pay_recovered", error_code="TIMEOUT", ts="2026-01-01T00:01:00Z"),
        Event(event="payment.captured", payment_id="pay_recovered", ts="2026-01-01T00:02:00Z"),
    ]
    trace = tracer.trace_payment(payment, events)
    # Financial state must reflect ALREADY_RECOVERED
    assert trace.financial_state["state"] == "ALREADY_RECOVERED"


# ── Configuration Hasher ──────────────────────────────────────────────────────

def test_config_hasher_determinism():
    from proof.config_hasher import ConfigurationHasher
    hasher = ConfigurationHasher()
    h1 = hasher.compute_hash()
    h2 = hasher.compute_hash()
    assert h1 == h2, "Same config must produce same hash"


def test_config_hasher_sensitivity():
    from proof.config_hasher import ConfigurationHasher
    hasher = ConfigurationHasher()
    assert hasher.verify_sensitivity(), "Changed config must produce different hash"


def test_config_hasher_no_secrets_in_snapshot():
    from proof.config_hasher import ConfigurationHasher
    import json
    hasher = ConfigurationHasher()
    snap = hasher.snapshot()
    serialized = json.dumps(snap)
    # Ensure no secret values leak into snapshot
    assert "razorpay" not in serialized.lower()
    assert "api_key" not in serialized.lower()
    assert "password" not in serialized.lower()


# ── Final Proof Engine ────────────────────────────────────────────────────────

def test_final_proof_hash_determinism():
    from proof.final_proof import FinalProofEngine
    engine = FinalProofEngine(seed=42, scenario_count=100)
    mock_results = {
        "naive": {"net_value": 100000.0, "verified_recovery": 50000.0, "cost": 500.0, "violations": 10},
        "deterministic": {"net_value": 120000.0, "verified_recovery": 60000.0, "cost": 600.0, "violations": 0},
        "intelligent": {"net_value": 122000.0, "verified_recovery": 61000.0, "cost": 620.0, "violations": 0},
        "champion": {"net_value": 122000.0, "verified_recovery": 61000.0, "cost": 620.0, "violations": 0},
    }
    proof1 = engine.generate(mock_results)
    proof2 = engine.generate(mock_results)
    assert proof1.final_proof_sha256 == proof2.final_proof_sha256


def test_final_proof_hash_sensitivity():
    from proof.final_proof import FinalProofEngine
    engine = FinalProofEngine(seed=42, scenario_count=100)
    results_a = {
        "naive": {"net_value": 100000.0, "verified_recovery": 50000.0, "cost": 500.0, "violations": 10},
        "deterministic": {"net_value": 120000.0, "verified_recovery": 60000.0, "cost": 600.0, "violations": 0},
        "intelligent": {"net_value": 122000.0, "verified_recovery": 61000.0, "cost": 620.0, "violations": 0},
        "champion": {"net_value": 122000.0, "verified_recovery": 61000.0, "cost": 620.0, "violations": 0},
    }
    results_b = dict(results_a)
    results_b["champion"] = {"net_value": 130000.0, "verified_recovery": 65000.0, "cost": 700.0, "violations": 0}
    proof_a = engine.generate(results_a)
    proof_b = engine.generate(results_b)
    assert proof_a.final_proof_sha256 != proof_b.final_proof_sha256


def test_final_proof_invariants():
    from proof.final_proof import FinalProofEngine
    engine = FinalProofEngine(seed=42, scenario_count=100)
    results = {
        "naive": {"net_value": 100.0, "verified_recovery": 50.0, "cost": 5.0, "violations": 5},
        "deterministic": {"net_value": 120.0, "verified_recovery": 60.0, "cost": 6.0, "violations": 0},
        "intelligent": {"net_value": 120.0, "verified_recovery": 60.0, "cost": 6.0, "violations": 0},
        "champion": {"net_value": 120.0, "verified_recovery": 60.0, "cost": 6.0, "violations": 0},
    }
    proof = engine.generate(results)
    # All zero-tolerance invariants must pass
    assert proof.all_invariants_pass()
    assert proof.phantom_revenue == 0.0
    assert proof.duplicate_recovery == 0
    assert proof.accounting_imbalance == 0.0
    assert proof.unsafe_actions == 0
