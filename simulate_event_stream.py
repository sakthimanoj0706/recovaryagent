"""
RecoverAI — Real-Time Event Stream Simulator.
Demonstrates dynamic state transition and eventual consistency across asynchronous payment events:
T+0: payment.created -> T+2: payment.failed (VERIFIED_LOST) -> T+45: payment.authorized (ALREADY_RECOVERED) -> T+46: payment.captured
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion import EventProcessor
from state_engine.models import PaymentRecord



def run_event_stream_simulation():
    print("=" * 80)
    print("       RecoverAI — REAL-TIME ASYNCHRONOUS EVENT STREAM SIMULATOR        ")
    print("             'Dynamic Re-Evaluation & Eventual Consistency'             ")
    print("=" * 80)

    processor = EventProcessor()
    processor.clear_store()

    pid = "pay_stream_sim_001"
    oid = "ord_stream_sim_001"
    amount = 12500.0
    base_time = datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc)

    # -------------------------------------------------------------------------
    # Event 1 (T+0): payment.created
    # -------------------------------------------------------------------------
    t0_iso = (base_time + timedelta(seconds=0)).isoformat()
    evt1 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_001_created",
        "event": "payment.created",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "ts": t0_iso,
    }
    print(f"\n[T+0s] Ingesting: payment.created")
    res1 = processor.process_webhook(evt1)
    print(f"  -> Ingestion Status : {res1.status.value}")
    print(f"  -> Financial State  : {res1.financial_state_after}")
    assert res1.financial_state_after in ["UNCERTAIN", "NOT_FOUND", "VERIFIED_LOST"], f"Unexpected state: {res1.financial_state_after}"

    # -------------------------------------------------------------------------
    # Event 2 (T+2s): payment.failed (INSUFFICIENT_FUNDS) -> VERIFIED_LOST
    # -------------------------------------------------------------------------
    t2_iso = (base_time + timedelta(seconds=2)).isoformat()
    evt2 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_002_failed",
        "event": "payment.failed",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "error_code": "INSUFFICIENT_FUNDS",
        "hardness": "soft",
        "ts": t2_iso,
    }
    print(f"\n[T+2s] Ingesting: payment.failed (INSUFFICIENT_FUNDS)")
    res2 = processor.process_webhook(evt2)
    print(f"  -> Ingestion Status : {res2.status.value}")
    print(f"  -> Financial State  : {res2.financial_state_after}")
    print(f"  -> State Changed    : {res2.state_changed}")
    assert res2.financial_state_after == "VERIFIED_LOST", f"Expected VERIFIED_LOST, got {res2.financial_state_after}"
    if res2.orchestrator_result:
        print(f"  -> Recovery Action  : {res2.orchestrator_result.get('agent_action')} (Firewall: {res2.orchestrator_result.get('firewall_decision')})")

    # -------------------------------------------------------------------------
    # Event 3 (T+45s): payment.authorized (Asynchronous Late-Auth) -> ALREADY_RECOVERED
    # -------------------------------------------------------------------------
    t45_iso = (base_time + timedelta(seconds=45)).isoformat()
    evt3 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_003_authorized",
        "event": "payment.authorized",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "late_authorization": True,
        "ts": t45_iso,
    }
    print(f"\n[T+45s] Ingesting: payment.authorized (Late Authorization Flip-Flop)")
    res3 = processor.process_webhook(evt3)
    print(f"  -> Ingestion Status : {res3.status.value}")
    print(f"  -> State Before     : {res3.financial_state_before}")
    print(f"  -> Financial State  : {res3.financial_state_after}")
    print(f"  -> State Changed    : {res3.state_changed}")
    assert res3.financial_state_after == "ALREADY_RECOVERED", f"Expected ALREADY_RECOVERED, got {res3.financial_state_after}"
    assert res3.state_changed is True, "State should have transitioned from VERIFIED_LOST to ALREADY_RECOVERED"

    # -------------------------------------------------------------------------
    # Event 4 (T+46s): payment.captured -> ALREADY_RECOVERED
    # -------------------------------------------------------------------------
    t46_iso = (base_time + timedelta(seconds=46)).isoformat()
    evt4 = {
        "provider": "mock",
        "event_id": f"evt_{pid}_004_captured",
        "event": "payment.captured",
        "payment_id": pid,
        "order_id": oid,
        "amount": amount,
        "method": "upi",
        "ts": t46_iso,
    }
    print(f"\n[T+46s] Ingesting: payment.captured")
    res4 = processor.process_webhook(evt4)
    print(f"  -> Ingestion Status : {res4.status.value}")
    print(f"  -> Financial State  : {res4.financial_state_after}")
    assert res4.financial_state_after == "ALREADY_RECOVERED", f"Expected ALREADY_RECOVERED, got {res4.financial_state_after}"

    # -------------------------------------------------------------------------
    # Event 5: Duplicate Webhook Event Ingestion (Idempotency Proof)
    # -------------------------------------------------------------------------
    print(f"\n[Idempotency Test] Re-submitting duplicate captured webhook (ID: {evt4['event_id']})")
    res5 = processor.process_webhook(evt4)
    print(f"  -> Ingestion Status : {res5.status.value}")
    print(f"  -> Message          : {res5.message}")
    assert res5.status.value == "DUPLICATE_EVENT", f"Expected DUPLICATE_EVENT, got {res5.status.value}"

    print("\n" + "=" * 80)
    print("[PASS] ALL EVENT STREAM SIMULATION ASSERTIONS PASSED (100% SUCCESS)")
    print("=" * 80 + "\n")



if __name__ == "__main__":
    run_event_stream_simulation()
