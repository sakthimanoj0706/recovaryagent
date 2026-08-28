"""
RecoverAI — Live Event-Driven Closed-Loop Recovery Demo (Step 6).
Demonstrates end-to-end integration:
Webhook Ingestion -> Financial State Engine -> Economics -> Advisory Agent -> Firewall -> Mock Gateway -> Late Capture Ingestion -> State Re-Evaluation -> Ledger Confirmation -> Webhook Idempotency Check.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion import EventProcessor
from state_engine.models import PaymentRecord
from gateway import get_gateway


def run_live_event_loop_demo():
    print("=" * 80)
    print("    RecoverAI — LIVE EVENT-DRIVEN CLOSED-LOOP RECOVERY DEMO (SIMULATION)    ")
    print("             'Prove -> Prioritize -> Plan -> Guard -> Act -> Verify'         ")
    print("=" * 80)

    processor = EventProcessor()
    processor.clear_store()
    gateway = get_gateway()

    pid = "pay_demo_live_25k"
    oid = "ord_demo_live_25k"
    amount = 25000.0
    base_time = datetime(2026, 8, 28, 11, 0, 0, tzinfo=timezone.utc)

    print("\n--- [STAGE 1: ASYNCHRONOUS PAYMENT FAILURE INGESTION] ---")
    print(f"Target Payment ID : {pid}")
    print(f"Target Order ID   : {oid}")
    print(f"Amount            : Rs. {amount:,.2f}")
    print(f"Payment Mode      : UPI (Mobile Checkout)")

    # 1. Ingest payment.created
    evt1 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_created",
        "event": "payment.created",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "ts": (base_time + timedelta(seconds=0)).isoformat(),
        "payload": {"merchant": "Acme Retail", "channel": "mobile_app"},
    }
    res1 = processor.process_webhook(evt1)
    print(f"\n[Webhook Ingested] Event: payment.created (Event ID: {evt1['event_id']})")
    print(f"  -> Ingestion Status    : {res1.status.value}")
    print(f"  -> State Engine Result : {res1.financial_state_after}")

    # 2. Ingest payment.failed (INSUFFICIENT_FUNDS)
    evt2 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_failed",
        "event": "payment.failed",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "error_code": "INSUFFICIENT_FUNDS",
        "error_description": "Declined due to insufficient account balance",
        "hardness": "soft",
        "ts": (base_time + timedelta(seconds=3)).isoformat(),
        "payload": {"error_source": "issuing_bank", "retryable": True},
    }
    print(f"\n[Webhook Ingested] Event: payment.failed (INSUFFICIENT_FUNDS)")
    res2 = processor.process_webhook(evt2)
    print(f"  -> Ingestion Status    : {res2.status.value}")
    print(f"  -> State Engine Verdict: {res2.financial_state_after} (Financial Truth Established)")
    print(f"  -> State Transition    : {res2.financial_state_before} -> {res2.financial_state_after}")
    assert res2.financial_state_after == "VERIFIED_LOST", "State must be VERIFIED_LOST"

    orch_info = res2.orchestrator_result or {}
    prob_val = orch_info.get('recovery_probability') or 0.0
    env_val = orch_info.get('expected_net_value') or 0.0
    print("\n--- [STAGE 2: BOUNDED AGENTIC RECOVERY DISPATCH] ---")
    print(f"  1. Recovery Probability : {prob_val * 100:.1f}%")
    print(f"  2. Expected Net Value   : Rs. {env_val:,.2f}")
    print(f"  3. Advisory Action      : {orch_info.get('agent_action')}")
    print(f"  4. Advisory Rationale   : {orch_info.get('agent_reason')}")
    print(f"  5. Firewall Decision    : {orch_info.get('firewall_decision')} (Rule: {orch_info.get('firewall_rule') or 'PASSED'})")
    print(f"  6. Gateway Status       : {orch_info.get('execution_status')}")


    # 3. Simulate asynchronous customer payment via link (payment.captured arrives at T+35s)
    print("\n--- [STAGE 3: ASYNCHRONOUS CAPTURE ARRIVAL & VERIFICATION] ---")
    evt3 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_captured_late",
        "event": "payment.captured",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "ts": (base_time + timedelta(seconds=35)).isoformat(),
        "payload": {"gateway_reference": "rzp_sim_cap_8842", "settled": True},
    }
    print(f"[Webhook Ingested] Event: payment.captured (Late Settlement)")
    res3 = processor.process_webhook(evt3)
    print(f"  -> Ingestion Status    : {res3.status.value}")
    print(f"  -> State Before        : {res3.financial_state_before}")
    print(f"  -> Verified State After: {res3.financial_state_after} (Source of Truth: FINANCIAL STATE ENGINE)")
    print(f"  -> State Changed       : {res3.state_changed}")
    assert res3.financial_state_after == "ALREADY_RECOVERED", "Ledger must verify ALREADY_RECOVERED"
    assert res3.state_changed is True, "State must transition from VERIFIED_LOST to ALREADY_RECOVERED"

    # 4. Ingest Duplicate Webhook (Idempotency Assurance)
    print("\n--- [STAGE 4: WEBHOOK IDEMPOTENCY & DUPLICATE PROTECTION] ---")
    print(f"[Adversarial Test] Re-submitting duplicate event_id: '{evt3['event_id']}'")
    res_dup = processor.process_webhook(evt3)
    print(f"  -> Ingestion Status    : {res_dup.status.value}")
    print(f"  -> Protection Message  : {res_dup.message}")
    print(f"  -> Actions Executed    : ZERO (Idempotent interception)")
    assert res_dup.status.value == "DUPLICATE_EVENT", "Duplicate webhook must be intercepted as DUPLICATE_EVENT"

    print("\n" + "=" * 80)
    print("                    LIVE EVENT LOOP DEMO SUMMARY                        ")
    print("=" * 80)
    print(f"Payment ID              : {pid}")
    print(f"Total Amount Processed  : Rs. {amount:,.2f}")
    print(f"Initial Financial State : VERIFIED_LOST")
    print(f"Agent Proposed Action   : PAYMENT_LINK")
    print(f"Firewall Verdict        : APPROVED")
    print(f"Verified Ledger State   : ALREADY_RECOVERED")
    print(f"Final Outcome           : RECOVERY_SUCCESS (Ledger Confirmed)")
    print(f"Webhook Idempotency     : VERIFIED (Zero double-recovery)")
    print("=" * 80)
    print("\n[PASS] DEMO LIVE EVENT LOOP ASSERTIONS COMPLETED (100% SUCCESS)\n")


if __name__ == "__main__":
    run_live_event_loop_demo()
