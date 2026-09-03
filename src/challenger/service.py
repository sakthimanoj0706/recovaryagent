from typing import Dict, Any
from enum import Enum
from pydantic import BaseModel
from .engine import ChallengerEvaluationEngine

class PromotionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    EVALUATING = "EVALUATING"
    PASSED = "PASSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"

class ChallengerStrategy(BaseModel):
    id: str
    version: str
    status: PromotionStatus = PromotionStatus.PROPOSED
    evaluation_results: Dict[str, Any] = {}
    proof_hash: str = ""

class ChallengerService:
    
    def __init__(self):
        self.active_challengers: Dict[str, ChallengerStrategy] = {}
        
    def propose(self, strat_id: str, version: str) -> ChallengerStrategy:
        chal = ChallengerStrategy(id=strat_id, version=version)
        self.active_challengers[strat_id] = chal
        return chal
        
    def evaluate(self, strat_id: str) -> ChallengerStrategy:
        if strat_id not in self.active_challengers:
            raise ValueError("Challenger not found")
            
        chal = self.active_challengers[strat_id]
        chal.status = PromotionStatus.EVALUATING
        
        # Run offline evaluation
        res = ChallengerEvaluationEngine.evaluate_4_way()
        chal.evaluation_results = res["results"]
        chal.proof_hash = res["proof"].cryptographic_hash
        
        # Safety checks
        ch_res = res["results"]["CHALLENGER"]
        if ch_res["viol"] > 0 or ch_res["phantom"] > 0 or ch_res["double"] > 0 or ch_res["unsafe"] > 0:
            chal.status = PromotionStatus.REJECTED
        else:
            chal.status = PromotionStatus.APPROVAL_REQUIRED
            
        return chal
        
    def approve(self, strat_id: str) -> ChallengerStrategy:
        # Requires Admin via API routes
        if strat_id not in self.active_challengers:
            raise ValueError("Challenger not found")
        chal = self.active_challengers[strat_id]
        if chal.status != PromotionStatus.APPROVAL_REQUIRED:
            raise ValueError("Challenger is not ready for approval or failed safety.")
            
        chal.status = PromotionStatus.APPROVED
        return chal
        
    def promote(self, strat_id: str) -> ChallengerStrategy:
        if strat_id not in self.active_challengers:
            raise ValueError("Challenger not found")
        chal = self.active_challengers[strat_id]
        if chal.status != PromotionStatus.APPROVED:
            raise ValueError("Challenger must be explicitly approved first.")
            
        chal.status = PromotionStatus.PROMOTED
        return chal
        
    def rollback(self, strat_id: str) -> ChallengerStrategy:
        if strat_id not in self.active_challengers:
            raise ValueError("Challenger not found")
        chal = self.active_challengers[strat_id]
        chal.status = PromotionStatus.ROLLED_BACK
        return chal
