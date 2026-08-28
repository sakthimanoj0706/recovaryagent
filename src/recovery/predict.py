"""
CLI Predictor for single-payment Recovery Intelligence.

Usage:
  python -m src.recovery.predict --payment-id pay_9edbf54e7c7646
"""

import argparse
import sys
import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

# Ensure safe encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state_engine import FinancialStateEngine, PaymentRecord, Event
from src.recovery.model import RecoveryProbabilityModel
from src.recovery.economics import RecoveryCostConfig
from src.recovery.decision import RecoveryDecisionEngine, RecoveryDecision
from src.recovery.features import build_recovery_dataset


MODEL_FILE = Path(__file__).parent.parent.parent / "models" / "recovery_probability_model.joblib"


def get_or_train_model() -> RecoveryProbabilityModel:
    """Load model if exists; otherwise train and save."""
    if MODEL_FILE.exists():
        return RecoveryProbabilityModel.load(MODEL_FILE)

    # Train model on dataset
    payments_df = pd.read_csv("payments.csv")
    events = []
    with open("events.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(Event(**json.loads(line)))

    engine = FinancialStateEngine()
    results = engine.evaluate_all(payments_df.to_dict("records"), events)
    verified_lost_pids = set(r.payment_id for r in results if r.state.value == "VERIFIED_LOST")

    payments = [PaymentRecord(**r) for r in payments_df.to_dict("records")]
    train_df = build_recovery_dataset(payments, events, verified_lost_pids)

    model = RecoveryProbabilityModel(random_state=42)
    model.train(train_df, train_df["simulated_recovery_target"])
    model.save(MODEL_FILE)
    return model


def predict_cli(payment_id: str):
    payments_df = pd.read_csv("payments.csv")
    match_rows = payments_df[payments_df["payment_id"] == payment_id]
    if match_rows.empty:
        print(f"Error: Payment ID '{payment_id}' not found in payments.csv.")
        sys.exit(1)

    pay_dict = match_rows.iloc[0].to_dict()
    payment = PaymentRecord(**pay_dict)

    events = []
    order_events = []
    with open("events.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ev_data = json.loads(line)
                if ev_data.get("payment_id") == payment_id:
                    events.append(Event(**ev_data))
                if payment.order_id and ev_data.get("order_id") == payment.order_id:
                    order_events.append(Event(**ev_data))

    model = get_or_train_model()
    decision_engine = RecoveryDecisionEngine(model=model, cost_config=RecoveryCostConfig())
    res = decision_engine.evaluate_payment(payment, events, order_events)

    print("\n" + "-" * 40)
    print("RecoverAI Recovery Intelligence")
    print("-" * 40)
    print(f"\nPayment: {res.payment_id}")
    print(f"Financial State: {res.financial_state}")

    fail_evs = [e for e in events if e.event == "payment.failed"]
    last_fail = fail_evs[-1] if fail_evs else None
    err_code = last_fail.error_code if last_fail and last_fail.error_code else "UNKNOWN"

    print(f"\nAmount: Rs. {res.amount:,.0f}")
    print(f"Failure: {err_code}")
    print(f"Customer: {payment.customer_segment or 'unknown'}")

    if res.financial_state != "VERIFIED_LOST":
        print(f"\nDecision:\n[INELIGIBLE] {res.decision.value} ({res.reason})")
        print("\n" + "-" * 40 + "\n")
        return

    prob_pct = int(round((res.recovery_probability or 0.0) * 100))
    print(f"\nRecovery Probability: {prob_pct}%")
    print(f"\nExpected Gross Recovery: Rs. {res.expected_gross_recovery:,.0f}")
    total_costs = (res.retry_cost or 0) + (res.intervention_cost or 0) + (res.friction_cost or 0)
    print(f"Estimated Costs: Rs. {total_costs:,.0f}")
    print(f"\nExpected Net Value: Rs. {res.expected_net_value:,.0f}")

    if res.decision == RecoveryDecision.RECOVERY_WORTHWHILE:
        decision_label = "[RECOVERY WORTHWHILE]"
    else:
        decision_label = "[DO NOT RECOVER]"

    print(f"\nDecision:\n{decision_label}")

    if res.explanation:
        print("\nExplanation:")
        for pos in res.explanation.get("top_positive_factors", []):
            print(f"+ {pos}")
        for neg in res.explanation.get("top_negative_factors", []):
            print(f"- {neg}")

    print("\n" + "-" * 40 + "\n")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Recovery Predictor CLI")
    parser.add_argument("--payment-id", required=True, help="Payment ID to evaluate")
    args = parser.parse_args()
    predict_cli(args.payment_id)


if __name__ == "__main__":
    main()
