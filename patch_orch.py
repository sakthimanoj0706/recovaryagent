import re
with open("src/agent/orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''                if strategy_mode == "DETERMINISTIC":
                    try:
                        action = RecoveryAction(decision.deterministic_best_action.action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = f"DETERMINISTIC MODE: Chose {action.value}."
                    confidence = 1.0
                else:
                    try:
                        action = RecoveryAction(decision.selected_action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = decision.selection_reason
                    confidence = decision.llm_recommendation.confidence if decision.llm_recommendation else 1.0'''

patch = '''                if strategy_mode == "DETERMINISTIC":
                    try:
                        action = RecoveryAction(decision.deterministic_best_action.action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = f"DETERMINISTIC MODE: Chose {action.value}."
                    confidence = 1.0
                else:
                    try:
                        action = RecoveryAction(decision.selected_action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = decision.selection_reason
                    confidence = decision.llm_recommendation.confidence if decision.llm_recommendation else 1.0
                
                recommendation = RecoveryPlan(
                    payment_id=pid,
                    action=action,
                    priority=RecoveryPriority.HIGH,
                    reason=reason,
                    confidence=confidence,
                    expected_net_value=env if env is not None else 0.0
                )'''

if target in content:
    content = content.replace(target, patch)
    with open("src/agent/orchestrator.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Target not found")
