import re
with open("src/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will append them at the end.
new_routes = """
# ==========================================
# INTELLIGENT RECOVERY ENGINE (STEP 18)
# ==========================================

from pydantic import BaseModel
from intelligence.service import IntelligentRecoveryService
from state_engine.models import PaymentRecord, Event

intel_service = IntelligentRecoveryService()

class IntelligenceRequest(BaseModel):
    payment: dict
    events: list[dict]
    retry_count: int = 0

@router.post("/intelligence/analyze")
async def analyze_failure(req: IntelligenceRequest, _role: Role = Depends(require_role(Role.ADMIN))):
    payment = PaymentRecord(**req.payment)
    events = [Event(**e) for e in req.events]
    cls = intel_service.classifier.classify("VERIFIED_LOST", events)
    return {"classification": cls.model_dump()}

@router.post("/intelligence/decide")
async def intelligence_decide(req: IntelligenceRequest, _role: Role = Depends(require_role(Role.ADMIN))):
    payment = PaymentRecord(**req.payment)
    events = [Event(**e) for e in req.events]
    decision = intel_service.decide(payment, events, req.retry_count)
    return {"decision": decision.model_dump()}

@router.post("/intelligence/evaluate")
async def intelligence_evaluate(req: IntelligenceRequest, _role: Role = Depends(require_role(Role.ADMIN))):
    # Already evaluated inside decide, but we can expose it.
    payment = PaymentRecord(**req.payment)
    events = [Event(**e) for e in req.events]
    decision = intel_service.decide(payment, events, req.retry_count)
    return {"evaluation": decision.evaluation.model_dump()}

@router.get("/intelligence/latest")
async def get_latest_intelligence(_role: Role = Depends(require_role(Role.ADMIN))):
    # Mock for frontend
    return {"status": "active", "models_loaded": True, "decisions_made": 1000}
"""

with open("src/api/routes.py", "a", encoding="utf-8") as f:
    f.write(new_routes)
