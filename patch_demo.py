import re
with open("demo_full_system.py", "r", encoding="utf-8") as f:
    content = f.read()

patch = '''
    print("\\n" + "="*80)
    print("STEP 19: PRODUCTION INTELLIGENCE & CONTROL PLANE")
    print("="*80)
    print("Recording outcome of final decision...")
    
    from learning.models import RecoveryOutcome
    from learning.outcome_store import OutcomeStore
    from learning.metrics import LearningMetricsCalculator
    from challenger.service import ChallengerService
    import time
    
    store = OutcomeStore()
    o = RecoveryOutcome(
        decision_id="d_demo", payment_id="p_demo", strategy_id="determ_v1", strategy_version="1.0",
        failure_class="hard", candidate_action="RETRY", selected_action="RETRY",
        expected_recovery=100.0, expected_cost=5.0, expected_net_value=95.0, expected_probability=0.9,
        risk_loss=0.0, policy_result="APPROVED", firewall_result="APPROVED",
        execution_result="SUCCESS", verification_result="VERIFIED",
        actual_recovered_value=100.0, actual_cost=5.0, actual_net_value=95.0,
        recovery_success=True, recovery_latency=0.5, correlation_id="c_demo"
    )
    store.record(o)
    print("Outcome recorded to deterministic store.")
    
    metrics = LearningMetricsCalculator.calculate_expected_vs_actual(store.get_all())
    print(f"Expected Net Value: INR {metrics['expected_net_value']}")
    print(f"Actual Net Value: INR {metrics['actual_net_value']}")
    
    print("\\nEvaluating Offline Challenger Strategy...")
    time.sleep(1)
    
    svc = ChallengerService()
    svc.propose("chal_v1", "1.1")
    
    # Fast mock for demo purposes to avoid hanging on 1000 scenarios if unmocked
    import challenger.engine
    original_eval = challenger.engine.ChallengerEvaluationEngine.evaluate_4_way
    try:
        def mock_eval():
            return original_eval(seed=42, population_size=10)
        challenger.engine.ChallengerEvaluationEngine.evaluate_4_way = mock_eval
        chal = svc.evaluate("chal_v1")
        print(f"Challenger evaluation status: {chal.status.value}")
        print(f"Proof Hash: {chal.proof_hash}")
        
        if chal.status.value == "APPROVAL_REQUIRED":
            print("Challenger passed safety checks. Attempting PROMOTION...")
            svc.approve("chal_v1")
            svc.promote("chal_v1")
            print("Challenger PROMOTED successfully to Champion!")
    finally:
        challenger.engine.ChallengerEvaluationEngine.evaluate_4_way = original_eval
'''

# Find the place to inject it
content = content.replace('print("\\n" + "="*80)\n    print("DEMO COMPLETE: ALL 18 PHASES VERIFIED.")', patch + '\n    print("\\n" + "="*80)\n    print("DEMO COMPLETE: ALL 19 PHASES VERIFIED.")')

with open("demo_full_system.py", "w", encoding="utf-8") as f:
    f.write(content)
