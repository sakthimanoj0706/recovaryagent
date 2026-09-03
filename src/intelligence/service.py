from typing import List, Optional
from state_engine import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from recovery.economics import RecoveryCostConfig
from agent.llm import BaseLLMClient

from .models import IntelligentDecision
from .failure_classifier import DeterministicFailureClassifier
from .candidate_generator import DeterministicCandidateGenerator
from .economic_ranker import EconomicRanker
from .evaluator import RecommendationEvaluator
from .agent import AdvisoryIntelligenceAgent

class IntelligentRecoveryService:
    """End-to-end intelligent recovery decision engine."""
    
    def __init__(
        self,
        model: Optional[RecoveryProbabilityModel] = None,
        config: Optional[RecoveryCostConfig] = None,
        llm_client: Optional[BaseLLMClient] = None
    ):
        self.classifier = DeterministicFailureClassifier()
        self.candidate_generator = DeterministicCandidateGenerator(model=model, config=config)
        self.ranker = EconomicRanker()
        self.evaluator = RecommendationEvaluator()
        self.agent = AdvisoryIntelligenceAgent(llm_client=llm_client)

    def decide(
        self,
        payment: PaymentRecord,
        events: List[Event],
        retry_count: int = 0
    ) -> IntelligentDecision:
        
        # 1. Failure Classification
        # We determine the financial state to pass to the classifier
        # In a real run, this comes from FinancialStateEngine, but we can compute a proxy or 
        # expect the caller to pass it. Wait, we can just infer from events or assume VERIFIED_LOST for active recovery.
        # We'll just pass a generic state to the classifier, or assume the caller handles it.
        # Let's adjust classifier to not strictly need `financial_state` if it's implicitly VERIFIED_LOST
        # For now, let's just use "VERIFIED_LOST" as default if we are running a recovery decision.
        classification = self.classifier.classify("VERIFIED_LOST", events)
        
        # 2. Candidate Generation
        candidates = self.candidate_generator.generate(payment, events, classification, retry_count)
        
        # 3. Deterministic Ranking
        best_action = self.ranker.get_best_action(candidates)
        
        # 4. LLM Recommendation
        llm_rec = self.agent.get_recommendation(payment, classification, candidates, retry_count)
        
        # 5. Evaluation
        evaluation = self.evaluator.evaluate(llm_rec, best_action, candidates)
        
        # 6. Final Decision
        # "A mathematically inferior action must not become preferred merely because an LLM recommends it."
        if evaluation.safety_status == "SAFE" and evaluation.economic_delta >= 0:
            selected_action = llm_rec.recommended_action
            selection_reason = f"LLM recommended {selected_action} which is safe and economically sound. ({llm_rec.reason})"
        else:
            selected_action = best_action.action
            selection_reason = f"Deterministic override. LLM recommendation was {evaluation.safety_status}. Fallback to {best_action.action}."

        return IntelligentDecision(
            payment_id=payment.payment_id,
            classification=classification,
            candidates=candidates,
            deterministic_best_action=best_action,
            llm_recommendation=llm_rec,
            evaluation=evaluation,
            selected_action=selected_action,
            selection_reason=selection_reason
        )
