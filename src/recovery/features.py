"""
Feature engineering and dataset construction for the RecoverAI Recovery Intelligence Layer.

Observes only legitimate operational payment features at decision time.
Explicitly excludes synthetic scenario/ground_truth labels to prevent data leakage.
"""

from typing import List, Dict, Any, Optional, Set
import numpy as np
import pandas as pd

try:
    from ..state_engine.models import PaymentRecord, Event
except (ImportError, ValueError):
    try:
        from state_engine.models import PaymentRecord, Event
    except ImportError:
        from src.state_engine.models import PaymentRecord, Event


LEAKAGE_COLUMNS = {"scenario", "ground_truth_state"}
FEATURE_COLUMNS = ["amount", "method", "customer_segment", "error_code", "hardness"]


def extract_payment_features(payment: PaymentRecord, events: List[Event]) -> Dict[str, Any]:
    """
    Extract observable features for a single payment.
    Gracefully handles missing or unobserved fields.
    """
    # Filter failure events
    fail_events = [e for e in events if e.event == "payment.failed"]
    last_fail = fail_events[-1] if fail_events else None

    # Amount (defaulting to 0.0 if missing)
    amt = float(payment.amount) if payment.amount is not None else 0.0

    # Payment method
    method = payment.method or (last_fail.method if last_fail else None) or "unknown"

    # Customer segment
    cust_segment = payment.customer_segment or "unknown"

    # Error code & hardness from failure event
    err_code = (last_fail.error_code if last_fail and last_fail.error_code else "UNKNOWN").strip().upper()
    hardness = (last_fail.hardness if last_fail and last_fail.hardness else "soft").strip().lower()

    return {
        "payment_id": payment.payment_id,
        "order_id": payment.order_id,
        "amount": amt,
        "method": method.lower(),
        "customer_segment": cust_segment.lower(),
        "error_code": err_code,
        "hardness": hardness,
    }


def simulate_recovery_outcome(features: Dict[str, Any], seed: Optional[int] = None) -> int:
    """
    Simulated synthetic recovery outcome generator.
    
    IMPORTANT ARCHITECTURAL NOTE:
    The existing dataset records initial failure lifecycle and financial state,
    but does not contain downstream recovery campaign observations.
    This synthetic target is generated deterministically based on real-world domain assumptions:
    - Soft errors (downtime, timeouts, 3DS auth retry) have higher recovery probability (~75-85%).
    - Hard errors (bad VPAs, blocked cards, permanent declines) have lower recovery probability (~15-30%).
    - Repeat & high-value customer segments exhibit higher response/conversion rates.
    """
    pid = features.get("payment_id", "default_pid")
    calc_seed = seed if seed is not None else (abs(hash(str(pid))) % (2**32 - 1))
    rng = np.random.RandomState(calc_seed)

    base_prob = 0.50
    hardness = features.get("hardness", "soft")
    cust_segment = features.get("customer_segment", "unknown")
    err_code = features.get("error_code", "UNKNOWN")

    # Hardness impact
    if hardness == "soft":
        base_prob += 0.25
    else:
        base_prob -= 0.30

    # Customer segment impact
    if cust_segment == "high_value_repeat":
        base_prob += 0.15
    elif cust_segment == "returning":
        base_prob += 0.05
    elif cust_segment == "new":
        base_prob -= 0.10

    # Specific error code adjustments
    if err_code in {"BANK_DOWNTIME", "TIMEOUT"}:
        base_prob += 0.10
    elif err_code in {"INSUFFICIENT_FUNDS", "TXN_LIMIT"}:
        base_prob += 0.05
    elif err_code in {"CARD_BLOCKED", "CARD_EXPIRED", "BAD_VPA"}:
        base_prob -= 0.15
    elif err_code == "USER_CANCELLED":
        base_prob -= 0.10

    clamped_prob = float(np.clip(base_prob, 0.05, 0.95))
    return 1 if rng.rand() < clamped_prob else 0


def build_recovery_dataset(
    payments: List[PaymentRecord],
    events: List[Event],
    verified_lost_pids: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Build the recovery ML dataset from VERIFIED_LOST payments only.
    """
    events_by_pay: Dict[str, List[Event]] = {}
    for ev in events:
        if ev.payment_id:
            events_by_pay.setdefault(ev.payment_id, []).append(ev)

    records = []
    for pay in payments:
        if verified_lost_pids is not None and pay.payment_id not in verified_lost_pids:
            continue

        pay_evs = events_by_pay.get(pay.payment_id, [])
        feats = extract_payment_features(pay, pay_evs)

        # Generate simulated recovery target for modeling
        sim_target = simulate_recovery_outcome(feats)
        feats["simulated_recovery_target"] = sim_target
        records.append(feats)

    df = pd.DataFrame(records)
    return df
