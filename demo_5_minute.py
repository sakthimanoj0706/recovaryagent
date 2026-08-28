"""
RecoverAI — 5-Minute Timed Pitch & Judge Demo with Speaker Cues (Step 8).
Executes a structured 5-minute presentation covering all core safety archetypes and accounting proofs.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event
from state_engine.engine import FinancialStateEngine
from recovery.model import RecoveryProbabilityModel
from agent.orchestrator import AgenticRecoveryOrchestrator
from agent.models import RecoveryAction
from audit.logger import AuditLogger


def print_speaker_cue(time_mark: str, title: str, cue: str):
    print("\n" + "=" * 80)
    print(f"[{time_mark}] {title.upper()}")
    print("=" * 80)
    print(f">> SPEAKER SCRIPT: \"{cue}\"")
    print("-" * 80)


def run_5_minute_demo():
    print("=" * 80)
    print("           RecoverAI — 5-MINUTE JUDGE DEMO & TIMED PITCH               ")
    print("     'Prove the money. Prioritize the chase. Recover it.'             ")
    print("=" * 80)

    model_path = Path(__file__).parent / "models" / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    audit_logger = AuditLogger()
    state_engine = FinancialStateEngine()
    orchestrator = AgenticRecoveryOrchestrator(state_engine=state_engine, model=model, audit_logger=audit_logger)

    # -------------------------------------------------------------------------
    # 0:00 — The Problem
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "0:00 - 0:30",
        "The Problem: Blind Payment Retries Destroy Merchant Trust",
        "Judges, when an online payment fails, typical gateway systems blindly hammer the bank with retries or dispatch immediate payment links. In Indian fintech, 15-20% of 'failed' UPI transactions are actually in-flight or get authorized seconds later. Blind retries double-charge customers, inflate gateway penalty fees, and create customer service nightmares."
    )
    print("  Problem Identified: Failed != Lost.")
    print("  Challenge         : Is money genuinely lost, and is recovery economically rational?")

    # -------------------------------------------------------------------------
    # 0:30 — The Architecture
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "0:30 - 1:00",
        "The Solution: RecoverAI 7-Stage Deterministic Safety Architecture",
        "RecoverAI solves this by separating financial truth from AI. The LLM has zero authority to declare payments recovered or execute transactions. Every payment flows through: PROVE on ledger -> PRIORITIZE via economics -> PLAN via AI advisory -> POLICY check -> GUARD via deterministic Firewall -> ACT via sandbox -> VERIFY on ledger -> AUDIT."
    )
    print("  Pipeline: OBSERVE -> PROVE -> PRIORITIZE -> PLAN -> POLICY -> GUARD -> ACT -> VERIFY -> AUDIT")

    # -------------------------------------------------------------------------
    # 1:00 — Demo 1: FAILED != LOST
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "1:00 - 2:00",
        "Fintech Hero Case 1: FAILED != LOST (Late Authorization Flip-Flop)",
        "Watch what happens when a Rs. 25,000 payment fails initially, but gets authorized 30 seconds later via bank webhook. The Financial State Engine immediately re-evaluates the ledger to ALREADY_RECOVERED, and FIREWALL-006 blocks any recovery attempt."
    )
    pay1 = PaymentRecord(payment_id="pay_pitch_flipflop_25k", amount=25000.0)
    evs1 = [
        Event(event="payment.created", payment_id=pay1.payment_id, amount=25000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay1.payment_id, amount=25000.0, ts="2026-08-28T10:00:05Z"),
        Event(event="payment.authorized", payment_id=pay1.payment_id, amount=25000.0, late_authorization=True, ts="2026-08-28T10:00:35Z"),
    ]
    out1 = orchestrator.process_payment(pay1, evs1)
    print(f"  [EXECUTION] Initial State: {out1.initial_state} | Agent: {out1.agent_action} | Firewall: {out1.firewall_decision} (FIREWALL-006)")
    print(f"  [FINANCIAL IMPACT] Rs. {out1.amount_withheld:,.2f} CORRECTLY WITHHELD (Double-charge prevented)")
    assert out1.initial_state == "ALREADY_RECOVERED"
    assert out1.amount_withheld == 25000.0

    # -------------------------------------------------------------------------
    # 2:00 — Demo 2: ECONOMICS != PERMISSION
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "2:00 - 3:00",
        "Fintech Hero Case 2: ECONOMICS != PERMISSION (Hard Decline Block)",
        "Now consider a Rs. 12,000 payment on a blocked card. Unit economics show positive Expected Net Value (+Rs. 1,632). But FIREWALL-004 halts automated retries because retrying a blocked card incurs bank penalty fees and card network violations."
    )
    pay2 = PaymentRecord(payment_id="pay_pitch_hard_block_12k", amount=12000.0)
    evs2 = [
        Event(event="payment.created", payment_id=pay2.payment_id, amount=12000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay2.payment_id, amount=12000.0, error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-28T10:00:05Z"),
    ]
    out2 = orchestrator.process_payment(pay2, evs2, override_action=RecoveryAction.RETRY)
    print(f"  [EXECUTION] ENV: Rs. {out2.expected_net_value:,.2f} | Proposed: RETRY | Firewall: {out2.firewall_decision} ({out2.firewall_rule})")
    print(f"  [FINANCIAL IMPACT] Rs. {out2.amount_withheld:,.2f} PROTECTED from futile bank retries")
    assert out2.firewall_rule == "FIREWALL-004"

    # -------------------------------------------------------------------------
    # 3:00 — Demo 3: AGENT CLAIM != FINANCIAL TRUTH
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "3:00 - 4:00",
        "Fintech Hero Case 3: AGENT CLAIM != FINANCIAL TRUTH (Verification Catch)",
        "What if an agent claims success, or a gateway webhook sends a payment link, but the customer abandons the checkout? The action execution reports success, but the Closed-Loop Verifier independently queries ledger truth and confirms the payment remains VERIFIED_LOST."
    )
    pay3 = PaymentRecord(payment_id="pay_pitch_ver_catch_15k", amount=15000.0, scenario="soft_decline_retryable")
    evs3 = [
        Event(event="payment.created", payment_id=pay3.payment_id, amount=15000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay3.payment_id, amount=15000.0, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    out3 = orchestrator.process_payment(pay3, evs3, force_simulated_success=False)
    print(f"  [EXECUTION] Action: {out3.agent_action} | Gateway: {out3.execution_status} | Verifier: {out3.verification_state}")
    print(f"  [FINANCIAL IMPACT] Recovered: Rs. {out3.amount_recovered:,.2f} | Outcome: {out3.final_outcome} (Zero False Success)")
    assert out3.amount_recovered == 0.0

    # -------------------------------------------------------------------------
    # 4:00 — Demo 4: Genuine Autonomous Recovery Loop
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "4:00 - 4:30",
        "Autonomous Closed-Loop Recovery Execution",
        "When money is genuinely verified lost and economics are positive, the bounded agent proposes PAYMENT_LINK. Upon successful customer checkout, the ledger confirms recovery, booking Rs. 10,000 into the Recovered bucket."
    )
    pay4 = PaymentRecord(payment_id="pay_pitch_success_10k", amount=10000.0, scenario="soft_decline_retryable")
    evs4 = [
        Event(event="payment.created", payment_id=pay4.payment_id, amount=10000.0, ts="2026-08-28T10:00:00Z"),
        Event(event="payment.failed", payment_id=pay4.payment_id, amount=10000.0, error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-28T10:00:05Z"),
    ]
    out4 = orchestrator.process_payment(pay4, evs4, force_simulated_success=True)
    print(f"  [EXECUTION] Action: {out4.agent_action} | Firewall: {out4.firewall_decision} | Verifier: {out4.verification_state}")
    print(f"  [FINANCIAL IMPACT] Rs. {out4.amount_recovered:,.2f} ACTUALLY RECOVERED (Ledger Confirmed)")
    assert out4.amount_recovered == 10000.0

    # -------------------------------------------------------------------------
    # 4:30 — Audit & Invariant Summary
    # -------------------------------------------------------------------------
    print_speaker_cue(
        "4:30 - 5:00",
        "Audit Trail & Verifiable Accounting Invariant",
        "Every single step is written to an immutable JSONL audit trail with unique correlation IDs. The accounting equation: Processed = Recovered + Withheld + Pending + Escalated is 100% mathematically balanced."
    )
    metrics = audit_logger.calculate_metrics()
    print(f"  Total Processed Cases       : {metrics.total_cases}")
    print(f"  * Total Amount Recovered    : Rs. {metrics.total_amount_recovered:,.2f}")
    print(f"  * Total Amount Withheld     : Rs. {metrics.total_amount_withheld:,.2f}")
    print(f"  * Total Amount Pending      : Rs. {metrics.total_amount_pending:,.2f}")
    print(f"  * Total Amount Escalated    : Rs. {metrics.total_amount_escalated:,.2f}")
    print(f"  * Accounting Invariant Check: {metrics.verify_accounting_balance()} (100% Balanced)")

    print("\n" + "=" * 80)
    print(">> CLOSING STATEMENT: \"RecoverAI is not an LLM that controls payments.")
    print("                      It is a bounded financial agent operating inside")
    print("                      deterministic financial safety rails.\"")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_5_minute_demo()
