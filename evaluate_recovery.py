"""
RecoverAI - Recovery Intelligence Evaluation Script.

Evaluates the Recovery Probability Model and Economic Decision Engine on VERIFIED_LOST payments.
Trains and persists the model pipeline, then reports model performance and portfolio economic simulation.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Ensure utf-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine import FinancialStateEngine, FinancialState, PaymentRecord, Event
from recovery.features import build_recovery_dataset, FEATURE_COLUMNS
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from recovery.decision import RecoveryDecisionEngine, RecoveryDecision


MODEL_PATH = Path("models") / "recovery_probability_model.joblib"


def run_recovery_evaluation():
    print("=" * 80)
    print(" RecoverAI — RECOVERY INTELLIGENCE EVALUATION ")
    print("=" * 80)

    # 1. Ingest Data
    payments_df = pd.read_csv("payments.csv")
    events = []
    with open("events.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(Event(**json.loads(line)))

    print(f"Loaded {len(payments_df)} payment records and {len(events)} lifecycle events.")

    # 2. Gate through Financial State Engine
    engine = FinancialStateEngine()
    state_results = engine.evaluate_all(payments_df.to_dict("records"), events)
    
    verified_lost_pids = set(r.payment_id for r in state_results if r.state == FinancialState.VERIFIED_LOST)
    print(f"\n[Financial State Gate] Identified {len(verified_lost_pids)} VERIFIED_LOST payments out of {len(payments_df)} total records.")
    print("Non-lost payments (ALREADY_RECOVERED, UNCERTAIN, EXCEPTION) are strictly excluded from recovery modeling.")

    # 3. Construct Recovery Dataset
    payments = [PaymentRecord(**r) for r in payments_df.to_dict("records")]
    recovery_df = build_recovery_dataset(payments, events, verified_lost_pids)
    
    total_lost_count = len(recovery_df)
    X = recovery_df[FEATURE_COLUMNS]
    y = recovery_df["simulated_recovery_target"]

    # 4. Train / Test Split
    test_size = 0.25
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    # 5. Train & Persist Model Pipeline
    model = RecoveryProbabilityModel(random_state=42)
    model.train(X_train, y_train)
    model.save(MODEL_PATH)
    print(f"\nTrained Logistic Regression model pipeline with {len(model.feature_names_)} features.")
    print(f"Saved model to: {MODEL_PATH}")

    # 6. Model Performance Evaluation
    y_test_pred = model.pipeline.predict(X_test)
    y_test_probs = model.pipeline.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_test_pred)
    prec = precision_score(y_test, y_test_pred)
    rec = recall_score(y_test, y_test_pred)
    f1 = f1_score(y_test, y_test_pred)
    auc = roc_auc_score(y_test, y_test_probs)
    cm = confusion_matrix(y_test, y_test_pred)

    print("\n==================================================")
    print(" 1. MODEL DATASET")
    print("==================================================")
    print(f"Total VERIFIED_LOST Cases    : {total_lost_count}")
    print(f"Training Population          : {len(X_train)} ({100 - int(test_size*100)}%)")
    print(f"Test Evaluation Population   : {len(X_test)} ({int(test_size*100)}%)")
    print(f"Simulated Target Positive %  : {y.mean() * 100:.1f}%")

    print("\n==================================================")
    print(" 2. MODEL PERFORMANCE (Test Split - 47 Cases)")
    print("==================================================")
    print(f"Accuracy                     : {acc * 100:.2f}%")
    print(f"Precision                    : {prec * 100:.2f}%")
    print(f"Recall                       : {rec * 100:.2f}%")
    print(f"F1 Score                     : {f1 * 100:.2f}%")
    print(f"ROC-AUC                      : {auc:.4f}")
    print("\nConfusion Matrix (Test Set):")
    print(f"  [TN={cm[0,0]:>2}, FP={cm[0,1]:>2}]")
    print(f"  [FN={cm[1,0]:>2}, TP={cm[1,1]:>2}]")
    print("\n* Note: Evaluated on synthetic simulated recovery outcomes for research & benchmark purposes.")

    # 7. Portfolio Economic Simulation on all VERIFIED_LOST Cases
    cost_config = RecoveryCostConfig(retry_cost=20.0, intervention_cost=10.0, friction_cost=50.0)
    decision_engine = RecoveryDecisionEngine(model=model, cost_config=cost_config, state_engine=engine)

    total_evaluated_amount = 0.0
    total_expected_gross = 0.0
    total_expected_cost = 0.0
    total_expected_net = 0.0
    worthwhile_count = 0
    do_not_recover_count = 0

    evaluated_results = []
    events_by_pay = defaultdict(list)
    for e in events:
        if e.payment_id:
            events_by_pay[e.payment_id].append(e)

    for p in payments:
        if p.payment_id in verified_lost_pids:
            res = decision_engine.evaluate_payment(
                p, events_by_pay.get(p.payment_id, []), precomputed_state=FinancialState.VERIFIED_LOST
            )
            evaluated_results.append((p, res))
            total_evaluated_amount += res.amount
            total_expected_gross += res.expected_gross_recovery or 0.0
            costs = (res.retry_cost or 0) + (res.intervention_cost or 0) + (res.friction_cost or 0)
            total_expected_cost += costs
            total_expected_net += res.expected_net_value or 0.0

            if res.decision == RecoveryDecision.RECOVERY_WORTHWHILE:
                worthwhile_count += 1
            else:
                do_not_recover_count += 1

    print("\n==================================================")
    print(" 3. ECONOMIC SIMULATION (All 188 VERIFIED_LOST Cases)")
    print("==================================================")
    print(f"Total Amount Evaluated       : Rs. {total_evaluated_amount:,.2f}")
    print(f"Synthetic Expected Gross     : Rs. {total_expected_gross:,.2f}")
    print(f"Total Estimated Costs        : Rs. {total_expected_cost:,.2f} (Rs. {cost_config.total_cost:.0f} / payment)")
    print(f"Synthetic Expected Net Value : Rs. {total_expected_net:,.2f}")
    print(f"Expected ROI Multiplier      : {(total_expected_gross / total_expected_cost if total_expected_cost > 0 else 0):.2f}x")
    print(f"Decisions: RECOVERY_WORTHWHILE: {worthwhile_count} ({worthwhile_count / total_lost_count * 100:.1f}%)")
    print(f"Decisions: DO_NOT_RECOVER     : {do_not_recover_count} ({do_not_recover_count / total_lost_count * 100:.1f}%)")

    # 8. Sample Predictions Breakdown
    print("\n==================================================")
    print(" 4. 5 REPRESENTATIVE RECOVERY PREDICTIONS")
    print("==================================================")
    for idx, (p, r) in enumerate(evaluated_results[:5], 1):
        print(f"Case #{idx:02d}: Payment [{r.payment_id}] | Method: {p.method} | Segment: {p.customer_segment}")
        print(f"  Amount                 : Rs. {r.amount:,.2f}")
        print(f"  Recovery Probability   : {int(round((r.recovery_probability or 0.0) * 100))}%")
        print(f"  Expected Gross Recovery: Rs. {r.expected_gross_recovery:,.2f}")
        print(f"  Expected Net Value     : Rs. {r.expected_net_value:,.2f}")
        print(f"  Decision               : {r.decision.value}")
        if r.explanation:
            pos = ", ".join(r.explanation.get("top_positive_factors", [])) or "None"
            neg = ", ".join(r.explanation.get("top_negative_factors", [])) or "None"
            print(f"  Top Positive Factors   : {pos}")
            print(f"  Top Negative Factors   : {neg}")
        print("-" * 80)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    run_recovery_evaluation()
