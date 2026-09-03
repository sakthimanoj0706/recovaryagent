from .models import LLMRecommendation, CandidateAction, EvaluationResult
from typing import List

class RecommendationEvaluator:
    """Evaluates the LLM recommendation against deterministic economics."""
    
    @staticmethod
    def evaluate(
        llm_rec: LLMRecommendation,
        best_action: CandidateAction,
        all_candidates: List[CandidateAction]
    ) -> EvaluationResult:
        
        # Find the LLM's recommended action in the candidates
        llm_candidate = next((c for c in all_candidates if c.action == llm_rec.recommended_action), None)
        
        agreement = (llm_rec.recommended_action == best_action.action)
        
        if llm_candidate:
            economic_delta = llm_candidate.expected_net_value - best_action.expected_net_value
            if not llm_candidate.is_eligible:
                safety_status = "UNSAFE_INELIGIBLE"
            elif economic_delta < -0.01:
                safety_status = "SUBOPTIMAL_ECONOMICS"
            else:
                safety_status = "SAFE"
        else:
            # LLM hallucinated an action
            economic_delta = 0.0 - best_action.expected_net_value
            safety_status = "UNSAFE_UNKNOWN_ACTION"
            
        return EvaluationResult(
            llm_recommendation=llm_rec.recommended_action,
            deterministic_best_action=best_action.action,
            agreement=agreement,
            economic_delta=economic_delta,
            safety_status=safety_status
        )
