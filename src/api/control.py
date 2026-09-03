from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from api.auth import Role, require_role
from learning.models import RecoveryOutcome
from learning.outcome_store import OutcomeStore
from learning.calibration import CalibrationMonitor
from learning.drift import DriftDetector
from challenger.service import ChallengerService

router = APIRouter(prefix="/control", tags=["Control Plane"])

outcome_store = OutcomeStore()
challenger_service = ChallengerService()

@router.post("/outcomes/record")
async def record_outcome(outcome: RecoveryOutcome, _role: Role = Depends(require_role(Role.ADMIN))):
    outcome_store.record(outcome)
    return {"status": "recorded"}

@router.get("/outcomes")
async def get_outcomes(_role: Role = Depends(require_role(Role.OPERATOR))):
    return outcome_store.get_all()

@router.get("/metrics")
async def get_metrics(_role: Role = Depends(require_role(Role.OPERATOR))):
    from learning.metrics import LearningMetricsCalculator
    outcomes = outcome_store.get_all()
    return LearningMetricsCalculator.calculate_expected_vs_actual(outcomes)

@router.get("/calibration")
async def get_calibration(_role: Role = Depends(require_role(Role.OPERATOR))):
    outcomes = outcome_store.get_all()
    return CalibrationMonitor.calculate_calibration(outcomes)

@router.get("/drift")
async def get_drift(_role: Role = Depends(require_role(Role.OPERATOR))):
    outcomes = outcome_store.get_all()
    # Mock split for baseline vs current
    mid = len(outcomes) // 2
    baseline = outcomes[:mid]
    current = outcomes[mid:]
    
    d1 = DriftDetector.detect_failure_distribution_drift(baseline, current)
    d2 = DriftDetector.detect_success_rate_drift(baseline, current)
    
    return [d1.model_dump(), d2.model_dump()]

@router.post("/challenger/evaluate")
async def evaluate_challenger(strat_id: str, version: str, _role: Role = Depends(require_role(Role.OPERATOR))):
    chal = challenger_service.propose(strat_id, version)
    return challenger_service.evaluate(strat_id).model_dump()

@router.post("/challenger/approve")
async def approve_challenger(strat_id: str, _role: Role = Depends(require_role(Role.ADMIN))):
    return challenger_service.approve(strat_id).model_dump()

@router.post("/challenger/promote")
async def promote_challenger(strat_id: str, _role: Role = Depends(require_role(Role.ADMIN))):
    return challenger_service.promote(strat_id).model_dump()

@router.post("/challenger/rollback")
async def rollback_challenger(strat_id: str, _role: Role = Depends(require_role(Role.ADMIN))):
    return challenger_service.rollback(strat_id).model_dump()

@router.get("/challenger/latest")
async def latest_challenger(_role: Role = Depends(require_role(Role.OPERATOR))):
    if not challenger_service.active_challengers:
        return None
    k = list(challenger_service.active_challengers.keys())[-1]
    return challenger_service.active_challengers[k].model_dump()
