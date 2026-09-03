import re
with open("tests/test_agentic_orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'run_recovery_agent\((.*?)\)', r'run_recovery_agent(\1, strategy_mode="NAIVE")', content)

# But wait, \1 might end with a trailing comma or I might append it to existing kwargs.
# If I just append it, we might have `strategy_mode="NAIVE"` at the end, which is fine!
# Wait, `run_recovery_agent(payment, events)` -> `run_recovery_agent(payment, events, strategy_mode="NAIVE")`
# `run_recovery_agent(payment, events, force_simulated_success=False)` -> `run_recovery_agent(payment, events, force_simulated_success=False, strategy_mode="NAIVE")`

with open("tests/test_agentic_orchestrator.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched tests")
