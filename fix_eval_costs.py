import re

with open("evaluate_intel.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("costs.manual_review_cost", "costs.manual_escalation_cost")
content = content.replace("costs.chargeback_risk_cost", "costs.hard_decline_penalty_cost")
content = content.replace("costs.retry_cost", "costs.gateway_attempt_cost")

with open("evaluate_intel.py", "w", encoding="utf-8") as f:
    f.write(content)
