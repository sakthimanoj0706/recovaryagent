from typing import List
from .models import CandidateAction

class EconomicRanker:
    """Deterministically ranks candidate actions by expected net value."""
    
    @staticmethod
    def rank(candidates: List[CandidateAction]) -> List[CandidateAction]:
        # Filter eligible actions first
        eligible = [c for c in candidates if c.is_eligible]
        
        # Sort by expected net value (descending)
        # If there's a tie, prioritize lower cost actions (e.g., STOP over ESCALATE)
        # Tie-breaker logic:
        # 1. Net value (descending)
        # 2. Operational cost (ascending)
        # 3. Alphabetical action name (deterministic fallback)
        
        eligible.sort(key=lambda c: (-c.expected_net_value, c.operational_cost, c.action))
        
        return eligible
    
    @staticmethod
    def get_best_action(candidates: List[CandidateAction]) -> CandidateAction:
        ranked = EconomicRanker.rank(candidates)
        if not ranked:
            # Fallback to STOP if nothing is eligible
            return CandidateAction(
                action="STOP",
                is_eligible=True,
                expected_recovery_probability=0.0,
                expected_gross_recovery=0.0,
                operational_cost=0.0,
                risk_penalty=0.0,
                expected_net_value=0.0,
                explanation="Fallback STOP action (no eligible candidates)."
            )
        return ranked[0]
