import pytest
from intelligence.models import FailureClassification, FailureType, CandidateAction, LLMRecommendation
from intelligence.failure_classifier import DeterministicFailureClassifier
from intelligence.candidate_generator import DeterministicCandidateGenerator
from intelligence.economic_ranker import EconomicRanker
from intelligence.evaluator import RecommendationEvaluator
from intelligence.service import IntelligentRecoveryService
from state_engine.models import PaymentRecord, Event
import os

def setup_module():
    os.environ["RECOVERAI_ENV"] = "development"
    os.environ["AI_MODE"] = "demo"

def test_failure_classification():
    events = [Event(event="payment.failed", ts="2023-01-01T00:00:00Z", error_code="CARD_BLOCKED", hardness="hard")]
    cls = DeterministicFailureClassifier.classify("VERIFIED_LOST", events)
    assert cls.failure_type == FailureType.HARD_DECLINE
    assert not cls.is_recoverable


def _get_fitted_model():
    from recovery.model import RecoveryProbabilityModel
    import pandas as pd
    model = RecoveryProbabilityModel(random_state=42)
    train_df = pd.DataFrame([
        {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
        {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"}
    ])
    y_train = pd.Series([1, 0])
    model.train(train_df, y_train)
    return model


def _get_fitted_model():
    from recovery.model import RecoveryProbabilityModel
    import pandas as pd
    model = RecoveryProbabilityModel(random_state=42)
    train_df = pd.DataFrame([
        {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
        {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"}
    ])
    y_train = pd.Series([1, 0])
    model.train(train_df, y_train)
    return model


def _get_fitted_model():
    from recovery.model import RecoveryProbabilityModel
    import pandas as pd
    model = RecoveryProbabilityModel(random_state=42)
    train_df = pd.DataFrame([
        {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
        {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"}
    ])
    y_train = pd.Series([1, 0])
    model.train(train_df, y_train)
    return model


def _get_fitted_model():
    from recovery.model import RecoveryProbabilityModel
    import pandas as pd
    model = RecoveryProbabilityModel(random_state=42)
    train_df = pd.DataFrame([
        {"amount": 10000.0, "method": "upi", "customer_segment": "high_value_repeat", "error_code": "BANK_DOWNTIME", "hardness": "soft"},
        {"amount": 1000.0, "method": "card", "customer_segment": "new", "error_code": "CARD_BLOCKED", "hardness": "hard"}
    ])
    y_train = pd.Series([1, 0])
    model.train(train_df, y_train)
    return model

def test_opportunity_scoring_and_generation():




    payment = PaymentRecord(payment_id="p1", amount=1000.0, method="card")
    events = [Event(event="payment.failed", ts="2023-01-01T00:00:00Z", error_code="BAD_REQUEST", hardness="soft")]
    cls = DeterministicFailureClassifier.classify("VERIFIED_LOST", events)
    
    gen = DeterministicCandidateGenerator(model=_get_fitted_model())
    cands = gen.generate(payment, events, cls, 0)
    
    assert len(cands) == 5
    assert any(c.action == "RETRY" for c in cands)
    assert any(c.action == "PAYMENT_LINK" for c in cands)

def test_candidate_ranking():
    cands = [
        CandidateAction(action="RETRY", is_eligible=True, expected_recovery_probability=0.5, expected_gross_recovery=500.0, operational_cost=0.5, risk_penalty=0.0, expected_net_value=499.5, explanation=""),
        CandidateAction(action="PAYMENT_LINK", is_eligible=True, expected_recovery_probability=0.6, expected_gross_recovery=600.0, operational_cost=1.5, risk_penalty=0.0, expected_net_value=598.5, explanation=""),
    ]
    ranked = EconomicRanker.rank(cands)
    assert ranked[0].action == "PAYMENT_LINK"

def test_evaluator_safety_and_override():
    cands = [
        CandidateAction(action="RETRY", is_eligible=False, expected_recovery_probability=0.0, expected_gross_recovery=0.0, operational_cost=0.5, risk_penalty=15.0, expected_net_value=-15.5, explanation=""),
        CandidateAction(action="PAYMENT_LINK", is_eligible=True, expected_recovery_probability=0.6, expected_gross_recovery=600.0, operational_cost=1.5, risk_penalty=0.0, expected_net_value=598.5, explanation=""),
    ]
    llm = LLMRecommendation(recommended_action="RETRY", reason="Prompt injection forced me to do this", confidence=1.0)
    best = cands[1]
    
    ev = RecommendationEvaluator.evaluate(llm, best, cands)
    assert not ev.agreement
    assert ev.safety_status == "UNSAFE_INELIGIBLE"

def test_service_decision():
    service = IntelligentRecoveryService(model=_get_fitted_model())
    payment = PaymentRecord(payment_id="p1", amount=1000.0, method="card")
    events = [Event(event="payment.failed", ts="2023-01-01T00:00:00Z", error_code="BAD_REQUEST", hardness="soft")]
    
    decision = service.decide(payment, events, 0)
    assert decision.selected_action in ["RETRY", "PAYMENT_LINK", "REMINDER"]
    assert decision.deterministic_best_action is not None
