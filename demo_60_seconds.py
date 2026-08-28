"""
RecoverAI — 60-Second Emergency Judge Demo (Step 8).
Delivers the core thesis in under 60 seconds with offline-deterministic execution:
"FAILED != LOST. The Financial State Engine is the source of truth."
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event
from state_engine.engine import FinancialStateEngine
from recovery.model import RecoveryProbabilityModel
from agent.orchestrator import AgenticRecoveryOrchestrator


def run_60_second_demo():
    print("=" * 80)
    print("        RecoverAI — 60-SECOND FINTECH EXECUTIVE DEMONSTRATION           ")
    print("        Thesis: 'Failed != Lost. The Ledger is Authoritative.'         ")
    print("=" * 80)

    state_engine = FinancialStateEngine()
    model_path = Path(__file__).parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    orchestrator = AgenticRecoveryOrchestrator(state_engine=state_engine, model=model)

    pid = "pay_hero_flipflop_25k"
    amount = 25000.0

    print(f"\n[SCENARIO: HIGH-VALUE PAYMENT FLIP-FLOP (Rs. {amount:,.2f})]")
    print("A customer attempts a Rs. 25,000 checkout on mobile UPI.")

    # 1. Payment created and failed
    print("\n1. [T+0s] payment.created -> payment.failed (BANK_TIMEOUT)")
    evs_step1 = [
        Event(event="payment.created", payment_id=pid, amount=amount, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pid, amount=amount, error_code="BANK_TIMEOUT", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    eval_1 = state_engine.evaluate_payment(PaymentRecord(payment_id=pid, amount=amount), evs_step1)
    print(f"   -> Financial State Engine Verdict: {eval_1.state.value} (Money verified lost)")
    print(f"   -> Standard payment retry systems would immediately dispatch duplicate charge.")

    # 2. Late authorization arrives
    print("\n2. [T+45s] payment.authorized (Asynchronous Late-Authorization Flip-Flop)")
    evs_step2 = evs_step1 + [
        Event(event="payment.authorized", payment_id=pid, amount=amount, late_authorization=True, ts="2026-08-28T10:00:45Z"),
    ]
    outcome = orchestrator.process_payment(PaymentRecord(payment_id=pid, amount=amount), evs_step2)
    print(f"   -> Financial State Engine Re-evaluates: {outcome.initial_state} (STATE-RULE-001)")
    print(f"   -> Advisory Agent Action              : {outcome.agent_action} (Prohibited)")
    print(f"   -> Recovery Firewall Gate             : {outcome.firewall_decision} (Rule: {outcome.firewall_rule})")
    print(f"   -> Verification Ledger Source of Truth: {outcome.source_of_truth}")
    print(f"   -> Closed-Loop Outcome                : {outcome.final_outcome}")
    print(f"   -> Amount Correctly Withheld          : Rs. {outcome.amount_withheld:,.2f}")

    assert outcome.initial_state == "ALREADY_RECOVERED"
    assert outcome.amount_withheld == 25000.0
    assert outcome.amount_recovered == 0.0

    print("\n" + "=" * 80)
    print("                           THE PITCH SUMMARY                            ")
    print("=" * 80)
    print("• What naive systems do  : Blindly retry, double-charging the customer Rs. 25,000.")
    print("• What RecoverAI does    : Proves financial truth on the ledger and withholds action.")
    print("• Money Protected        : Rs. 25,000.00 saved from double-charging.")
    print("• Fundamental Invariant  : 'FAILED != LOST'")
    print("=" * 80)
    print("\n[PASS] 60-SECOND DEMO COMPLETED IN SIMULATION MODE (100% SUCCESS)\n")


if __name__ == "__main__":
    run_60_second_demo()
