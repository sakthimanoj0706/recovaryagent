import pytest
from chaos.runner import run_chaos_suite

def test_chaos_scenarios_all_pass():
    report = run_chaos_suite(runs=1)
    
    assert report.failed == 0, f"Chaos validation failed: {report.failed} scenarios failed."
    assert report.passed == report.total_scenarios
    
def test_chaos_determinism_and_repeatability():
    report1 = run_chaos_suite(runs=1)
    report2 = run_chaos_suite(runs=2)
    
    assert report1.fingerprint_sha256 == report2.fingerprint_sha256
    
def test_webhook_idempotency_in_chaos():
    report = run_chaos_suite(runs=1)
    # The duplicate webhook scenario should be marked pass
    wb_results = [r for r in report.results if r.scenario_id == "C-WB-1"]
    assert len(wb_results) == 1
    assert wb_results[0].is_pass

def test_concurrency_accounting_in_chaos():
    report = run_chaos_suite(runs=1)
    conc_results = [r for r in report.results if r.scenario_id == "C-CONC-1"]
    assert len(conc_results) == 1
    assert conc_results[0].is_pass
    assert conc_results[0].phantom_revenue == 0.0
    assert conc_results[0].duplicate_recovery == 0.0
    assert conc_results[0].accounting_imbalance == 0.0
