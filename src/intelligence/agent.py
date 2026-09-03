import json
from typing import List, Optional
from state_engine import PaymentRecord
from .models import FailureClassification, CandidateAction, LLMRecommendation
from agent.llm import BaseLLMClient

class AdvisoryIntelligenceAgent:
    """Queries the LLM for an advisory recommendation based on structured data."""
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        from agent.llm import get_default_llm_client, DeterministicFallbackLLMClient
        self.llm_client = llm_client or get_default_llm_client()
        self.is_demo = isinstance(self.llm_client, DeterministicFallbackLLMClient)
        
    def get_recommendation(
        self,
        payment: PaymentRecord,
        classification: FailureClassification,
        candidates: List[CandidateAction],
        previous_attempts: int
    ) -> LLMRecommendation:
        
        # If demo mode, just mirror the best candidate deterministic action
        if self.is_demo:
            best = max([c for c in candidates if c.is_eligible] or candidates[:1], key=lambda x: x.expected_net_value)
            return LLMRecommendation(
                recommended_action=best.action,
                reason="[DEMO MODE] Deterministic Fallback used as proxy for LLM.",
                confidence=1.0
            )
            
        # In live mode we'd construct the prompt and call the LLM.
        # But BaseLLMClient is tightly coupled to RecoveryPlan.
        # So we'll map the intelligence context to a standard RecoveryContext and call generate_recovery_plan.
        from agent.models import RecoveryContext, RecoveryAction
        
        ctx = RecoveryContext(
            payment_id=payment.payment_id,
            amount=float(payment.amount or 0.0),
            method=payment.method or "unknown",
            customer_segment=payment.customer_segment or "standard",
            financial_state="VERIFIED_LOST",
            recovery_probability=candidates[0].expected_recovery_probability if candidates else 0.0,
            expected_net_value=max((c.expected_net_value for c in candidates if c.is_eligible), default=0.0),
            failure_reason=classification.reason,
            hardness="hard" if classification.failure_type.value == "HARD_DECLINE" else "soft",
            retry_count=previous_attempts,
            previous_attempts=previous_attempts,
            previous_actions=[]
        )
        
        allowed_actions = [RecoveryAction(c.action) for c in candidates if c.is_eligible]
        
        try:
            plan = self.llm_client.generate_recovery_plan(ctx, allowed_actions, "")
            if plan:
                return LLMRecommendation(
                    recommended_action=plan.action.value,
                    reason=plan.reason,
                    confidence=plan.confidence
                )
        except Exception:
            pass
            
        return LLMRecommendation(
            recommended_action="STOP",
            reason="LLM unavailable or generated malformed response.",
            confidence=0.0
        )
