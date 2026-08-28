"""
Automated test suite for RecoverAI Recovery Intelligence Layer.
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import FinancialState, PaymentRecord, Event
from recovery.features import extract_payment_features, simulate_recovery_outcome, build_recovery_dataset
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig, calculate_expected_net_value
from recovery.decision import RecoveryDecisionEngine, RecoveryDecision


@pytest.fixture
def trained_model():
    # Train a standard fixture model
    X_train = pd.DataFrame([
        {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
        {"amount": 5000.0, "method": "card", "customer_segment": "returning", "error_code": "TIMEOUT", "hardness": "soft"},
        {"amount": 25000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "INSUFFICIENT_FUNDS", "hardness": "soft"},
        {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"},
        {"amount": 500.0, "method": "upi", "customer_segment": "new", "error_code": "BAD_VPA", "hardness": "hard"},
        {"amount": 2000.0, "method": "netbanking", "customer_segment": "new", "error_code": "USER_CANCELLED", "hardness": "hard"},
    ])
    y_train = pd.Series([1, 1, 1, 0, 0, 0])
    model = RecoveryProbabilityModel(random_state=42)
    model.train(X_train, y_train)
    return model


@pytest.fixture
def decision_engine(trained_model):
    cost_cfg = RecoveryCostConfig(retry_cost=20.0, intervention_cost=10.0, friction_cost=50.0)
    return RecoveryDecisionEngine(model=trained_model, cost_config=cost_cfg)


# 1. VERIFIED_LOST enters recovery model
def test_verified_lost_enters_recovery_model(decision_engine):
    payment = PaymentRecord(payment_id="pay_lost_001", order_id="order_001", amount=5000.0, method="upi", customer_segment="returning")
    events = [
        Event(event="payment.created", payment_id="pay_lost_001", order_id="order_001", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_lost_001", order_id="order_001", error_code="TIMEOUT", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.financial_state == "VERIFIED_LOST"
    assert result.recovery_probability is not None
    assert 0.0 <= result.recovery_probability <= 1.0
    assert result.decision in [RecoveryDecision.RECOVERY_WORTHWHILE, RecoveryDecision.DO_NOT_RECOVER]


# 2. ALREADY_RECOVERED is rejected
def test_already_recovered_rejected(decision_engine):
    payment = PaymentRecord(payment_id="pay_rec_002", order_id="order_002", amount=1500.0)
    events = [
        Event(event="payment.created", payment_id="pay_rec_002", order_id="order_002", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_rec_002", order_id="order_002", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_rec_002", order_id="order_002", ts="2026-08-10T10:00:10Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.financial_state == "ALREADY_RECOVERED"
    assert result.decision == RecoveryDecision.INELIGIBLE_STATE
    assert result.recovery_probability is None
    assert result.expected_net_value is None
    assert "rejected" in result.reason.lower()


# 3. UNCERTAIN is rejected
def test_uncertain_rejected(decision_engine):
    payment = PaymentRecord(payment_id="pay_unc_003", order_id="order_003", amount=2000.0)
    events = [
        Event(event="payment.created", payment_id="pay_unc_003", order_id="order_003", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_unc_003", order_id="order_003", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_unc_003", order_id="order_003", ts="2026-08-10T10:01:00Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.financial_state == "UNCERTAIN"
    assert result.decision == RecoveryDecision.INELIGIBLE_STATE
    assert result.recovery_probability is None


# 4. EXCEPTION is rejected
def test_exception_rejected(decision_engine):
    payment = PaymentRecord(
        payment_id="pay_exc_004",
        order_id="order_004",
        amount=1999.0,
        has_settlement=True,
        settled_amount=1900.0,
        settlement_matches_order=False,
    )
    events = [
        Event(event="payment.created", payment_id="pay_exc_004", order_id="order_004", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_exc_004", order_id="order_004", ts="2026-08-10T10:00:10Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.financial_state == "EXCEPTION"
    assert result.decision == RecoveryDecision.INELIGIBLE_STATE
    assert result.recovery_probability is None


# 5. Probability is between 0 and 1
def test_probability_bounded(trained_model):
    features = {
        "amount": 75000.0,
        "method": "upi",
        "customer_segment": "high_value_repeat",
        "error_code": "BANK_DOWNTIME",
        "hardness": "soft",
    }
    prob = trained_model.predict_probability(features)
    assert 0.0 <= prob <= 1.0


# 6. Expected gross recovery calculation
def test_expected_gross_recovery_calc():
    amount = 10000.0
    prob = 0.80
    econ = calculate_expected_net_value(amount=amount, probability=prob)
    assert econ.expected_gross_recovery == 8000.0


# 7. Expected net value calculation
def test_expected_net_value_calc():
    amount = 10000.0
    prob = 0.80
    config = RecoveryCostConfig(retry_cost=20.0, intervention_cost=10.0, friction_cost=50.0)
    econ = calculate_expected_net_value(amount=amount, probability=prob, config=config)
    assert econ.expected_gross_recovery == 8000.0
    assert econ.total_cost == 80.0
    assert econ.expected_net_value == 7920.0


# 8. Positive expected value -> RECOVERY_WORTHWHILE
def test_positive_expected_value_worthwhile(decision_engine):
    payment = PaymentRecord(payment_id="pay_pos_008", order_id="order_008", amount=5000.0, method="upi", customer_segment="high_value_repeat")
    events = [
        Event(event="payment.created", payment_id="pay_pos_008", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_pos_008", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T10:00:05Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.expected_net_value > 0
    assert result.decision == RecoveryDecision.RECOVERY_WORTHWHILE


# 9. Zero expected value -> DO_NOT_RECOVER
def test_zero_expected_value_do_not_recover():
    amount = 100.0
    prob = 0.80  # Gross = 80
    config = RecoveryCostConfig(retry_cost=30.0, intervention_cost=20.0, friction_cost=30.0)  # Cost = 80 -> Net = 0
    econ = calculate_expected_net_value(amount=amount, probability=prob, config=config)
    assert econ.expected_net_value == 0.0
    decision = RecoveryDecision.RECOVERY_WORTHWHILE if econ.expected_net_value > 0 else RecoveryDecision.DO_NOT_RECOVER
    assert decision == RecoveryDecision.DO_NOT_RECOVER


# 10. Negative expected value -> DO_NOT_RECOVER
def test_negative_expected_value_do_not_recover(decision_engine):
    # Small amount (₹50) with low probability (< 0.20) and ₹80 cost -> negative net value
    payment = PaymentRecord(payment_id="pay_neg_010", order_id="order_010", amount=50.0, method="card", customer_segment="new")
    events = [
        Event(event="payment.created", payment_id="pay_neg_010", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_neg_010", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T10:00:05Z"),
    ]
    result = decision_engine.evaluate_payment(payment, events)
    assert result.expected_net_value <= 0
    assert result.decision == RecoveryDecision.DO_NOT_RECOVER


# 11. Missing feature handling
def test_missing_feature_handling(trained_model):
    features = {
        "amount": None,
        "method": None,
        "customer_segment": None,
        "error_code": None,
        "hardness": None,
    }
    prob = trained_model.predict_probability(features)
    assert 0.0 <= prob <= 1.0


# 12. Categorical feature handling with unseen categories
def test_categorical_feature_handling_unseen(trained_model):
    features = {
        "amount": 2500.0,
        "method": "crypto_wallet",  # Unseen method
        "customer_segment": "vip_diamond",  # Unseen segment
        "error_code": "UNKNOWN_CUSTOM_ERROR",  # Unseen error
        "hardness": "soft",
    }
    prob = trained_model.predict_probability(features)
    assert 0.0 <= prob <= 1.0


# 13. Model reproducibility
def test_model_reproducibility():
    X = pd.DataFrame([
        {"amount": 1000.0, "method": "upi", "customer_segment": "new", "error_code": "TIMEOUT", "hardness": "soft"},
        {"amount": 5000.0, "method": "card", "customer_segment": "returning", "error_code": "CARD_BLOCKED", "hardness": "hard"},
    ])
    y = pd.Series([1, 0])

    m1 = RecoveryProbabilityModel(random_state=123)
    m1.train(X, y)
    p1 = m1.predict_probability(X)

    m2 = RecoveryProbabilityModel(random_state=123)
    m2.train(X, y)
    p2 = m2.predict_probability(X)

    np.testing.assert_allclose(p1, p2)


# 14. No ground_truth_state leakage
def test_no_ground_truth_state_leakage(trained_model):
    leaked_features = {
        "amount": 5000.0,
        "method": "upi",
        "customer_segment": "returning",
        "error_code": "TIMEOUT",
        "hardness": "soft",
        "ground_truth_state": "VERIFIED_LOST_SOFT",  # Leakage attempt
    }
    with pytest.raises(ValueError, match="Data leakage detected"):
        trained_model.predict_probability(leaked_features)


# 15. No scenario leakage
def test_no_scenario_leakage(trained_model):
    leaked_features = {
        "amount": 5000.0,
        "method": "upi",
        "customer_segment": "returning",
        "error_code": "TIMEOUT",
        "hardness": "soft",
        "scenario": "clean_failure_soft",  # Leakage attempt
    }
    with pytest.raises(ValueError, match="Data leakage detected"):
        trained_model.predict_probability(leaked_features)
