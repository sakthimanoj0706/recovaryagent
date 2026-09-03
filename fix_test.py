import re
with open("tests/test_intelligent_recovery.py", "r", encoding="utf-8") as f:
    content = f.read()

patch = '''
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
'''

content = content.replace("def test_opportunity_scoring_and_generation():", patch)
content = content.replace("gen = DeterministicCandidateGenerator()", "gen = DeterministicCandidateGenerator(model=_get_fitted_model())")
content = content.replace("service = IntelligentRecoveryService()", "service = IntelligentRecoveryService(model=_get_fitted_model())")

with open("tests/test_intelligent_recovery.py", "w", encoding="utf-8") as f:
    f.write(content)
