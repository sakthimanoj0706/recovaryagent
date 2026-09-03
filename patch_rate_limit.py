import re

with open("src/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

import_str = "from .rate_limit import expensive_limiter, webhook_limiter\n"
if "from .rate_limit" not in content:
    content = content.replace("from fastapi import APIRouter", import_str + "from fastapi import APIRouter")

# Apply webhook_limiter to webhooks
content = content.replace("@router.post(\"/webhooks/razorpay\")", "@router.post(\"/webhooks/razorpay\", dependencies=[Depends(webhook_limiter)])")
content = content.replace("@router.post(\"/webhooks/payment\")", "@router.post(\"/webhooks/payment\", dependencies=[Depends(webhook_limiter)])")

# Apply expensive_limiter to LLM/agent
content = content.replace("@router.post(\"/agent/recover/{payment_id}\")", "@router.post(\"/agent/recover/{payment_id}\", dependencies=[Depends(expensive_limiter)])")
content = content.replace("@router.post(\"/recovery/run/{payment_id}\")", "@router.post(\"/recovery/run/{payment_id}\", dependencies=[Depends(expensive_limiter)])")

with open("src/api/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
