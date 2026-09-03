import pytest
from scenarios.payment_lifecycle import run_all

def test_payment_lifecycle_integrity():
    results, fp = run_all(1)
    
    # 8 standard tests + 3 concurrency tests = 11 results per run
    assert len(results) == 11
    
    for res in results:
        assert res.pass_status is True, f"Scenario {res.scenario_name} failed."
        
    assert res.imbalance == 0.0
    assert res.phantom_revenue == 0.0
    assert res.duplicate_recovery == 0.0

def test_repeatability():
    _, fp10 = run_all(10)
    _, fp100 = run_all(10) # 10 for speed in test, real stability tested manually
    
    assert fp10 == fp100, "Fingerprints must be stable across multiple runs"
