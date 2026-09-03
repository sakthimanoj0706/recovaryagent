import argparse
from typing import List
import hashlib
import json

from .models import ChaosScenario, ChaosResult, ChaosReport
from .scenarios import ChaosScenarios

def generate_fingerprint(results: List[ChaosResult]) -> str:
    data = [r.fingerprint_dict() for r in results]
    json_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_data.encode("utf-8")).hexdigest()

def run_chaos_suite(runs: int = 1) -> ChaosReport:
    # Run multiple times to ensure stability, but only keep last results for report
    for r in range(runs):
        results = ChaosScenarios.run_all()
        
    passed = sum(1 for r in results if r.is_pass)
    failed = len(results) - passed
    
    print("\n" + "="*50)
    print("CHAOS VALIDATION RESULTS")
    print("="*50)
    
    for r in results:
        print(f"SCENARIO: {r.scenario_id}")
        print(f"FAULT: {r.fault_type.value}")
        print(f"INITIAL STATE: {r.initial_state}")
        print(f"ADVISORY ACTION: {r.advisory_action or 'N/A'}")
        print(f"POLICY RESULT: {r.policy_result or 'N/A'}")
        print(f"FIREWALL RESULT: {r.firewall_result or 'N/A'}")
        print(f"PROVIDER RESULT: {r.provider_result or 'N/A'}")
        print(f"VERIFICATION RESULT: {r.verification_result or 'N/A'}")
        print(f"FINAL STATE: {r.final_state}")
        print(f"RECOVERED VALUE: {r.recovered_value}")
        print(f"PHANTOM REVENUE: {r.phantom_revenue}")
        print(f"DUPLICATE RECOVERY: {r.duplicate_recovery}")
        print(f"ACCOUNTING IMBALANCE: {r.accounting_imbalance}")
        print(f"PASS/FAIL: {'PASS' if r.is_pass else 'FAIL'}")
        print("-" * 30)

    fingerprint = generate_fingerprint(results)
    
    print(f"Total Scenarios: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Fingerprint (SHA-256): {fingerprint}")
    
    return ChaosReport(total_scenarios=len(results), passed=passed, failed=failed, results=results, fingerprint_sha256=fingerprint)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    
    run_chaos_suite(args.runs)
