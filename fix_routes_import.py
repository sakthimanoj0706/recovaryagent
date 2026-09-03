import re
with open("src/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

patch = '''from api.auth import Role, require_role
from pydantic import BaseModel
from intelligence.service import IntelligentRecoveryService'''

content = content.replace("from pydantic import BaseModel\nfrom intelligence.service import IntelligentRecoveryService", patch)

with open("src/api/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
