"""
RecoverAI - Closed-Loop Execution & Verification Interactive Demo.

Demonstrates the core closed loop:
PROVE -> PRIORITIZE -> PLAN -> FIREWALL -> ACT -> VERIFY -> OUTCOME -> AUDIT

Showcases 6 distinct scenarios:
1. Successful Recovery Path
2. Failed Recovery (Verification is Source of Truth - Never Trust the Agent)
3. Late Authorization (FAILED != LOST)
4. Economically Irrational Recovery (Negative ENV -> Correctly Withheld)
5. Hard Decline Safety Rule (FIREWALL-004 Safe Stop)
6. Maximum Retry Limit Protection (FIREWALL-005)
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction
from agent.orchestrator import RecoverAIOrchestrator
from agent.llm import get_default_llm_client
from audit.logger import AuditLogger


def print_closed_loop_card(outcome, scenario_num: int, title: str):
    print("\n" + "=" * 65, flush=True)
    print(f" SCENARIO {scenario_num}: {title.upper()}", flush=True)
    print("=" * 65, flush=True)
    print("==================================================", flush=True)
    print("                 RECOVERAI", flush=True)
    print("       PROVE THE MONEY. RECOVER IT.", flush=True)
    print("==================================================", flush=True)
    print("PAYMENT", flush=True)
    print("-----------------------------------------------", flush=True)
    print(f"Payment ID        : {outcome.payment_id}", flush=True)
    print(f"Amount            : Rs. {outcome.amount:,.2f}", flush=True)
    print(f"Initial State     : {outcome.initial_state}", flush=True)
    print(flush=True)

    print("RECOVERY INTELLIGENCE", flush=True)
    print("-----------------------------------------------", flush=True)
    prob_str = f"{int(round(outcome.recovery_probability * 100))}%" if outcome.recovery_probability is not None else "N/A"
    env_str = f"Rs. {outcome.expected_net_value:,.2f}" if outcome.expected_net_value is not None else "N/A"
    print(f"Probability       : {prob_str}", flush=True)
    print(f"Expected Net Value: {env_str}", flush=True)
    dec_str = "RECOVERY_WORTHWHILE" if outcome.expected_net_value and outcome.expected_net_value > 0 else "DO_NOT_RECOVER"
    print(f"Decision          : {dec_str}", flush=True)
    print(flush=True)

    print("AGENT", flush=True)
    print("-----------------------------------------------", flush=True)
    print(f"Action            : {outcome.agent_action or 'N/A'}", flush=True)
    print(f"Reason            : {outcome.agent_reason or 'No action formulated.'}", flush=True)
    print(flush=True)

    print("RECOVERY FIREWALL", flush=True)
    print("-----------------------------------------------", flush=True)
    print(f"Decision          : {outcome.firewall_decision}", flush=True)
    if outcome.firewall_rule:
        print(f"Rule              : {outcome.firewall_rule}", flush=True)
    if outcome.firewall_reason:
        print(f"Reason            : {outcome.firewall_reason}", flush=True)
    print(flush=True)

    print("EXECUTION", flush=True)
    print("-----------------------------------------------", flush=True)
    print(f"Mode              : {'SYNTHETIC SIMULATION' if outcome.simulation_flag else 'LIVE'}", flush=True)
    if outcome.execution_id:
        print(f"Execution ID      : {outcome.execution_id}", flush=True)
    print(f"Status            : {outcome.execution_status}", flush=True)
    if outcome.execution_message:
        print(f"Detail            : {outcome.execution_message}", flush=True)
    print(flush=True)

    print("VERIFICATION", flush=True)
    print("-----------------------------------------------", flush=True)
    claimed = "SUCCESS" if outcome.execution_status == "SIMULATED_SUCCESS" else "BLOCKED / FAILED"
    print(f"Agent Claim       : {claimed}", flush=True)
    print(f"Verified State    : {outcome.verification_state}", flush=True)
    print(f"Source of Truth   : {outcome.source_of_truth}", flush=True)
    print(flush=True)

    print("FINAL RESULT", flush=True)
    print("-----------------------------------------------", flush=True)
    if outcome.final_outcome == "RECOVERY_SUCCESS":
        print(f"✓ RECOVERY SUCCESS", flush=True)
        print(f"Amount Recovered  : Rs. {outcome.amount_recovered:,.2f}", flush=True)
    elif outcome.final_outcome == "RECOVERY_FAILED":
        print(f"✗ RECOVERY FAILED (Money remains unrecovered)", flush=True)
        print(f"Amount Recovered  : Rs. 0.00", flush=True)
    else:
        print(f"🛑 ACTION BLOCKED ({outcome.final_outcome})", flush=True)
        print(f"Reason            : {outcome.reason}", flush=True)
        print(f"Rs. {outcome.amount_withheld:,.2f} correctly withheld.", flush=True)
    print("==================================================\n", flush=True)


def run_demo():
    print("*" * 80, flush=True)
    print(" RecoverAI — CLOSED-LOOP EXECUTION & VERIFICATION DEMO ", flush=True)
    print(" 'Prove the money. Prioritize the chase. Recover it.' ", flush=True)
    print("*" * 80, flush=True)

    # Ingest ML model & LLM
    model_path = Path("models") / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    llm_client = get_default_llm_client()
    audit_logger = AuditLogger(Path("logs") / "recovery_audit.jsonl")
    orchestrator = RecoverAIOrchestrator(
        llm_client=llm_client,
        model=model,
        audit_logger=audit_logger,
    )

    outcomes = []

    # -------------------------------------------------------------------------
    # SCENARIO 1: SUCCESSFUL RECOVERY
    # -------------------------------------------------------------------------
    pay1 = PaymentRecord(
        payment_id="pay_demo_001",
        order_id="order_demo_001",
        amount=10000.0,
        method="upi",
        customer_segment="high_value_repeat",
    )
    events1 = [
        Event(event="payment.created", payment_id="pay_demo_001", order_id="order_demo_001", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_001", order_id="order_demo_001", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:06Z"),
    ]
    res1 = orchestrator.process_payment(pay1, events1, force_simulated_success=True)
    outcomes.append(res1)
    print_closed_loop_card(res1, 1, "Successful Recovery Path (Payment Link -> Captured)")

    # -------------------------------------------------------------------------
    # SCENARIO 2: FAILED RECOVERY (NEVER TRUST THE AGENT)
    # -------------------------------------------------------------------------
    pay2 = PaymentRecord(
        payment_id="pay_demo_002",
        order_id="order_demo_002",
        amount=8500.0,
        method="upi",
        customer_segment="returning",
    )
    events2 = [
        Event(event="payment.created", payment_id="pay_demo_002", order_id="order_demo_002", ts="2026-08-10T10:30:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_002", order_id="order_demo_002", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:30:06Z"),
    ]
    res2 = orchestrator.process_payment(pay2, events2, force_simulated_success=False)
    outcomes.append(res2)
    print_closed_loop_card(res2, 2, "Failed Recovery Detected (State Remains VERIFIED_LOST)")

    # -------------------------------------------------------------------------
    # SCENARIO 3: LATE AUTHORIZATION (FAILED != LOST)
    # -------------------------------------------------------------------------
    pay3 = PaymentRecord(
        payment_id="pay_demo_003",
        order_id="order_demo_003",
        amount=7499.0,
        method="upi",
        customer_segment="returning",
    )
    events3 = [
        Event(event="payment.created", payment_id="pay_demo_003", order_id="order_demo_003", ts="2026-08-10T11:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_003", order_id="order_demo_003", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T11:00:06Z"),
        Event(event="payment.authorized", payment_id="pay_demo_003", order_id="order_demo_003", ts="2026-08-10T11:05:00Z"),
        Event(event="payment.captured", payment_id="pay_demo_003", order_id="order_demo_003", ts="2026-08-10T11:05:08Z"),
    ]
    res3 = orchestrator.process_payment(pay3, events3)
    outcomes.append(res3)
    print_closed_loop_card(res3, 3, "Late Authorization (FAILED != LOST -> No Action)")

    # -------------------------------------------------------------------------
    # SCENARIO 4: NEGATIVE ECONOMICS (CORRECTLY WITHHELD)
    # -------------------------------------------------------------------------
    pay4 = PaymentRecord(
        payment_id="pay_demo_004",
        order_id="order_demo_004",
        amount=50.0,
        method="card",
        customer_segment="new",
    )
    events4 = [
        Event(event="payment.created", payment_id="pay_demo_004", order_id="order_demo_004", ts="2026-08-10T12:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_004", order_id="order_demo_004", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T12:00:05Z"),
    ]
    res4 = orchestrator.process_payment(pay4, events4)
    outcomes.append(res4)
    print_closed_loop_card(res4, 4, "Negative Economics (DO_NOT_RECOVER -> Correctly Withheld)")

    # -------------------------------------------------------------------------
    # SCENARIO 5: HARD DECLINE SAFETY RULE
    # -------------------------------------------------------------------------
    pay5 = PaymentRecord(
        payment_id="pay_demo_005",
        order_id="order_demo_005",
        amount=12000.0,
        method="card",
        customer_segment="returning",
    )
    events5 = [
        Event(event="payment.created", payment_id="pay_demo_005", order_id="order_demo_005", ts="2026-08-10T13:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_005", order_id="order_demo_005", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T13:00:05Z"),
    ]
    res5 = orchestrator.process_payment(pay5, events5, override_action=RecoveryAction.RETRY)
    outcomes.append(res5)
    print_closed_loop_card(res5, 5, "Hard Decline Safety Rule (FIREWALL-004 Blocks RETRY)")

    # -------------------------------------------------------------------------
    # SCENARIO 6: RETRY LIMIT PROTECTION
    # -------------------------------------------------------------------------
    pay6 = PaymentRecord(
        payment_id="pay_demo_006",
        order_id="order_demo_006",
        amount=5000.0,
        method="upi",
        customer_segment="returning",
    )
    events6 = [
        Event(event="payment.created", payment_id="pay_demo_006", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_006", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.failed", payment_id="pay_demo_006", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:01:05Z"),
        Event(event="payment.failed", payment_id="pay_demo_006", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:02:05Z"),
        Event(event="payment.failed", payment_id="pay_demo_006", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:03:05Z"),
    ]
    res6 = orchestrator.process_payment(pay6, events6, override_action=RecoveryAction.RETRY)
    outcomes.append(res6)
    print_closed_loop_card(res6, 6, "Maximum Retry Limit Reached (Attempt 4 Blocked by FIREWALL-005)")

    # -------------------------------------------------------------------------
    # HERO METRICS SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print("                  RECOVERAI METRICS DASHBOARD SUMMARY", flush=True)
    print("=" * 80, flush=True)
    print(f"Total Cases Processed         : {len(outcomes)}", flush=True)
    print(f"Recovery Attempts Dispatched  : {sum(1 for o in outcomes if o.agent_action in ['PAYMENT_LINK', 'RETRY', 'REMINDER'] and o.firewall_decision == 'APPROVED')}", flush=True)
    print(f"Successful Recoveries         : {sum(1 for o in outcomes if o.final_outcome == 'RECOVERY_SUCCESS')}", flush=True)
    print(f"Failed Recoveries             : {sum(1 for o in outcomes if o.final_outcome == 'RECOVERY_FAILED')}", flush=True)
    print(f"Firewall Policy Blocks        : {sum(1 for o in outcomes if o.firewall_decision in ['STOP', 'BLOCKED'])}", flush=True)
    print("--------------------------------------------------------------------------------", flush=True)
    print(f"🏆 HERO METRIC #1 — ₹ ACTUALLY RECOVERED : Rs. {sum(o.amount_recovered for o in outcomes):,.2f}", flush=True)
    print(f"🛡️  HERO METRIC #2 — ₹ CORRECTLY WITHHELD : Rs. {sum(o.amount_withheld for o in outcomes):,.2f}", flush=True)
    print("--------------------------------------------------------------------------------", flush=True)
    print("Meaning:", flush=True)
    print("₹ ACTUALLY RECOVERED : Confirmed captured by Financial State Engine post-intervention.", flush=True)
    print("₹ CORRECTLY WITHHELD : Intentionally blocked from unnecessary/irrational chase.", flush=True)
    print("================================================================================\n", flush=True)


if __name__ == "__main__":
    run_demo()
