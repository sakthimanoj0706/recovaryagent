import re
with open("src/agent/orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('reason = "LLM unavailable"', 'reason = "LLM unavailable. Escalated."')

with open("src/agent/orchestrator.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched orchestrator")
