with open("tests/test_agentic_orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("run_recovery_agent(payment, events)", 'run_recovery_agent(payment, events, strategy_mode="NAIVE")')
content = content.replace("run_recovery_agent(payment, events, ", 'run_recovery_agent(payment, events, strategy_mode="NAIVE", ')

with open("tests/test_agentic_orchestrator.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched tests")
