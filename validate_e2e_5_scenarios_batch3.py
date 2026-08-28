import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event, FinancialState
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction, RecoveryPlan, RecoveryContext, AgentRecommendation, RecoveryPriority
from agent.orchestrator import RecoverAIOrchestrator
from agent.llm import get_default_llm_client, BaseLLMClient
from audit.logger import AuditLogger
from evaluate_engine import load_dataset


def print_scenario_card(num: int, title: str, outcome, extra_notes: str = ""):
    print(f"\n--- [SCENARIO {num}: {title.upper()}] ---")
    print(f"1.  Payment ID              : {outcome.payment_id}")
    print(f"    Amount                  : Rs. {outcome.amount:,.2f}")
    print(f"2.  Initial Financial State : {outcome.initial_state}")
    prob_str = (
        f"{outcome.recovery_probability:.4f} ({int(round(outcome.recovery_probability * 100))}%)"
        if outcome.recovery_probability is not None
        else "N/A (Bypassed)"
    )
    print(f"3.  Recovery Probability    : {prob_str}")
    env_str = (
        f"Rs. {outcome.expected_net_value:,.2f}"
        if outcome.expected_net_value is not None
        else "N/A (Bypassed)"
    )
    print(f"4.  Expected Net Value      : {env_str}")
    
    if outcome.expected_net_value is not None:
        if outcome.firewall_rule == "FIREWALL-002" or outcome.expected_net_value <= 0:
            econ_dec = "DO_NOT_RECOVER"
        else:
            econ_dec = "RECOVERY_WORTHWHILE"
    else:
        econ_dec = "N/A"
        
    print(f"    Economic Decision       : {econ_dec}")
    ag_action = outcome.agent_action or "NOT CALLED"
    print(f"5.  Agent Action            : {ag_action}")
    print(f"6.  Agent Reason            : {outcome.agent_reason or 'Agent not invoked.'}")
    print(f"7.  Firewall Decision       : {outcome.firewall_decision}")
    print(f"8.  Firewall Rule ID        : {outcome.firewall_rule or 'N/A'}")
    print(f"9.  Execution Status        : {outcome.execution_status}")
    print(f"10. Verification State      : {outcome.verification_state}")
    print(f"    Source of Truth         : {outcome.source_of_truth}")
    print(f"11. Final Result            : {outcome.final_outcome}")
    print(f"12. Amount Recovered        : Rs. {outcome.amount_recovered:,.2f}")
    print(f"13. Amount Withheld         : Rs. {outcome.amount_withheld:,.2f}")
    print(f"    Verdict Detail          : {outcome.reason}")
    if extra_notes:
        print(f"    Architectural Note      : {extra_notes}")


class MockProbabilityModel(RecoveryProbabilityModel):
    def predict_probability(self, features: Dict[str, Any]) -> float:
        amt = features.get("amount", 0.0)
        if amt == 800.0:
            return 0.1 # EV = 800 * 0.1 - 80 = 0.0
        if amt == 200000.0:
            return 0.10 # EV = 200000 * 0.1 - 80 = 19920.0
        return 0.5
    
    def explain(self, features: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        return {"top_factors": ["Mock explanation"]}


class FailingLLMClient(BaseLLMClient):
    def generate_recovery_plan(self, context, allowed_actions, policy_hints):
        raise ConnectionError("Live network failure: Timeout during LLM generation")


def run_e2e_validation_batch3():
    print("=" * 90)
    print("        RECOVERAI FULL END-TO-END SYSTEM VALIDATION (BATCH 3: SCENARIOS 11 - 15)      ")
    print("=" * 90)

    # Initialize components
    mock_model = MockProbabilityModel()
    
    test_audit_log_path = Path("logs") / "e2e_validation_batch3_audit.jsonl"
    if test_audit_log_path.exists():
        test_audit_log_path.unlink()

    audit_logger = AuditLogger(test_audit_log_path)
    llm_client = get_default_llm_client()
    
    orchestrator = RecoverAIOrchestrator(
        model=mock_model,
        llm_client=llm_client,
        audit_logger=audit_logger,
    )

    results = []
    
    # =========================================================================
    # SCENARIO 11: EXACT ZERO EXPECTED NET VALUE (BOUNDARY CASE)
    # =========================================================================
    print("\n" + "#" * 90)
    print("SCENARIO 11 — EXACT ZERO EXPECTED NET VALUE (BOUNDARY CASE)")
    print("#" * 90)
    pay11 = PaymentRecord(
        payment_id="pay_val_s11_011",
        order_id="order_val_s11_011",
        amount=800.0,
        method="upi",
        customer_segment="returning",
    )
    events11 = [
        Event(event="payment.created", payment_id=pay11.payment_id, order_id=pay11.order_id, ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay11.payment_id, order_id=pay11.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    res11 = orchestrator.process_payment(pay11, events11)
    results.append({
        "scenario": 11,
        "name": "Exact Zero EV",
        "outcome": res11,
    })
    print_scenario_card(11, "Exact Zero EV", res11, extra_notes="EV = exactly 0.00. Testing if EV <= 0 triggers DO_NOT_RECOVER.")


    # =========================================================================
    # SCENARIO 12: LLM PLANNER UNAVAILABLE, SAFE FALLBACK
    # =========================================================================
    print("\n" + "#" * 90)
    print("SCENARIO 12 — LLM PLANNER UNAVAILABLE, SAFE FALLBACK")
    print("#" * 90)
    
    failing_orchestrator = RecoverAIOrchestrator(
        model=mock_model,
        llm_client=FailingLLMClient(),
        audit_logger=audit_logger,
    )
    
    pay12 = PaymentRecord(
        payment_id="pay_val_s12_012",
        order_id="order_val_s12_012",
        amount=5000.0,
        method="upi",
        customer_segment="returning",
    )
    events12 = [
        Event(event="payment.created", payment_id=pay12.payment_id, order_id=pay12.order_id, ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay12.payment_id, order_id=pay12.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    res12 = failing_orchestrator.process_payment(pay12, events12)
    results.append({
        "scenario": 12,
        "name": "LLM Unavailable Fallback",
        "outcome": res12,
    })
    print_scenario_card(12, "LLM Unavailable Fallback", res12, extra_notes="Agent must not crash orchestrator, must fallback safely.")


    # =========================================================================
    # SCENARIO 13: ORDER-LEVEL MULTI-ATTEMPT RECOVERY
    # =========================================================================
    print("\n" + "#" * 90)
    print("SCENARIO 13 — ORDER-LEVEL MULTI-ATTEMPT RECOVERY")
    print("#" * 90)
    
    payments, dataset_events, _ = load_dataset()
    pay13 = next(p for p in payments if p.payment_id == "pay_96272e9e82e14c")
    order_events13 = [e for e in dataset_events if e.order_id == "order_ade981aae9ff4a"]
    pay_events13 = [e for e in dataset_events if e.payment_id == "pay_96272e9e82e14c"]
    
    res13 = orchestrator.process_payment(pay13, pay_events13, order_events=order_events13)
    results.append({
        "scenario": 13,
        "name": "Order-Level Recovery Check",
        "outcome": res13,
    })
    print_scenario_card(13, "Order-Level Recovery Check", res13, extra_notes="STATE-RULE-002: Another successful payment attempt for the same order.")


    # =========================================================================
    # SCENARIO 14: HIGH-VALUE PAYMENT, LOW PROBABILITY, STILL POSITIVE EV
    # =========================================================================
    print("\n" + "#" * 90)
    print("SCENARIO 14 — HIGH-VALUE PAYMENT, LOW PROBABILITY, STILL POSITIVE EV")
    print("#" * 90)
    pay14 = PaymentRecord(
        payment_id="pay_val_s14_014",
        order_id="order_val_s14_014",
        amount=200000.0,
        method="upi",
        customer_segment="returning",
    )
    events14 = [
        Event(event="payment.created", payment_id=pay14.payment_id, order_id=pay14.order_id, ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay14.payment_id, order_id=pay14.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    res14 = orchestrator.process_payment(pay14, events14)
    results.append({
        "scenario": 14,
        "name": "High-Value Low-Prob (+EV)",
        "outcome": res14,
    })
    print_scenario_card(14, "High-Value Low-Prob (+EV)", res14, extra_notes="Testing EV formula weighs amount x probability properly.")


    # =========================================================================
    # SCENARIO 15: ESCALATED CASE LATER RESOLVED BY HUMAN, RE-ENTERS SYSTEM
    # =========================================================================
    print("\n" + "#" * 90)
    print("SCENARIO 15 — ESCALATED CASE LATER RESOLVED BY HUMAN, RE-ENTERS SYSTEM")
    print("#" * 90)
    pay15 = PaymentRecord(
        payment_id="pay_val_s15_015",
        order_id="order_val_s15_015",
        amount=8500.0,
        method="card",
        customer_segment="returning",
        has_settlement=True,
        settled_amount=7500.0,
        settlement_matches_order=False,
    )
    events15 = [
        Event(event="payment.created", payment_id=pay15.payment_id, order_id=pay15.order_id, ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id=pay15.payment_id, order_id=pay15.order_id, ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id=pay15.payment_id, order_id=pay15.order_id, ts="2026-08-10T10:00:10Z"),
    ]
    res15_phase1 = orchestrator.process_payment(pay15, events15)
    print(f"[Phase 1: EXCEPTION] State: {res15_phase1.initial_state} | Action: {res15_phase1.agent_action} | Final: {res15_phase1.final_outcome}")

    # Phase 2: Human resolves it
    pay15_resolved = PaymentRecord(
        payment_id=pay15.payment_id,
        order_id=pay15.order_id,
        amount=pay15.amount,
        method=pay15.method,
        customer_segment=pay15.customer_segment,
        has_settlement=True,
        settled_amount=8500.0,  # RESOLVED
        settlement_matches_order=True,  # RESOLVED
    )
    # Clear idempotency history so we can observe re-evaluation
    orchestrator._action_history.get(pay15.payment_id, set()).clear()
    res15_phase2 = orchestrator.process_payment(pay15_resolved, events15)
    print(f"[Phase 2: RESOLVED] State: {res15_phase2.initial_state} | Action: {res15_phase2.agent_action} | Final: {res15_phase2.final_outcome}")
    
    results.append({
        "scenario": 15,
        "name": "Escalated Then Resolved",
        "outcome": res15_phase2,
    })
    print_scenario_card(15, "Escalated Then Resolved", res15_phase2, extra_notes="Human fixed mismatch, state engine re-evaluates as ALREADY_RECOVERED.")

    # =========================================================================
    # END-TO-END VALIDATION TABLE (BATCH 3)
    # =========================================================================
    print("\n" + "=" * 90)
    print("                      END-TO-END VALIDATION TABLE (BATCH 3: SCENARIOS 11-15)              ")
    print("=" * 90)
    print(f"{'Scenario':<10} | {'Initial State':<18} | {'Agent':<14} | {'Firewall':<10} | {'Execution':<10} | {'Verified State':<18} | {'Final Result':<24}")
    print("-" * 90)
    for r in results:
        sc_num = r["scenario"]
        o = r["outcome"]
        init_st = o.initial_state
        ag_act = o.agent_action or "NOT CALLED"
        fw_dec = o.firewall_decision
        exec_st = (
            "SUCCESS"
            if o.execution_status == "SIMULATED_SUCCESS"
            else ("FAILED" if o.execution_status == "SIMULATED_FAILURE" else "NONE")
        )
        v_st = o.verification_state
        f_res = o.final_outcome
        print(f"{sc_num:<10} | {init_st:<18} | {ag_act:<14} | {fw_dec:<10} | {exec_st:<10} | {v_st:<18} | {f_res:<24}")
    print("=" * 90)

    # =========================================================================
    # EXPLICIT SAFETY & ARCHITECTURAL ASSERTIONS
    # =========================================================================
    print("\n" + "=" * 90)
    print("                        EXPLICIT SAFETY & ARCHITECTURAL ASSERTIONS                        ")
    print("=" * 90)

    # Assertion 11: Exact Zero Expected Net Value (Boundary Case)
    assert res11.expected_net_value == 0.0, f"Expected EV = 0.0, got {res11.expected_net_value}"
    assert res11.final_outcome == "CORRECTLY_WITHHELD", f"Expected CORRECTLY_WITHHELD, got {res11.final_outcome}"
    assert res11.agent_action == "STOP", f"Expected agent_action=STOP, got {res11.agent_action}"
    assert res11.firewall_rule == "FIREWALL-002", f"Expected FIREWALL-002 (Negative EV), got {res11.firewall_rule}"
    print("✔ ASSERTION 11 (Scenario 11): EV == 0.0 triggers DO_NOT_RECOVER correctly via FIREWALL-002 (operator is <= 0).")

    # Assertion 12: LLM Planner Unavailable, Safe Fallback
    assert res12.agent_action == "ESCALATE", f"Expected fallback to ESCALATE, got {res12.agent_action}"
    assert "LLM planner service unavailable" in res12.agent_reason, f"Unexpected fallback reason: {res12.agent_reason}"
    assert res12.amount_recovered == 0.0, "Must not falsely claim recovery."
    print("✔ ASSERTION 12 (Scenario 12): Agent Planner failure caught gracefully; falls back safely to ESCALATE without crashing.")

    # Assertion 13: Order-Level Multi-Attempt Recovery
    assert res13.initial_state == "ALREADY_RECOVERED", f"Expected ALREADY_RECOVERED, got {res13.initial_state}"
    assert "STATE-RULE-002" in res13.decision_trace["prove"]["state_rule_id"], "Should be evaluated as STATE-RULE-002"
    assert res13.agent_action == "STOP", f"Expected STOP, got {res13.agent_action}"
    print(f"✔ ASSERTION 13 (Scenario 13): Specific failed payment_id skipped because order-level check via STATE-RULE-002 confirms success.")

    # Assertion 14: High-Value Low-Prob (+EV)
    assert res14.expected_net_value > 0, f"Expected positive EV, got {res14.expected_net_value}"
    assert res14.firewall_decision == "APPROVED", f"Expected APPROVED, got {res14.firewall_decision}"
    print(f"✔ ASSERTION 14 (Scenario 14): Low probability (10%) but high value (Rs. 200,000) generates +EV (Rs. {res14.expected_net_value:,.2f}) and passes firewall.")

    # Assertion 15: Escalated Case Later Resolved
    assert res15_phase1.initial_state == "EXCEPTION", f"Phase 1 should be EXCEPTION, got {res15_phase1.initial_state}"
    assert res15_phase2.initial_state == "ALREADY_RECOVERED", f"Phase 2 should be ALREADY_RECOVERED, got {res15_phase2.initial_state}"
    
    s15_audit_records = [rec for rec in audit_logger.get_records() if rec.payment_id == "pay_val_s15_015"]
    assert len(s15_audit_records) == 2, f"Expected 2 audit log records for s15, found {len(s15_audit_records)}"
    assert s15_audit_records[0].initial_financial_state == "EXCEPTION"
    assert s15_audit_records[1].initial_financial_state == "ALREADY_RECOVERED"
    print("✔ ASSERTION 15 (Scenario 15): Manual resolution of EXCEPTION successfully re-evaluates to ALREADY_RECOVERED, preserving audit history.")

    print("\nALL ASSERTIONS PASSED.\n")

if __name__ == "__main__":
    run_e2e_validation_batch3()
