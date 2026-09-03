import re

with open("src/benchmark/strategies.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the incorrect cost config assignments in the IntelligentRecoveryStrategy class
content = content.replace("costs.manual_review_cost", "costs.manual_escalation_cost")
content = content.replace("costs.chargeback_risk_cost", "costs.hard_decline_penalty_cost")
content = content.replace("intel_service.candidate_generator.config.retry_cost = costs.payment_link_cost", "intel_service.candidate_generator.config.retry_cost = costs.gateway_attempt_cost")

with open("src/benchmark/strategies.py", "w", encoding="utf-8") as f:
    f.write(content)
