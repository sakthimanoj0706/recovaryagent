"""
RecoverAI — Autonomous Agentic Replanning Demo Scenario.
Validates the complete autonomous multi-step closed-loop recovery:

Payment: Rs. 15,000
Initial State: VERIFIED_LOST
Probability: 92%
ENV: Positive (+Rs. 13,728)

Stage 1:
- Agent Proposal: PAYMENT_LINK
- Firewall: APPROVED
- Action Executor: SIMULATED_FAILURE (customer abandoned checkout)
- Verifier: VERIFIED_LOST (ledger confirms money still unrecovered)

Stage 2 (Autonomous Replanning):
- Agent Observes: PAYMENT_LINK failed
- Agent Replans: REMINDER
- Firewall: APPROVED
- Action Executor: SIMULATED_SUCCESS
- Verifier: ALREADY_RECOVERED (ledger confirms payment captured)

Final Outcome: RECOVERY_SUCCESS (Rs. 15,000.00 Recovered)
"""

import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.orchestrator import AgenticRecoveryOrchestrator
from agent.llm import DeterministicFallbackLLMClient
from audit.logger import AuditLogger


def run_agentic_demo():
    print("=" * 80)
    print("        RecoverAI — PRODUCTION-STYLE AGENTIC RECOVERY ORCHESTRATOR DEMO         ")
    print("              'Prove the money. Prioritize the chase. Recover it.'             ")
    print("=" * 80)

    model_path = Path(__file__).parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    audit_logger = AuditLogger(log_path=Path(__file__).parent / "logs" / "agentic_demo_audit.jsonl")

    orchestrator = AgenticRecoveryOrchestrator(
        model=model,
        llm_client=DeterministicFallbackLLMClient(),
        audit_logger=audit_logger,
    )

    payment = PaymentRecord(
        payment_id="pay_agentic_demo_15k",
        order_id="order_demo_15k",
        amount=15000.0,
        currency="INR",
        method="upi",
        customer_segment="high_value_repeat",
    )

    events = [
        Event(event="payment.created", payment_id=payment.payment_id, order_id=payment.order_id, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=payment.payment_id, order_id=payment.order_id, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]

    print("\n--- [PAYMENT INGESTION] ---")
    print(f"Payment ID              : {payment.payment_id}")
    print(f"Amount                  : Rs. {payment.amount:,.2f}")
    print(f"Customer Segment        : {payment.customer_segment}")
    print(f"Failure Reason          : INSUFFICIENT_FUNDS (soft decline)")

    print("\n>>> Launching Autonomous Bounded Recovery Loop (MAX_AGENT_STEPS = 3)...")

    # Run multi-step scenario
    result = orchestrator.run_recovery_agent(payment, events, multi_step_scenario=True)

    print(f"\nTotal Iterations Taken  : {result.iterations}")
    print(f"Run ID                  : {result.run_id}")

    for idx, step in enumerate(result.steps_taken, start=1):
        print(f"\n--------------------------------------------------------------------------------")
        print(f"STEP {step.step_number} [{step.stage}]")
        print(f"--------------------------------------------------------------------------------")
        print(f"1. Observation           : Financial State = {step.observation.get('financial_state')}")
        print(f"2. Advisory Proposal     : {step.agent_proposal} (Confidence: {step.confidence})")
        print(f"3. Advisory Rationale    : {step.agent_reason}")
        print(f"4. Policy Check          : {step.policy_verdict}")
        print(f"5. Recovery Firewall     : {step.firewall_verdict} ({step.firewall_reason})")
        print(f"6. Action Execution      : {step.execution_status} (ID: {step.execution_id})")
        print(f"7. Ledger Verification   : {step.verification_state} (Source: {step.verification_source})")
        print(f"8. Next Action Decision  : {step.next_step}")

    print("\n" + "=" * 80)
    print("                             FINAL AGENT RUN RESULT                             ")
    print("=" * 80)
    print(f"Initial Financial State : {result.financial_state}")
    print(f"Recovery Probability    : {result.recovery_probability:.2%}" if result.recovery_probability else "N/A")
    print(f"Expected Net Value      : Rs. {result.expected_net_value:,.2f}" if result.expected_net_value else "N/A")
    print(f"Final Agent Action      : {result.agent_action}")
    print(f"Final Execution Status  : {result.execution_status}")
    print(f"Verified Ledger State   : {result.verification_state}")
    print(f"Final Result            : {result.final_result}")
    print(f"Amount Recovered        : Rs. {result.amount_recovered:,.2f}")
    print(f"Amount Withheld         : Rs. {result.amount_withheld:,.2f}")
    print("=" * 80)

    # Explicit Safety Assertions
    assert result.iterations == 2, f"Expected exactly 2 iterations, got {result.iterations}"
    assert result.steps_taken[0].execution_status == "SIMULATED_FAILURE", "Step 1 execution should have failed"
    assert result.steps_taken[0].verification_state == "VERIFIED_LOST", "Step 1 ledger verification should prove VERIFIED_LOST"
    assert result.steps_taken[1].execution_status == "SIMULATED_SUCCESS", "Step 2 execution should succeed"
    assert result.steps_taken[1].verification_state == "ALREADY_RECOVERED", "Step 2 ledger verification must prove ALREADY_RECOVERED"
    assert result.final_result == "RECOVERY_SUCCESS", "Final result must be RECOVERY_SUCCESS"
    assert result.amount_recovered == 15000.0, "Expected Rs. 15,000.00 recovered"

    print("\n[PASS] ALL AGENTIC CLOSED-LOOP REPLANNING ASSERTIONS PASSED (100% SUCCESS)\n")


if __name__ == "__main__":
    run_agentic_demo()

