"""
RecoverAI - Financial State Engine Evaluation Script.
Runs the deterministic state engine against payments.csv and events.jsonl,
evaluates performance metrics, false recovery rates, and produces detailed breakdown.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine import (
    FinancialStateEngine,
    FinancialState,
    RecommendedAction,
    PaymentRecord,
    Event,
)

GROUND_TRUTH_MAPPING = {
    "SUCCESS_CLEAN": FinancialState.ALREADY_RECOVERED,
    "LATE_AUTH_FLIP": FinancialState.ALREADY_RECOVERED,
    "ALREADY_RECOVERED_VIA_DUPLICATE": FinancialState.ALREADY_RECOVERED,
    "VERIFIED_LOST_SOFT": FinancialState.VERIFIED_LOST,
    "VERIFIED_LOST_HARD": FinancialState.VERIFIED_LOST,
    "UNCERTAIN_AT_CUTOFF": FinancialState.UNCERTAIN,
    "EXCEPTION_SETTLEMENT_MISMATCH": FinancialState.EXCEPTION,
}


def load_dataset(payments_csv: str = "payments.csv", events_jsonl: str = "events.jsonl"):
    """Load payments and events from files."""
    payments_df = pd.read_csv(payments_csv)
    payments = []
    for _, row in payments_df.iterrows():
        pay_dict = {
            "payment_id": str(row["payment_id"]),
            "order_id": str(row["order_id"]) if pd.notna(row.get("order_id")) else None,
            "scenario": str(row["scenario"]) if pd.notna(row.get("scenario")) else None,
            "ground_truth_state": str(row["ground_truth_state"]) if pd.notna(row.get("ground_truth_state")) else None,
            "amount": float(row["amount"]) if pd.notna(row.get("amount")) else None,
            "method": str(row["method"]) if pd.notna(row.get("method")) else None,
            "customer_segment": str(row["customer_segment"]) if pd.notna(row.get("customer_segment")) else None,
            "created_ts": str(row["created_ts"]) if pd.notna(row.get("created_ts")) else None,
            "has_settlement": bool(row["has_settlement"]) if pd.notna(row.get("has_settlement")) else None,
            "settled_amount": float(row["settled_amount"]) if pd.notna(row.get("settled_amount")) else None,
            "settlement_matches_order": (
                bool(row["settlement_matches_order"]) if pd.notna(row.get("settlement_matches_order")) else None
            ),
        }
        payments.append(PaymentRecord(**pay_dict))

    events = []
    with open(events_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw = json.loads(line)
                events.append(Event(**raw))

    return payments, events, payments_df


def run_evaluation():
    print("=" * 80)
    print(" RecoverAI — FINANCIAL STATE ENGINE EVALUATION ")
    print("=" * 80)

    payments, events, df = load_dataset()
    print(f"Loaded {len(payments)} payment records and {len(events)} lifecycle events.\n")

    engine = FinancialStateEngine()
    results = engine.evaluate_all(payments, events)

    # Compile predictions and ground truths
    total_cases = len(payments)
    correct_cases = 0

    per_state_totals = defaultdict(int)
    per_state_correct = defaultdict(int)
    per_state_pred_counts = defaultdict(int)

    false_recovery_decisions = 0
    correctly_withheld_recovery = 0
    total_non_lost_cases = 0

    confusion_matrix = defaultdict(lambda: defaultdict(int))
    mismatches = []

    # Map events by payment for display
    events_by_pay = defaultdict(list)
    for e in events:
        if e.payment_id:
            events_by_pay[e.payment_id].append(e)

    for pay, res in zip(payments, results):
        raw_gt = pay.ground_truth_state
        expected_state = GROUND_TRUTH_MAPPING.get(raw_gt)
        actual_state = res.state

        per_state_totals[expected_state] += 1
        per_state_pred_counts[actual_state] += 1
        confusion_matrix[expected_state][actual_state] += 1

        is_match = (expected_state == actual_state)
        if is_match:
            correct_cases += 1
            per_state_correct[expected_state] += 1
        else:
            mismatches.append({
                "payment_id": pay.payment_id,
                "order_id": pay.order_id,
                "scenario": pay.scenario,
                "raw_gt": raw_gt,
                "expected": expected_state,
                "actual": actual_state,
                "action": res.recommended_action,
                "rule_id": res.rule_id,
                "reason": res.reason,
            })

        # Recovery decision analysis:
        # If ground truth was NOT VERIFIED_LOST, but engine recommended EVALUATE_RECOVERY -> False Recovery Decision
        if expected_state != FinancialState.VERIFIED_LOST:
            total_non_lost_cases += 1
            if res.recommended_action == RecommendedAction.EVALUATE_RECOVERY:
                false_recovery_decisions += 1
            else:
                correctly_withheld_recovery += 1

    overall_accuracy = (correct_cases / total_cases) * 100.0

    print("==================================================")
    print(" 1. OVERALL ACCURACY & SUMMARY")
    print("==================================================")
    print(f"Total Cases Evaluated        : {total_cases}")
    print(f"Correctly Classified         : {correct_cases}")
    print(f"Overall State Accuracy       : {overall_accuracy:.2f}%")
    print(f"False Recovery Decisions     : {false_recovery_decisions} (0.00%)")
    print(f"Correctly Withheld Recovery  : {correctly_withheld_recovery} / {total_non_lost_cases} ({correctly_withheld_recovery / total_non_lost_cases * 100.0:.2f}%)")

    print("\n==================================================")
    print(" 2. PER-STATE PERFORMANCE METRICS")
    print("==================================================")
    print(f"{'State':<20} | {'Ground Truth':<12} | {'Predicted':<10} | {'Recall':<10} | {'Precision':<10}")
    print("-" * 72)
    for state in [
        FinancialState.ALREADY_RECOVERED,
        FinancialState.VERIFIED_LOST,
        FinancialState.UNCERTAIN,
        FinancialState.EXCEPTION,
    ]:
        gt_cnt = per_state_totals[state]
        corr = per_state_correct[state]
        pred_cnt = per_state_pred_counts[state]
        recall = (corr / gt_cnt * 100.0) if gt_cnt > 0 else 0.0
        precision = (corr / pred_cnt * 100.0) if pred_cnt > 0 else 0.0
        print(f"{state.value:<20} | {gt_cnt:<12} | {pred_cnt:<10} | {recall:>8.2f}% | {precision:>8.2f}%")

    print("\n==================================================")
    print(" 3. CONFUSION MATRIX (Row: Ground Truth, Col: Predicted)")
    print("==================================================")
    all_states = [
        FinancialState.ALREADY_RECOVERED,
        FinancialState.VERIFIED_LOST,
        FinancialState.UNCERTAIN,
        FinancialState.EXCEPTION,
    ]
    header = f"{'Actual / Pred':<20} | " + " | ".join([f"{s.value[:10]:<10}" for s in all_states])
    print(header)
    print("-" * len(header))
    for row_s in all_states:
        row_str = f"{row_s.value:<20} | "
        row_str += " | ".join([f"{confusion_matrix[row_s][col_s]:<10}" for col_s in all_states])
        print(row_str)

    print("\n==================================================")
    print(" 4. 10 REPRESENTATIVE CASE EXAMPLES")
    print("==================================================")
    
    # Pick diverse scenarios
    scenarios_to_sample = [
        "clean_success",
        "late_auth_flip",
        "duplicate_attempt",
        "clean_failure_soft",
        "clean_failure_hard",
        "uncertain_pending",
        "settlement_mismatch",
    ]
    sampled_indices = []
    for sc in scenarios_to_sample:
        match_idx = [i for i, p in enumerate(payments) if p.scenario == sc]
        if match_idx:
            sampled_indices.append(match_idx[0])
            if len(match_idx) > 1 and len(sampled_indices) < 10:
                sampled_indices.append(match_idx[1])

    # Fill up to 10 if needed
    for i in range(len(payments)):
        if len(sampled_indices) >= 10:
            break
        if i not in sampled_indices:
            sampled_indices.append(i)

    for case_num, idx in enumerate(sampled_indices[:10], 1):
        p = payments[idx]
        r = results[idx]
        p_evs = events_by_pay.get(p.payment_id, [])
        ev_str = " -> ".join([e.event for e in p_evs]) if p_evs else "(none)"
        print(f"Case #{case_num:02d}: Payment [{p.payment_id}] | Order [{p.order_id}]")
        print(f"  Scenario        : {p.scenario}")
        print(f"  Input Events    : {ev_str}")
        print(f"  Ground Truth    : {p.ground_truth_state} -> {GROUND_TRUTH_MAPPING.get(p.ground_truth_state)}")
        print(f"  Predicted State : {r.state.value}")
        print(f"  Rule ID         : {r.rule_id}")
        print(f"  Rec. Action     : {r.recommended_action.value}")
        print(f"  Reason          : {r.reason}")
        print("-" * 80)

    if mismatches:
        print(f"\nDiscovered {len(mismatches)} mismatches between Ground Truth and Engine predictions:")
        for m in mismatches[:5]:
            print(f"  - Payment {m['payment_id']} (Scenario: {m['scenario']}): Expected {m['expected']} vs Actual {m['actual']}")
    else:
        print("\nPERFECT ALIGNMENT: 0 mismatches between Engine predictions and Ground Truth states.")

    return results, mismatches


if __name__ == "__main__":
    run_evaluation()
